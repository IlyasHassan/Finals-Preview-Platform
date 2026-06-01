from pathlib import Path
from typing import Dict
import pandas as pd

REQUIRED_FILES = {
    "team_stats": "team_stats.csv",
    "player_stats": "player_stats.csv",
    "shot_zones": "shot_zones.csv",
    "lineups": "lineups.csv",
    "pnr_duos": "pnr_duos.csv",
    "matchups": "matchups.csv",
}


def get_project_root() -> Path:
    return Path(__file__).resolve().parents[2]


def load_table_set(base_path, required_files=REQUIRED_FILES) -> Dict[str, pd.DataFrame]:
    base_path = Path(base_path)
    data = {}
    missing = []

    for key, filename in required_files.items():
        path = base_path / filename
        if not path.exists():
            missing.append(str(path))
            continue
        data[key] = pd.read_csv(path)

    if missing:
        raise FileNotFoundError("Missing required data files:\n" + "\n".join(missing))

    return data


def load_all_sample_data(base_path=None) -> Dict[str, pd.DataFrame]:
    if base_path is None:
        base_path = get_project_root() / "data" / "sample"
    return load_table_set(base_path)


def load_live_snapshot_or_sample() -> Dict[str, pd.DataFrame]:
    root = get_project_root()
    live_path = root / "data" / "live"
    try:
        return load_table_set(live_path)
    except Exception:
        return load_all_sample_data()
