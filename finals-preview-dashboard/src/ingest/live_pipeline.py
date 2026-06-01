from __future__ import annotations

from pathlib import Path
from typing import Dict, Tuple

import pandas as pd

from src.config import SAMPLE_PLAYER_NAMES, SEASON, SEASON_TYPE
from src.utils.load_data import get_project_root, load_all_sample_data
from src.ingest.nba_stats import (
    fetch_team_stats,
    fetch_player_stats,
    fetch_lineups,
    fetch_shot_zones,
    fetch_synergy_pnr,
)
from src.ingest.basketball_reference import fetch_bref_advanced
from src.ingest.pbpstats_client import fetch_lineup_enrichment


REQUIRED_TABLES = ["team_stats", "player_stats", "shot_zones", "lineups", "pnr_duos", "matchups"]


def _fallback_table(sample: Dict[str, pd.DataFrame], key: str) -> pd.DataFrame:
    return sample[key].copy()


def _save_live_tables(tables: Dict[str, pd.DataFrame]) -> None:
    root = get_project_root()
    live_dir = root / "data" / "live"
    live_dir.mkdir(parents=True, exist_ok=True)

    for key, df in tables.items():
        if key in REQUIRED_TABLES and isinstance(df, pd.DataFrame) and not df.empty:
            df.to_csv(live_dir / f"{key}.csv", index=False)


def _merge_bref(player_stats: pd.DataFrame, bref: pd.DataFrame) -> pd.DataFrame:
    if player_stats.empty or bref.empty or "player" not in player_stats.columns or "player" not in bref.columns:
        return player_stats

    out = player_stats.merge(bref, on="player", how="left", suffixes=("", "_bref"))

    for target, source in [
        ("per", "per_bref"),
        ("bpm", "bpm_bref"),
        ("vorp", "vorp_bref"),
        ("ws48", "ws48_bref"),
    ]:
        if source in out.columns:
            out[target] = out[source].combine_first(out.get(target))

    if "ts_pct_bref" in out.columns:
        out["ts_pct"] = out["ts_pct_bref"].combine_first(out["ts_pct"])

    if "usg_pct_bref" in out.columns:
        # Basketball-Reference USG% is already percent-style, e.g. 30.2.
        out["usg_pct"] = out["usg_pct_bref"].combine_first(out["usg_pct"])

    drop_cols = [c for c in out.columns if c.endswith("_bref") or c in ["ts_pct_bref", "usg_pct_bref"]]
    return out.drop(columns=drop_cols, errors="ignore")


def _build_proxy_pnr_from_synergy(synergy: pd.DataFrame, sample_pnr: pd.DataFrame) -> pd.DataFrame:
    """Creates a conservative PnR table if Synergy data is available.

    Since public Synergy results usually expose play-type rows rather than exact
    handler-screener pairs, true duo pairing still requires pass tracking or
    possession-level reconstruction. If the available Synergy shape is not enough,
    sample data remains the fallback.
    """
    if synergy.empty:
        return sample_pnr.copy()

    required_name_cols = [col for col in ["PLAYER_NAME", "PLAYER", "NAME"] if col in synergy.columns]
    if not required_name_cols:
        return sample_pnr.copy()

    name_col = required_name_cols[0]
    ppp_col = next((col for col in ["PPP", "POINTS_PER_POSSESSION", "POSS_PTS"] if col in synergy.columns), None)
    poss_col = next((col for col in ["POSS", "POSS_PCT", "POSS_COUNT"] if col in synergy.columns), None)

    if ppp_col is None:
        return sample_pnr.copy()

    top = synergy.copy()
    top["ppp_value"] = pd.to_numeric(top[ppp_col], errors="coerce")
    top = top.dropna(subset=["ppp_value"]).sort_values("ppp_value", ascending=False).head(6)

    rows = []
    for _, row in top.iterrows():
        rows.append(
            {
                "team": row.get("TEAM_ABBREVIATION", row.get("TEAM_NAME", "Live")),
                "ball_handler": row.get(name_col, "Unknown"),
                "screener": "Unresolved from public play-type row",
                "possessions": float(row.get(poss_col, 100)) if poss_col else 100,
                "ppp": float(row["ppp_value"]),
                "tov_pct": float(row.get("TOV_PCT", 0)),
                "assist_pct": float(row.get("AST_PCT", 0)),
                "pass_connections": 0,
                "shared_minutes": 0,
                "net_rating": 0,
                "coverage_note": "Live Synergy play-type row; exact duo unresolved without possession/pass enrichment",
            }
        )

    return pd.DataFrame(rows) if rows else sample_pnr.copy()


def build_dataset(
    prefer_live: bool = False,
    season: str = SEASON,
    season_type: str = SEASON_TYPE,
) -> Tuple[Dict[str, pd.DataFrame], pd.DataFrame]:
    """Build dashboard tables.

    Returns:
        tables: dashboard table dictionary
        manifest: source status/caveat table for the Methods page
    """
    sample = load_all_sample_data()
    manifest_rows = []

    if not prefer_live:
        manifest = pd.DataFrame(
            [
                {
                    "Table": key,
                    "Source Used": "Sample CSV",
                    "Status": "Sample mode",
                    "Caveat": "Static sample/proxy data. Use live-first mode for ingestion attempts.",
                }
                for key in REQUIRED_TABLES
            ]
        )
        return sample, manifest

    tables: Dict[str, pd.DataFrame] = {}

    # Team stats
    team_stats = fetch_team_stats(season, season_type)
    if team_stats.empty:
        tables["team_stats"] = _fallback_table(sample, "team_stats")
        manifest_rows.append({"Table": "team_stats", "Source Used": "Sample CSV fallback", "Status": "Fallback", "Caveat": "NBA.com/stats team request failed or returned empty."})
    else:
        # preserve missing display columns expected by chart
        for col in sample["team_stats"].columns:
            if col not in team_stats.columns:
                team_stats[col] = sample["team_stats"][col].iloc[0] if col not in ["team"] else team_stats.get("team", "")
        tables["team_stats"] = team_stats[sample["team_stats"].columns]
        manifest_rows.append({"Table": "team_stats", "Source Used": "NBA.com/stats via nba_api", "Status": "Live", "Caveat": "Paint/perimeter defense may remain proxy if opponent tracking splits are unavailable."})

    # Player stats + Basketball-Reference advanced merge
    player_stats = fetch_player_stats(season, season_type)
    bref = fetch_bref_advanced(season, player_names=None)
    if player_stats.empty:
        tables["player_stats"] = _fallback_table(sample, "player_stats")
        manifest_rows.append({"Table": "player_stats", "Source Used": "Sample CSV fallback", "Status": "Fallback", "Caveat": "NBA.com/stats player request failed or returned empty."})
    else:
        player_stats = _merge_bref(player_stats, bref)
        for col in sample["player_stats"].columns:
            if col not in player_stats.columns:
                player_stats[col] = 0 if col not in ["player", "team", "role"] else ""
        tables["player_stats"] = player_stats[sample["player_stats"].columns]
        status = "Live + B-Ref merge" if not bref.empty else "Live NBA only"
        caveat = "Basketball-Reference advanced metrics merged when player names matched." if not bref.empty else "Basketball-Reference request failed or returned no matching rows."
        manifest_rows.append({"Table": "player_stats", "Source Used": "NBA.com/stats + Basketball-Reference", "Status": status, "Caveat": caveat})

    # Shot zones
    shot_zones = fetch_shot_zones(player_stats if not player_stats.empty else pd.DataFrame(), season, season_type)
    if shot_zones.empty:
        tables["shot_zones"] = _fallback_table(sample, "shot_zones")
        manifest_rows.append({"Table": "shot_zones", "Source Used": "Sample CSV fallback", "Status": "Fallback", "Caveat": "ShotChartDetail request failed, timed out, or player IDs were unavailable."})
    else:
        for col in sample["shot_zones"].columns:
            if col not in shot_zones.columns:
                shot_zones[col] = 0 if col not in ["player", "team", "zone"] else ""
        tables["shot_zones"] = shot_zones[sample["shot_zones"].columns]
        manifest_rows.append({"Table": "shot_zones", "Source Used": "NBA ShotChartDetail", "Status": "Live", "Caveat": "Zone eFG% uses FG% approximation unless shot value enrichment is added."})

    # Lineups
    lineups = fetch_lineups(season, season_type)
    pbp_lineups = fetch_lineup_enrichment(season, season_type)
    if lineups.empty:
        tables["lineups"] = _fallback_table(sample, "lineups")
        manifest_rows.append({"Table": "lineups", "Source Used": "Sample CSV fallback", "Status": "Fallback", "Caveat": "NBA.com/stats lineup request failed or returned empty."})
    else:
        for col in sample["lineups"].columns:
            if col not in lineups.columns:
                lineups[col] = 0 if col not in ["lineup", "team"] else ""
        tables["lineups"] = lineups[sample["lineups"].columns]
        caveat = "PBPStats lineup enrichment available." if not pbp_lineups.empty else "PBPStats enrichment failed or returned unrecognized shape."
        manifest_rows.append({"Table": "lineups", "Source Used": "NBA.com/stats + optional PBPStats", "Status": "Live", "Caveat": caveat})

    # PnR
    synergy = fetch_synergy_pnr(season, season_type)
    pnr_duos = _build_proxy_pnr_from_synergy(synergy, sample["pnr_duos"])
    tables["pnr_duos"] = pnr_duos
    pnr_status = "Live proxy" if not synergy.empty else "Fallback"
    pnr_source = "NBA SynergyPlayTypes via nba_api" if not synergy.empty else "Sample CSV fallback"
    pnr_caveat = "Exact handler-screener duo and defensive coverage labels require deeper possession/pass tracking." if not synergy.empty else "Synergy request failed or returned empty."
    manifest_rows.append({"Table": "pnr_duos", "Source Used": pnr_source, "Status": pnr_status, "Caveat": pnr_caveat})

    # Matchups
    tables["matchups"] = _fallback_table(sample, "matchups")
    manifest_rows.append({"Table": "matchups", "Source Used": "Sample CSV fallback", "Status": "Not implemented live yet", "Caveat": "Batch 2 scaffolds live ingestion; matchup rollup can be added as a later hardening pass."})

    _save_live_tables(tables)

    return tables, pd.DataFrame(manifest_rows)
