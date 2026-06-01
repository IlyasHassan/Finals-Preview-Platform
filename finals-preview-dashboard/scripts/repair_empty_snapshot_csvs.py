from pathlib import Path
import sys

sys.path.append(str(Path(__file__).resolve().parents[1]))

from src.utils.snapshot_loader import EXPECTED_COLUMNS, snapshot_dir

base = snapshot_dir()
base.mkdir(parents=True, exist_ok=True)

for key, columns in EXPECTED_COLUMNS.items():
    filename = {
        "team_stats": "team_stats.csv",
        "player_stats": "player_stats.csv",
        "roster": "roster.csv",
        "lineups": "lineups.csv",
        "pnr_play_types": "pnr_play_types.csv",
        "matchups": "matchups.csv",
        "source_manifest": "source_manifest.csv",
        "snapshot_metadata": "snapshot_metadata.csv",
        "shot_zones": "shot_zones.csv",
        "espn_teams": "espn_teams.csv",
        "espn_rosters": "espn_rosters.csv",
    }.get(key)

    if not filename:
        continue

    path = base / filename
    if path.exists() and path.stat().st_size == 0:
        path.write_text(",".join(columns) + "\n", encoding="utf-8")
        print(f"Repaired empty file with headers: {path}")

print("Repair complete.")
