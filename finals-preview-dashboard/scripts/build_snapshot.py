from __future__ import annotations

import argparse
import sys
from datetime import datetime, timezone
from pathlib import Path
from io import StringIO

import pandas as pd
import requests_cache

sys.path.append(str(Path(__file__).resolve().parents[1]))

from nba_api.stats.endpoints import (
    commonteamroster,
    leaguedashteamstats,
    leaguedashplayerstats,
    leaguedashlineups,
    synergyplaytypes,
    shotchartdetail,
)

from src.config import TEAM_IDS
from src.metrics.formatting import normalize_percentile


SNAPSHOT_DIR = Path("data/snapshot")
RAW_DIR = Path("data/raw")


def nba_headers() -> dict:
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


def safe_frame(endpoint_obj, index: int = 0) -> pd.DataFrame:
    frames = endpoint_obj.get_data_frames()
    if not frames:
        return pd.DataFrame()

    if index >= len(frames):
        return frames[0]

    return frames[index]


def pick(row: pd.Series, *names: str, default=0):
    for name in names:
        if name in row and pd.notna(row[name]):
            return row[name]
    return default


def write_table(df: pd.DataFrame, filename: str, columns: list[str] | None = None) -> None:
    SNAPSHOT_DIR.mkdir(parents=True, exist_ok=True)

    if df is None or df.empty:
        if columns:
            df = pd.DataFrame(columns=columns)
        else:
            df = pd.DataFrame()

    df.to_csv(SNAPSHOT_DIR / filename, index=False)


def fetch_roster(season: str):
    rows = []
    status = []

    for team, team_id in TEAM_IDS.items():
        try:
            endpoint = commonteamroster.CommonTeamRoster(
                team_id=team_id,
                season=season,
                headers=nba_headers(),
                timeout=30,
            )
            df = safe_frame(endpoint)

            if df.empty:
                status.append(("roster", "NBA CommonTeamRoster", "Unavailable", f"{team}: empty table"))
                continue

            for _, row in df.iterrows():
                rows.append(
                    {
                        "player_id": row.get("PLAYER_ID"),
                        "player": row.get("PLAYER", row.get("PLAYER_NAME", "")),
                        "team": team,
                        "position": row.get("POSITION", ""),
                        "jersey": row.get("NUM", ""),
                        "height": row.get("HEIGHT", ""),
                        "weight": row.get("WEIGHT", ""),
                        "birth_date": row.get("BIRTH_DATE", ""),
                        "age": row.get("AGE", ""),
                        "exp": row.get("EXP", ""),
                        "school": row.get("SCHOOL", ""),
                    }
                )

            status.append(("roster", "NBA CommonTeamRoster", "Loaded", f"{team}: {len(df)} rows"))

        except Exception as exc:
            status.append(("roster", "NBA CommonTeamRoster", "Failed", f"{team}: {exc}"))

    return pd.DataFrame(rows), status


def fetch_team_stats(season: str, season_type: str):
    try:
        advanced = safe_frame(
            leaguedashteamstats.LeagueDashTeamStats(
                season=season,
                season_type_all_star=season_type,
                measure_type_detailed_defense="Advanced",
                per_mode_detailed="PerGame",
                pace_adjust="N",
                headers=nba_headers(),
                timeout=30,
            )
        )

        four_factors = safe_frame(
            leaguedashteamstats.LeagueDashTeamStats(
                season=season,
                season_type_all_star=season_type,
                measure_type_detailed_defense="Four Factors",
                per_mode_detailed="PerGame",
                pace_adjust="N",
                headers=nba_headers(),
                timeout=30,
            )
        )

    except Exception as exc:
        return pd.DataFrame(), [("team_stats", "NBA LeagueDashTeamStats", "Failed", str(exc))]

    if advanced.empty:
        return pd.DataFrame(), [("team_stats", "NBA LeagueDashTeamStats", "Unavailable", "Advanced table empty")]

    advanced = advanced[advanced["TEAM_ID"].isin(set(TEAM_IDS.values()))].copy()

    if not four_factors.empty and "TEAM_ID" in four_factors.columns:
        four_factors = four_factors[four_factors["TEAM_ID"].isin(set(TEAM_IDS.values()))].copy()
        merged = advanced.merge(
            four_factors,
            on=["TEAM_ID", "TEAM_NAME"],
            how="left",
            suffixes=("", "_FOUR"),
        )
    else:
        merged = advanced

    rows = []

    for _, row in merged.iterrows():
        team = next(
            (name for name, team_id in TEAM_IDS.items() if team_id == row["TEAM_ID"]),
            row.get("TEAM_NAME", "Unknown"),
        )

        rows.append(
            {
                "team": team,
                "ortg": float(pick(row, "OFF_RATING", "E_OFF_RATING", default=0)),
                "drtg": float(pick(row, "DEF_RATING", "E_DEF_RATING", default=0)),
                "net_rating": float(pick(row, "NET_RATING", "E_NET_RATING", default=0)),
                "pace": float(pick(row, "PACE", "PACE_PER40", default=0)),
                "efg_pct": float(pick(row, "EFG_PCT", default=0)),
                "ts_pct": float(pick(row, "TS_PCT", default=0)),
                "tov_pct": float(pick(row, "TM_TOV_PCT", "TOV_PCT", default=0)),
                "oreb_pct": float(pick(row, "OREB_PCT", default=0)),
                "dreb_pct": float(pick(row, "DREB_PCT", default=0)),
            }
        )

    output = pd.DataFrame(rows)

    if not output.empty:
        output["off_rank"] = normalize_percentile(output["ortg"], True)
        output["def_rank"] = normalize_percentile(output["drtg"], False)
        output["reb_rank"] = normalize_percentile(output["dreb_pct"], True)
        output["pace_rank"] = normalize_percentile(output["pace"], True)
        output["shooting_rank"] = normalize_percentile(output["efg_pct"], True)
        output["turnover_rank"] = normalize_percentile(output["tov_pct"], False)

    return output, [("team_stats", "NBA LeagueDashTeamStats", "Loaded", f"{len(output)} rows")]


def fetch_player_stats(season: str, season_type: str, roster: pd.DataFrame):
    try:
        base = safe_frame(
            leaguedashplayerstats.LeagueDashPlayerStats(
                season=season,
                season_type_all_star=season_type,
                measure_type_detailed_defense="Base",
                per_mode_detailed="PerGame",
                headers=nba_headers(),
                timeout=30,
            )
        )

        advanced = safe_frame(
            leaguedashplayerstats.LeagueDashPlayerStats(
                season=season,
                season_type_all_star=season_type,
                measure_type_detailed_defense="Advanced",
                per_mode_detailed="PerGame",
                headers=nba_headers(),
                timeout=30,
            )
        )

    except Exception as exc:
        return pd.DataFrame(), [("player_stats", "NBA LeagueDashPlayerStats", "Failed", str(exc))]

    if base.empty:
        return pd.DataFrame(), [("player_stats", "NBA LeagueDashPlayerStats", "Unavailable", "Base table empty")]

    base = base[base["TEAM_ID"].isin(set(TEAM_IDS.values()))].copy()

    if not advanced.empty and "PLAYER_ID" in advanced.columns:
        keep = [
            column
            for column in ["PLAYER_ID", "TS_PCT", "USG_PCT", "AST_PCT", "REB_PCT", "TOV_PCT", "NET_RATING"]
            if column in advanced.columns
        ]
        base = base.merge(advanced[keep], on="PLAYER_ID", how="left")

    rows = []

    for _, row in base.iterrows():
        team = next(
            (name for name, team_id in TEAM_IDS.items() if team_id == row["TEAM_ID"]),
            row.get("TEAM_ABBREVIATION", ""),
        )

        usg_pct = float(pick(row, "USG_PCT", default=0))
        if usg_pct <= 1:
            usg_pct *= 100

        rows.append(
            {
                "player_id": row.get("PLAYER_ID"),
                "player": row.get("PLAYER_NAME", ""),
                "team": team,
                "gp": float(pick(row, "GP", default=0)),
                "min": float(pick(row, "MIN", default=0)),
                "pts": float(pick(row, "PTS", default=0)),
                "reb": float(pick(row, "REB", default=0)),
                "ast": float(pick(row, "AST", default=0)),
                "stl": float(pick(row, "STL", default=0)),
                "blk": float(pick(row, "BLK", default=0)),
                "fg_pct": float(pick(row, "FG_PCT", default=0)),
                "fg3_pct": float(pick(row, "FG3_PCT", default=0)),
                "ft_pct": float(pick(row, "FT_PCT", default=0)),
                "ts_pct": float(pick(row, "TS_PCT", default=0)),
                "usg_pct": usg_pct,
                "net_rating": float(pick(row, "NET_RATING", default=0)),
            }
        )

    output = pd.DataFrame(rows)

    if roster is not None and not roster.empty and "player_id" in roster.columns:
        roster_keep = roster[["player_id", "position", "jersey", "height", "weight", "age", "exp", "school"]].copy()
        output = output.merge(roster_keep, on="player_id", how="left")

    return output.sort_values(["team", "min"], ascending=[True, False]), [
        ("player_stats", "NBA LeagueDashPlayerStats", "Loaded", f"{len(output)} rows")
    ]


def fetch_bref_advanced(season: str):
    try:
        year = int(season.split("-")[0]) + 1
    except Exception:
        year = 2026

    url = f"https://www.basketball-reference.com/leagues/NBA_{year}_advanced.html"

    try:
        session = requests_cache.CachedSession(
            str(RAW_DIR / "bref_cache"),
            expire_after=60 * 60 * 24 * 30,
        )

        response = session.get(
            url,
            headers={
                "User-Agent": (
                    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                    "AppleWebKit/537.36 (KHTML, like Gecko) "
                    "Chrome/124.0.0.0 Safari/537.36"
                )
            },
            timeout=30,
        )
        response.raise_for_status()

        tables = pd.read_html(StringIO(response.text))

    except Exception as exc:
        return pd.DataFrame(), [("basketball_reference_advanced", "Basketball-Reference", "Failed", str(exc))]

    if not tables:
        return pd.DataFrame(), [("basketball_reference_advanced", "Basketball-Reference", "Unavailable", "No tables")]

    table = tables[0]

    if "Rk" in table.columns:
        table = table[table["Rk"] != "Rk"].copy()

    rename_map = {
        "Player": "player",
        "PER": "per",
        "TS%": "ts_pct_bref",
        "USG%": "usg_pct_bref",
        "BPM": "bpm",
        "VORP": "vorp",
        "WS/48": "ws48",
    }

    keep = [column for column in rename_map if column in table.columns]
    output = table[keep].rename(columns=rename_map)

    for column in ["per", "ts_pct_bref", "usg_pct_bref", "bpm", "vorp", "ws48"]:
        if column in output.columns:
            output[column] = pd.to_numeric(output[column], errors="coerce")

    output = output.drop_duplicates(subset=["player"], keep="first")

    return output, [("basketball_reference_advanced", "Basketball-Reference", "Loaded", f"{len(output)} rows")]


def merge_bref(player_stats: pd.DataFrame, bref: pd.DataFrame) -> pd.DataFrame:
    if player_stats.empty or bref.empty:
        return player_stats

    output = player_stats.merge(bref, on="player", how="left")

    if "ts_pct_bref" in output.columns:
        output["ts_pct_reference"] = output["ts_pct_bref"]

    if "usg_pct_bref" in output.columns:
        output["usg_pct_reference"] = output["usg_pct_bref"]

    return output


def fetch_lineups(season: str, season_type: str):
    rows = []
    status = []

    for team, team_id in TEAM_IDS.items():
        try:
            endpoint = leaguedashlineups.LeagueDashLineups(
                team_id_nullable=team_id,
                group_quantity=5,
                season=season,
                season_type_all_star=season_type,
                measure_type_detailed_defense="Advanced",
                per_mode_detailed="Per100Possessions",
                headers=nba_headers(),
                timeout=30,
            )
            df = safe_frame(endpoint)

        except Exception as exc:
            status.append(("lineups", "NBA LeagueDashLineups", "Failed", f"{team}: {exc}"))
            continue

        if df.empty:
            status.append(("lineups", "NBA LeagueDashLineups", "Unavailable", f"{team}: empty"))
            continue

        for _, row in df.head(20).iterrows():
            rows.append(
                {
                    "lineup": row.get("GROUP_NAME", row.get("GROUP_ID", "")),
                    "team": team,
                    "min": float(pick(row, "MIN", default=0)),
                    "ortg": float(pick(row, "OFF_RATING", default=0)),
                    "drtg": float(pick(row, "DEF_RATING", default=0)),
                    "net_rating": float(pick(row, "NET_RATING", default=0)),
                    "efg_pct": float(pick(row, "EFG_PCT", default=0)),
                    "tov_pct": float(pick(row, "TM_TOV_PCT", "TOV_PCT", default=0)),
                    "reb_pct": float(pick(row, "REB_PCT", default=0)),
                    "plus_minus": float(pick(row, "PLUS_MINUS", default=0)),
                }
            )

        status.append(("lineups", "NBA LeagueDashLineups", "Loaded", f"{team}: {len(df)} source rows"))

    return pd.DataFrame(rows), status


def fetch_pnr_play_types(season: str, season_type: str):
    frames = []
    status = []

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
                headers=nba_headers(),
                timeout=30,
            )

            df = safe_frame(endpoint)

            if df.empty:
                status.append(("pnr_play_types", "NBA SynergyPlayTypes", "Unavailable", f"{play_type}: empty"))
                continue

            df["play_type"] = play_type
            frames.append(df)
            status.append(("pnr_play_types", "NBA SynergyPlayTypes", "Loaded", f"{play_type}: {len(df)} source rows"))

        except Exception as exc:
            status.append(("pnr_play_types", "NBA SynergyPlayTypes", "Failed", f"{play_type}: {exc}"))

    if not frames:
        return pd.DataFrame(), status

    raw = pd.concat(frames, ignore_index=True)

    if "TEAM_ID" in raw.columns:
        raw = raw[raw["TEAM_ID"].isin(set(TEAM_IDS.values()))].copy()

    name_col = next((column for column in ["PLAYER_NAME", "PLAYER", "NAME"] if column in raw.columns), None)
    ppp_col = next((column for column in ["PPP", "POINTS_PER_POSSESSION", "POSS_PTS"] if column in raw.columns), None)
    poss_col = next((column for column in ["POSS", "POSS_COUNT"] if column in raw.columns), None)

    rows = []

    for _, row in raw.iterrows():
        team = next(
            (name for name, team_id in TEAM_IDS.items() if row.get("TEAM_ID") == team_id),
            row.get("TEAM_ABBREVIATION", row.get("TEAM_NAME", "")),
        )

        rows.append(
            {
                "team": team,
                "player": row.get(name_col, "") if name_col else "",
                "play_type": row.get("play_type", ""),
                "possessions": float(row.get(poss_col, 0)) if poss_col else 0,
                "ppp": float(row.get(ppp_col, 0)) if ppp_col else 0,
                "percentile": float(row.get("PERCENTILE", 0)) if "PERCENTILE" in row else None,
                "tov_pct": float(row.get("TOV_PCT", 0)) if "TOV_PCT" in row else None,
                "score_freq": float(row.get("SCORE_POSS_PCT", 0)) if "SCORE_POSS_PCT" in row else None,
            }
        )

    return pd.DataFrame(rows), status


def fetch_shot_zones(player_stats: pd.DataFrame, season: str, season_type: str, max_players: int):
    rows = []
    status = []

    if player_stats.empty or "player_id" not in player_stats.columns:
        return pd.DataFrame(), [("shot_zones", "NBA ShotChartDetail", "Unavailable", "No player IDs available")]

    players = player_stats.sort_values(["team", "min"], ascending=[True, False]).groupby("team").head(max_players)

    for _, player in players.iterrows():
        player_id = int(player["player_id"])

        try:
            endpoint = shotchartdetail.ShotChartDetail(
                team_id=0,
                player_id=player_id,
                season_nullable=season,
                season_type_all_star=season_type,
                context_measure_simple="FGA",
                headers=nba_headers(),
                timeout=30,
            )

            shots = safe_frame(endpoint)

        except Exception as exc:
            status.append(("shot_zones", "NBA ShotChartDetail", "Failed", f"{player['player']}: {exc}"))
            continue

        if shots.empty:
            status.append(("shot_zones", "NBA ShotChartDetail", "Unavailable", f"{player['player']}: empty"))
            continue

        zone_col = "SHOT_ZONE_BASIC" if "SHOT_ZONE_BASIC" in shots.columns else "SHOT_ZONE_AREA"

        if zone_col not in shots.columns:
            status.append(("shot_zones", "NBA ShotChartDetail", "Unavailable", f"{player['player']}: no zone column"))
            continue

        shots["SHOT_VALUE"] = shots.get("SHOT_TYPE", "").astype(str).str.contains("3PT").map({True: 3, False: 2})
        shots["POINTS"] = shots["SHOT_MADE_FLAG"] * shots["SHOT_VALUE"]

        grouped = (
            shots.groupby(zone_col)
            .agg(
                loc_x=("LOC_X", "mean"),
                loc_y=("LOC_Y", "mean"),
                fg_pct=("SHOT_MADE_FLAG", "mean"),
                points=("POINTS", "sum"),
                shot_volume=("SHOT_MADE_FLAG", "size"),
            )
            .reset_index()
            .rename(columns={zone_col: "zone"})
        )

        grouped["efg_pct"] = grouped["points"] / (2 * grouped["shot_volume"])
        grouped["player_id"] = player_id
        grouped["player"] = player["player"]
        grouped["team"] = player["team"]
        grouped["volume_rank"] = grouped["shot_volume"].rank(ascending=False, method="dense").astype(int)

        rows.extend(
            grouped[
                ["player_id", "player", "team", "zone", "loc_x", "loc_y", "fg_pct", "efg_pct", "shot_volume", "volume_rank"]
            ].to_dict("records")
        )

        status.append(("shot_zones", "NBA ShotChartDetail", "Loaded", f"{player['player']}: {len(grouped)} zones"))

    return pd.DataFrame(rows), status


def create_empty_matchups():
    columns = [
        "defender",
        "team_defense",
        "offender",
        "team_offense",
        "possessions",
        "pts_allowed",
        "fg_pct_allowed",
        "fg_pct_suppression",
        "notes",
    ]

    return pd.DataFrame(columns=columns), [
        (
            "matchups",
            "NBA matchup endpoint or possession parser",
            "Not built",
            "No fake matchup matrix is generated. Add MatchupsRollup/BoxScoreMatchupsV3 integration or a possession parser.",
        )
    ]


def write_snapshot_readme(season: str, season_type: str, created_at: str) -> None:
    content = f"""# Snapshot Data

Generated at UTC: `{created_at}`

Season: `{season}`

Season type: `{season_type}`

## Files

- `team_stats.csv`: NBA.com/stats team advanced and four factors snapshot.
- `player_stats.csv`: NBA.com/stats player snapshot with Basketball-Reference advanced context when available.
- `roster.csv`: NBA CommonTeamRoster snapshot.
- `lineups.csv`: NBA LeagueDashLineups snapshot.
- `shot_zones.csv`: Combined NBA ShotChartDetail zone summary for selected rotation players.
- `pnr_play_types.csv`: NBA SynergyPlayTypes pick-and-roll ball-handler and roll-man rows when available.
- `matchups.csv`: Empty unless a real matchup parser/endpoint is added. No fabricated matchup data.
- `source_manifest.csv`: Source success/failure log.
- `snapshot_metadata.csv`: Snapshot creation metadata.

## Policy

This folder contains saved source data. The Streamlit app reads this folder only and does not request public data on page load.
"""
    (SNAPSHOT_DIR / "README.md").write_text(content, encoding="utf-8")


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--season", default="2025-26")
    parser.add_argument("--season-type", default="Regular Season")
    parser.add_argument("--max-shotchart-players", type=int, default=12, help="Number of players per team to include in shot_zones.csv")
    args = parser.parse_args()

    SNAPSHOT_DIR.mkdir(parents=True, exist_ok=True)
    RAW_DIR.mkdir(parents=True, exist_ok=True)

    status_rows = []

    roster, status = fetch_roster(args.season)
    status_rows.extend(status)
    write_table(roster, "roster.csv")

    team_stats, status = fetch_team_stats(args.season, args.season_type)
    status_rows.extend(status)
    write_table(team_stats, "team_stats.csv")

    player_stats, status = fetch_player_stats(args.season, args.season_type, roster)
    status_rows.extend(status)

    bref, status = fetch_bref_advanced(args.season)
    status_rows.extend(status)

    if not bref.empty:
        player_stats = merge_bref(player_stats, bref)

    write_table(player_stats, "player_stats.csv")

    lineups, status = fetch_lineups(args.season, args.season_type)
    status_rows.extend(status)
    write_table(lineups, "lineups.csv")

    shot_zones, status = fetch_shot_zones(player_stats, args.season, args.season_type, args.max_shotchart_players)
    status_rows.extend(status)
    write_table(
        shot_zones,
        "shot_zones.csv",
        columns=["player_id", "player", "team", "zone", "loc_x", "loc_y", "fg_pct", "efg_pct", "shot_volume", "volume_rank"],
    )

    pnr, status = fetch_pnr_play_types(args.season, args.season_type)
    status_rows.extend(status)
    write_table(
        pnr,
        "pnr_play_types.csv",
        columns=["team", "player", "play_type", "possessions", "ppp", "percentile", "tov_pct", "score_freq"],
    )

    matchups, status = create_empty_matchups()
    status_rows.extend(status)
    write_table(matchups, "matchups.csv")

    created_at = datetime.now(timezone.utc).isoformat()

    metadata = pd.DataFrame(
        [
            {
                "snapshot_created_utc": created_at,
                "season": args.season,
                "season_type": args.season_type,
                "max_shotchart_players_per_team": args.max_shotchart_players,
                "data_policy": "snapshot_only_no_sample_fallback_no_live_requests_on_page_load",
            }
        ]
    )
    write_table(metadata, "snapshot_metadata.csv")

    manifest = pd.DataFrame(status_rows, columns=["Table", "Source", "Status", "Details"])
    write_table(manifest, "source_manifest.csv")

    write_snapshot_readme(args.season, args.season_type, created_at)

    print("Snapshot complete.")
    print(SNAPSHOT_DIR.resolve())
    print(manifest)


if __name__ == "__main__":
    main()
