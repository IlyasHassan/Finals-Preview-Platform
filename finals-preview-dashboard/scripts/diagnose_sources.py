from __future__ import annotations

import argparse
import sys
from pathlib import Path
import pandas as pd

sys.path.append(str(Path(__file__).resolve().parents[1]))

from scripts.common_snapshot import (
    reset_attempt_dir,
    write_attempt_manifest,
    write_error_log,
    fetch_roster_with_espn_backup,
    fetch_team_stats,
    fetch_player_stats,
    fetch_lineups,
    fetch_pnr_play_types,
    fetch_bref_advanced,
)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--season", default="2025-26")
    parser.add_argument("--season-type", default="Regular Season")
    args = parser.parse_args()

    reset_attempt_dir()
    status_rows = []
    errors = []

    print("Diagnosing NBA/Basketball-Reference sources...")

    roster, espn_teams, espn_rosters, status = fetch_roster_with_espn_backup(args.season)
    status_rows.extend(status)
    print(f"roster rows: {len(roster)}")
    print(f"espn_teams rows: {len(espn_teams)}")
    print(f"espn_rosters rows: {len(espn_rosters)}")

    team_stats, status = fetch_team_stats(args.season, args.season_type)
    status_rows.extend(status)
    print(f"team_stats rows: {len(team_stats)}")

    player_stats, status = fetch_player_stats(args.season, args.season_type, roster)
    status_rows.extend(status)
    print(f"player_stats rows: {len(player_stats)}")

    lineups, status = fetch_lineups(args.season, args.season_type)
    status_rows.extend(status)
    print(f"lineups rows: {len(lineups)}")

    pnr, status = fetch_pnr_play_types(args.season, args.season_type)
    status_rows.extend(status)
    print(f"pnr rows: {len(pnr)}")

    bref, status = fetch_bref_advanced(args.season)
    status_rows.extend(status)
    print(f"basketball-reference rows: {len(bref)}")

    for required_name, df in [
        ("roster", roster),
        ("team_stats", team_stats),
        ("player_stats", player_stats),
    ]:
        if df.empty:
            errors.append(f"{required_name} is empty. The core snapshot cannot be built.")

    write_attempt_manifest(status_rows)
    write_error_log(errors)

    manifest = pd.DataFrame(status_rows, columns=["Table", "Source", "Status", "Details"])
    print("\\nSource manifest:")
    print(manifest.to_string(index=False))

    if errors:
        print("\\nErrors:")
        for error in errors:
            print(f"- {error}")
        print("\\nSaved details to data/raw/latest_build_attempt/")
        raise SystemExit(1)

    print("\\nDiagnosis passed for core tables.")
    print("Saved details to data/raw/latest_build_attempt/")


if __name__ == "__main__":
    main()
