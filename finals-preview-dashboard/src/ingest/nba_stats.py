from __future__ import annotations

from pathlib import Path
from typing import Dict, List, Tuple

import pandas as pd

from src.config import TEAM_IDS, TEAM_FULL_NAMES, SAMPLE_PLAYER_NAMES, SEASON, SEASON_TYPE
from src.metrics.derived_metrics import normalize_percentile


def _safe_get_data_frame(endpoint_obj, index: int = 0) -> pd.DataFrame:
    frames = endpoint_obj.get_data_frames()
    if not frames:
        return pd.DataFrame()
    if index >= len(frames):
        return frames[0]
    return frames[index]


def _pick(row: pd.Series, *names, default=0):
    for name in names:
        if name in row and pd.notna(row[name]):
            return row[name]
    return default


def _nba_headers() -> dict:
    return {
        "Host": "stats.nba.com",
        "Connection": "keep-alive",
        "Accept": "application/json, text/plain, */*",
        "x-nba-stats-token": "true",
        "User-Agent": (
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
            "AppleWebKit/537.36 (KHTML, like Gecko) "
            "Chrome/124.0.0.0 Safari/537.36"
        ),
        "x-nba-stats-origin": "stats",
        "Origin": "https://www.nba.com",
        "Referer": "https://www.nba.com/",
        "Accept-Language": "en-US,en;q=0.9",
    }


def fetch_team_stats(season: str = SEASON, season_type: str = SEASON_TYPE) -> pd.DataFrame:
    """Fetches team-level ratings from NBA.com/stats through nba_api.

    Returns the dashboard's standardized `team_stats` shape.
    Falls back to an empty DataFrame if the request fails.
    """
    try:
        from nba_api.stats.endpoints import leaguedashteamstats
    except Exception:
        return pd.DataFrame()

    try:
        adv_endpoint = leaguedashteamstats.LeagueDashTeamStats(
            season=season,
            season_type_all_star=season_type,
            measure_type_detailed_defense="Advanced",
            per_mode_detailed="PerGame",
            pace_adjust="N",
            headers=_nba_headers(),
            timeout=20,
        )
        adv = _safe_get_data_frame(adv_endpoint)

        four_endpoint = leaguedashteamstats.LeagueDashTeamStats(
            season=season,
            season_type_all_star=season_type,
            measure_type_detailed_defense="Four Factors",
            per_mode_detailed="PerGame",
            pace_adjust="N",
            headers=_nba_headers(),
            timeout=20,
        )
        four = _safe_get_data_frame(four_endpoint)
    except Exception:
        return pd.DataFrame()

    if adv.empty:
        return pd.DataFrame()

    team_ids = set(TEAM_IDS.values())
    adv = adv[adv["TEAM_ID"].isin(team_ids)].copy()
    if not four.empty and "TEAM_ID" in four.columns:
        four = four[four["TEAM_ID"].isin(team_ids)].copy()
        merged = adv.merge(four, on=["TEAM_ID", "TEAM_NAME"], how="left", suffixes=("", "_FOUR"))
    else:
        merged = adv

    rows = []
    for _, row in merged.iterrows():
        team_name = next((name for name, tid in TEAM_IDS.items() if tid == row["TEAM_ID"]), row.get("TEAM_NAME", "Unknown"))
        rows.append(
            {
                "team": team_name,
                "ortg": float(_pick(row, "OFF_RATING", "E_OFF_RATING", default=0)),
                "drtg": float(_pick(row, "DEF_RATING", "E_DEF_RATING", default=0)),
                "net_rating": float(_pick(row, "NET_RATING", "E_NET_RATING", default=0)),
                "pace": float(_pick(row, "PACE", "PACE_PER40", default=0)),
                "efg_pct": float(_pick(row, "EFG_PCT", default=0)),
                "ts_pct": float(_pick(row, "TS_PCT", default=0)),
                "tov_pct": float(_pick(row, "TM_TOV_PCT", "TOV_PCT", default=0)),
                "oreb_pct": float(_pick(row, "OREB_PCT", default=0)),
                "dreb_pct": float(_pick(row, "DREB_PCT", default=0)),
                "paint_defense": 50,
                "perimeter_defense": 50,
            }
        )

    output = pd.DataFrame(rows)
    if output.empty:
        return output

    output["off_rank"] = normalize_percentile(output["ortg"], True)
    output["def_rank"] = normalize_percentile(output["drtg"], False)
    output["reb_rank"] = normalize_percentile(output.get("dreb_pct", pd.Series([0] * len(output))), True)
    output["trans_rank"] = 50
    output["rim_rank"] = 50
    output["perimeter_rank"] = 50
    return output


def fetch_player_stats(season: str = SEASON, season_type: str = SEASON_TYPE) -> pd.DataFrame:
    """Fetches player stats from NBA.com/stats and standardizes for the dashboard."""
    try:
        from nba_api.stats.endpoints import leaguedashplayerstats
    except Exception:
        return pd.DataFrame()

    try:
        base_endpoint = leaguedashplayerstats.LeagueDashPlayerStats(
            season=season,
            season_type_all_star=season_type,
            measure_type_detailed_defense="Base",
            per_mode_detailed="PerGame",
            headers=_nba_headers(),
            timeout=20,
        )
        base = _safe_get_data_frame(base_endpoint)

        advanced_endpoint = leaguedashplayerstats.LeagueDashPlayerStats(
            season=season,
            season_type_all_star=season_type,
            measure_type_detailed_defense="Advanced",
            per_mode_detailed="PerGame",
            headers=_nba_headers(),
            timeout=20,
        )
        advanced = _safe_get_data_frame(advanced_endpoint)
    except Exception:
        return pd.DataFrame()

    if base.empty:
        return pd.DataFrame()

    team_ids = set(TEAM_IDS.values())
    base = base[base["TEAM_ID"].isin(team_ids)].copy()
    if not advanced.empty and "PLAYER_ID" in advanced.columns:
        keep_cols = [
            col for col in ["PLAYER_ID", "TS_PCT", "USG_PCT", "AST_PCT", "REB_PCT", "TOV_PCT", "NET_RATING"]
            if col in advanced.columns
        ]
        base = base.merge(advanced[keep_cols], on="PLAYER_ID", how="left")

    rows = []
    for _, row in base.iterrows():
        team_name = next((name for name, tid in TEAM_IDS.items() if tid == row["TEAM_ID"]), row.get("TEAM_ABBREVIATION", "Unknown"))
        rows.append(
            {
                "player": row.get("PLAYER_NAME", ""),
                "team": team_name,
                "role": "Rotation player",
                "pts": float(_pick(row, "PTS", default=0)),
                "ast": float(_pick(row, "AST", default=0)),
                "reb": float(_pick(row, "REB", default=0)),
                "per": 0.0,
                "ts_pct": float(_pick(row, "TS_PCT", default=0)),
                "usg_pct": float(_pick(row, "USG_PCT", default=0)) * 100 if _pick(row, "USG_PCT", default=0) <= 1 else float(_pick(row, "USG_PCT", default=0)),
                "bpm": 0.0,
                "vorp": 0.0,
                "ws48": 0.0,
                "player_id": row.get("PLAYER_ID", None),
            }
        )

    output = pd.DataFrame(rows)
    if output.empty:
        return output

    # Keep likely rotation players using minutes, but do not over-filter if data is sparse.
    if "MIN" in base.columns:
        mins = base[["PLAYER_NAME", "MIN"]].rename(columns={"PLAYER_NAME": "player"})
        output = output.merge(mins, on="player", how="left")
        output = output.sort_values(["team", "MIN"], ascending=[True, False]).groupby("team").head(10)
        output = output.drop(columns=["MIN"])

    return output.reset_index(drop=True)


def fetch_lineups(season: str = SEASON, season_type: str = SEASON_TYPE, group_quantity: int = 5) -> pd.DataFrame:
    """Fetches lineup data from NBA.com/stats.

    Returns the dashboard's standardized `lineups` shape.
    """
    try:
        from nba_api.stats.endpoints import leaguedashlineups
    except Exception:
        return pd.DataFrame()

    all_rows = []

    for team, team_id in TEAM_IDS.items():
        try:
            endpoint = leaguedashlineups.LeagueDashLineups(
                team_id_nullable=team_id,
                group_quantity=group_quantity,
                season=season,
                season_type_all_star=season_type,
                measure_type_detailed_defense="Advanced",
                per_mode_detailed="Per100Possessions",
                headers=_nba_headers(),
                timeout=20,
            )
            df = _safe_get_data_frame(endpoint)
        except Exception:
            df = pd.DataFrame()

        if df.empty:
            continue

        for _, row in df.head(10).iterrows():
            all_rows.append(
                {
                    "lineup": row.get("GROUP_NAME", row.get("GROUP_ID", "Unknown lineup")),
                    "team": team,
                    "min": float(_pick(row, "MIN", default=0)),
                    "ortg": float(_pick(row, "OFF_RATING", default=0)),
                    "drtg": float(_pick(row, "DEF_RATING", default=0)),
                    "net_rating": float(_pick(row, "NET_RATING", default=0)),
                    "efg_pct": float(_pick(row, "EFG_PCT", default=0)),
                    "tov_pct": float(_pick(row, "TM_TOV_PCT", "TOV_PCT", default=0)),
                    "reb_pct": float(_pick(row, "REB_PCT", default=0)),
                    "plus_minus": float(_pick(row, "PLUS_MINUS", default=0)),
                }
            )

    return pd.DataFrame(all_rows)


def fetch_shot_zones(players_df: pd.DataFrame, season: str = SEASON, season_type: str = SEASON_TYPE) -> pd.DataFrame:
    """Fetches and summarizes NBA ShotChartDetail data by player and shot zone.

    This can be slow and may be blocked in cloud environments, so failures return
    an empty DataFrame for graceful fallback.
    """
    try:
        from nba_api.stats.endpoints import shotchartdetail
    except Exception:
        return pd.DataFrame()

    if players_df.empty or "player_id" not in players_df.columns:
        return pd.DataFrame()

    rows = []

    for _, player_row in players_df.head(12).iterrows():
        player_id = player_row.get("player_id")
        if pd.isna(player_id):
            continue

        try:
            endpoint = shotchartdetail.ShotChartDetail(
                team_id=0,
                player_id=int(player_id),
                season_nullable=season,
                season_type_all_star=season_type,
                context_measure_simple="FGA",
                headers=_nba_headers(),
                timeout=20,
            )
            shots = _safe_get_data_frame(endpoint)
        except Exception:
            shots = pd.DataFrame()

        if shots.empty:
            continue

        zone_col = "SHOT_ZONE_BASIC" if "SHOT_ZONE_BASIC" in shots.columns else "SHOT_ZONE_AREA"
        if zone_col not in shots.columns:
            continue

        grouped = (
            shots.groupby(zone_col)
            .agg(
                loc_x=("LOC_X", "mean"),
                loc_y=("LOC_Y", "mean"),
                fg_pct=("SHOT_MADE_FLAG", "mean"),
                shot_volume=("SHOT_MADE_FLAG", "size"),
            )
            .reset_index()
        )

        for _, zone in grouped.iterrows():
            rows.append(
                {
                    "player": player_row["player"],
                    "team": player_row["team"],
                    "zone": zone[zone_col],
                    "loc_x": float(zone["loc_x"]),
                    "loc_y": float(zone["loc_y"]),
                    "fg_pct": float(zone["fg_pct"]),
                    "efg_pct": float(zone["fg_pct"]),
                    "shot_volume": int(zone["shot_volume"]),
                    "volume_rank": 0,
                }
            )

    output = pd.DataFrame(rows)
    if not output.empty:
        output["volume_rank"] = output.groupby("player")["shot_volume"].rank(ascending=False, method="dense").astype(int)

    return output


def fetch_synergy_pnr(season: str = SEASON, season_type: str = SEASON_TYPE) -> pd.DataFrame:
    """Attempts to fetch Synergy play-type data for PnR ball handler / roll man.

    Public data usually does not expose true defensive coverage labels. This returns
    player/team play-type efficiency when available. Duo construction still needs
    pass or lineup enrichment, so the pipeline may fall back to sample PnR data.
    """
    try:
        from nba_api.stats.endpoints import synergyplaytypes
    except Exception:
        return pd.DataFrame()

    frames = []

    for play_type in ["PRBallHandler", "PRRollman"]:
        try:
            endpoint = synergyplaytypes.SynergyPlayTypes(
                league_id="00",
                per_mode_simple="PerGame",
                play_type_nullable=play_type,
                player_or_team="P",
                season=season,
                season_type_all_star=season_type,
                type_grouping_nullable="offensive",
                headers=_nba_headers(),
                timeout=20,
            )
            df = _safe_get_data_frame(endpoint)
            if not df.empty:
                df["play_type"] = play_type
                frames.append(df)
        except Exception:
            continue

    if not frames:
        return pd.DataFrame()

    return pd.concat(frames, ignore_index=True)
