from __future__ import annotations

import argparse
import shutil
import sys
from datetime import datetime, timezone
from pathlib import Path

import pandas as pd

sys.path.append(str(Path(__file__).resolve().parents[1]))

from scripts.common_snapshot import (
    SNAPSHOT_DIR,
    ATTEMPT_DIR,
    reset_attempt_dir,
    write_attempt_manifest,
    write_error_log,
    write_table,
    validate_non_empty,
    fetch_roster_with_espn_backup,
    fetch_team_stats,
    fetch_player_stats,
    fetch_bref_advanced,
    merge_bref,
    fetch_lineups,
    fetch_pnr_play_types,
    fetch_shot_zones,
    empty_matchups,
    write_snapshot_readme,
)


def atomic_replace_snapshot(temp_dir: Path, include_shotcharts: bool):
    SNAPSHOT_DIR.mkdir(parents=True, exist_ok=True)

    # Copy only files created in the temp build. This preserves existing shot_zones
    # if the user is rebuilding core with --skip-shotcharts.
    for file_path in temp_dir.glob("*"):
        if file_path.is_file():
            if file_path.name == "shot_zones.csv" or include_shotcharts:
                shutil.copy2(file_path, SNAPSHOT_DIR / file_path.name)
            elif file_path.name != "shot_zones.csv":
                shutil.copy2(file_path, SNAPSHOT_DIR / file_path.name)


def build_core(args, temp_dir: Path, status_rows: list, errors: list):
    roster, espn_teams, espn_rosters, status = fetch_roster_with_espn_backup(args.season)
    status_rows.extend(status)
    validate_non_empty("roster", roster, errors)
    write_table(roster, temp_dir, "roster.csv")
    write_table(espn_teams, temp_dir, "espn_teams.csv")
    write_table(espn_rosters, temp_dir, "espn_rosters.csv")

    team_stats, status = fetch_team_stats(args.season, args.season_type)
    status_rows.extend(status)
    validate_non_empty("team_stats", team_stats, errors)
    write_table(team_stats, temp_dir, "team_stats.csv")

    player_stats, status = fetch_player_stats(args.season, args.season_type, roster)
    status_rows.extend(status)
    validate_non_empty("player_stats", player_stats, errors)

    bref, status = fetch_bref_advanced(args.season)
    status_rows.extend(status)
    if not bref.empty:
        player_stats = merge_bref(player_stats, bref)

    write_table(player_stats, temp_dir, "player_stats.csv")

    lineups, status = fetch_lineups(args.season, args.season_type)
    status_rows.extend(status)
    if lineups.empty:
        status_rows.append(("lineups_validation", "Builder", "Warning", "Lineups empty. Core build continues, but Lineups page will be empty."))
    write_table(
        lineups,
        temp_dir,
        "lineups.csv",
        columns=["lineup", "team", "min", "ortg", "drtg", "net_rating", "efg_pct", "tov_pct", "reb_pct", "plus_minus"],
    )

    pnr, status = fetch_pnr_play_types(args.season, args.season_type)
    status_rows.extend(status)
    if pnr.empty:
        status_rows.append(("pnr_validation", "Builder", "Warning", "PnR play-type table empty. Core build continues, but PnR page will be empty."))
    write_table(
        pnr,
        temp_dir,
        "pnr_play_types.csv",
        columns=["team", "player", "play_type", "possessions", "ppp", "percentile", "tov_pct", "score_freq"],
    )

    matchups, status = empty_matchups()
    status_rows.extend(status)
    write_table(matchups, temp_dir, "matchups.csv")

    return player_stats


def build_shotcharts(args, temp_dir: Path, player_stats: pd.DataFrame, status_rows: list, errors: list):
    if player_stats is None or player_stats.empty:
        existing_player_stats = SNAPSHOT_DIR / "player_stats.csv"
        if existing_player_stats.exists():
            player_stats = pd.read_csv(existing_player_stats)
        else:
            errors.append("Cannot build shot charts because player_stats.csv is missing or empty.")
            return

    shot_zones, status = fetch_shot_zones(
        player_stats,
        args.season,
        args.season_type,
        args.max_shotchart_players,
    )
    status_rows.extend(status)

    if shot_zones.empty:
        errors.append("shot_zones is empty. ShotChartDetail failed for all selected players.")

    write_table(
        shot_zones,
        temp_dir,
        "shot_zones.csv",
        columns=["player_id", "player", "team", "zone", "loc_x", "loc_y", "fg_pct", "efg_pct", "shot_volume", "volume_rank"],
    )


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--season", default="2025-26")
    parser.add_argument("--season-type", default="Regular Season")
    parser.add_argument("--skip-shotcharts", action="store_true", help="Build core tables only. Fastest option.")
    parser.add_argument("--only-shotcharts", action="store_true", help="Only build shot_zones.csv using existing player_stats.csv.")
    parser.add_argument("--max-shotchart-players", type=int, default=6, help="Players per team for shot chart pulls.")
    args = parser.parse_args()

    reset_attempt_dir()

    temp_dir = ATTEMPT_DIR / "snapshot_candidate"
    temp_dir.mkdir(parents=True, exist_ok=True)

    status_rows = []
    errors = []
    player_stats = pd.DataFrame()

    if not args.only_shotcharts:
        player_stats = build_core(args, temp_dir, status_rows, errors)

    include_shotcharts = not args.skip_shotcharts
    if include_shotcharts:
        build_shotcharts(args, temp_dir, player_stats, status_rows, errors)

    created_at = datetime.now(timezone.utc).isoformat()

    metadata = pd.DataFrame(
        [
            {
                "snapshot_created_utc": created_at,
                "season": args.season,
                "season_type": args.season_type,
                "max_shotchart_players_per_team": args.max_shotchart_players if include_shotcharts else 0,
                "shotcharts_included": include_shotcharts,
                "data_policy": "snapshot_only_no_sample_fallback_no_live_requests_on_page_load",
            }
        ]
    )
    write_table(metadata, temp_dir, "snapshot_metadata.csv")

    manifest = pd.DataFrame(status_rows, columns=["Table", "Source", "Status", "Details"])
    write_table(manifest, temp_dir, "source_manifest.csv")
    write_attempt_manifest(status_rows)

    write_snapshot_readme(temp_dir, args.season, args.season_type, created_at)

    if errors:
        write_error_log(errors)
        print("\\nSnapshot build failed. Existing data/snapshot was NOT overwritten.")
        print("\\nErrors:")
        for error in errors:
            print(f"- {error}")
        print("\\nSee:")
        print("- data/raw/latest_build_attempt/source_manifest.csv")
        print("- data/raw/latest_build_attempt/build_errors.txt")
        raise SystemExit(1)

    atomic_replace_snapshot(temp_dir, include_shotcharts=include_shotcharts)

    print("\\nSnapshot build complete.")
    print(f"Saved to: {SNAPSHOT_DIR.resolve()}")
    print("\\nSource manifest:")
    print(manifest.to_string(index=False))


if __name__ == "__main__":
    main()
