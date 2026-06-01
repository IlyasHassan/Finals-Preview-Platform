from pathlib import Path
import pandas as pd

from src.config import REQUIRED_SNAPSHOT_FILES


def project_root() -> Path:
    return Path(__file__).resolve().parents[2]


def snapshot_dir() -> Path:
    return project_root() / "data" / "snapshot"


def missing_snapshot_files() -> list[str]:
    base = snapshot_dir()
    return [
        filename
        for filename in REQUIRED_SNAPSHOT_FILES.values()
        if not (base / filename).exists()
    ]


def snapshot_exists() -> bool:
    return len(missing_snapshot_files()) == 0


def load_snapshot() -> dict[str, pd.DataFrame]:
    missing = missing_snapshot_files()

    if missing:
        raise FileNotFoundError(
            "Snapshot files are missing. Run scripts/build_snapshot.py first. Missing: "
            + ", ".join(missing)
        )

    base = snapshot_dir()
    data = {}

    for key, filename in REQUIRED_SNAPSHOT_FILES.items():
        data[key] = pd.read_csv(base / filename)

    return data
