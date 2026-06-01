from pathlib import Path
import pandas as pd

from src.config import REQUIRED_CORE_FILES, OPTIONAL_FILES


def project_root() -> Path:
    return Path(__file__).resolve().parents[2]


def snapshot_dir() -> Path:
    return project_root() / "data" / "snapshot"


def missing_core_files() -> list[str]:
    base = snapshot_dir()
    return [
        filename
        for filename in REQUIRED_CORE_FILES.values()
        if not (base / filename).exists()
    ]


def snapshot_exists() -> bool:
    return len(missing_core_files()) == 0


def load_snapshot() -> dict[str, pd.DataFrame]:
    missing = missing_core_files()

    if missing:
        raise FileNotFoundError(
            "Core snapshot files are missing. Run scripts/build_snapshot.py first. Missing: "
            + ", ".join(missing)
        )

    base = snapshot_dir()
    data = {}

    for key, filename in REQUIRED_CORE_FILES.items():
        data[key] = pd.read_csv(base / filename)

    for key, filename in OPTIONAL_FILES.items():
        path = base / filename
        data[key] = pd.read_csv(path) if path.exists() else pd.DataFrame()

    return data
