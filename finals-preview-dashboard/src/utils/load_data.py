from pathlib import Path
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


def load_all_sample_data(base_path: str | Path | None = None) -> dict[str, pd.DataFrame]:
    if base_path is None:
        base_path = get_project_root() / "data" / "sample"
    else:
        base_path = Path(base_path)

    data = {}
    missing = []

    for key, filename in REQUIRED_FILES.items():
        path = base_path / filename
        if not path.exists():
            missing.append(str(path))
            continue
        data[key] = pd.read_csv(path)

    if missing:
        raise FileNotFoundError(
            "Missing required sample data files:\n" + "\n".join(missing)
        )

    return data
