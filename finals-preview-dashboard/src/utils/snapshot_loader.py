from pathlib import Path
import pandas as pd

from src.config import REQUIRED_CORE_FILES, OPTIONAL_FILES


EXPECTED_COLUMNS = {
    "team_stats": [
        "team",
        "ortg",
        "drtg",
        "net_rating",
        "pace",
        "efg_pct",
        "ts_pct",
        "tov_pct",
        "oreb_pct",
        "dreb_pct",
        "primary_source",
        "off_rank",
        "def_rank",
        "reb_rank",
        "pace_rank",
        "shooting_rank",
        "turnover_rank",
    ],
    "player_stats": [
        "player_id",
        "player",
        "team",
        "gp",
        "min",
        "pts",
        "reb",
        "ast",
        "stl",
        "blk",
        "fg_pct",
        "fg3_pct",
        "ft_pct",
        "ts_pct",
        "usg_pct",
        "net_rating",
        "position",
        "jersey",
        "height",
        "weight",
        "age",
        "exp",
        "school",
        "primary_source",
        "per",
        "ts_pct_reference",
        "usg_pct_reference",
        "bpm",
        "vorp",
        "ws48",
    ],
    "roster": [
        "player_id",
        "player",
        "team",
        "position",
        "jersey",
        "height",
        "weight",
        "birth_date",
        "age",
        "exp",
        "school",
    ],
    "lineups": [
        "lineup",
        "team",
        "min",
        "ortg",
        "drtg",
        "net_rating",
        "efg_pct",
        "tov_pct",
        "reb_pct",
        "plus_minus",
    ],
    "pnr_play_types": [
        "team",
        "player",
        "play_type",
        "possessions",
        "ppp",
        "percentile",
        "tov_pct",
        "score_freq",
    ],
    "matchups": [
        "defender",
        "team_defense",
        "offender",
        "team_offense",
        "possessions",
        "pts_allowed",
        "fg_pct_allowed",
        "fg_pct_suppression",
        "notes",
    ],
    "source_manifest": ["Table", "Source", "Status", "Details"],
    "snapshot_metadata": [
        "snapshot_created_utc",
        "season",
        "season_type",
        "max_shotchart_players_per_team",
        "shotcharts_included",
        "data_policy",
    ],
    "shot_zones": [
        "player_id",
        "player",
        "team",
        "zone",
        "loc_x",
        "loc_y",
        "fg_pct",
        "efg_pct",
        "shot_volume",
        "volume_rank",
        "primary_source",
    ],
    "espn_teams": [
        "espn_team_id",
        "uid",
        "slug",
        "abbreviation",
        "display_name",
        "short_display_name",
        "name",
        "location",
        "color",
        "alternate_color",
        "logo",
    ],
    "espn_rosters": [
        "espn_id",
        "player",
        "team",
        "position",
        "jersey",
        "height",
        "weight",
        "age",
        "date_of_birth",
        "birth_city",
        "birth_state",
        "birth_country",
        "college",
        "experience",
        "status",
        "headshot",
        "espn_url",
        "salary",
    ],
}


CRITICAL_NONEMPTY_TABLES = {"team_stats", "player_stats", "roster"}


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


def safe_read_csv(path: Path, key: str) -> pd.DataFrame:
    """Read a snapshot CSV safely.

    Some tables are allowed to be empty when their source fails, especially:
    lineups, pnr_play_types, matchups, and shot_zones.

    A zero-byte/headerless file should not crash the public app. It is returned
    as an empty DataFrame with the expected schema, and the UI will show a warning.
    """
    columns = EXPECTED_COLUMNS.get(key, [])

    if not path.exists():
        return pd.DataFrame(columns=columns)

    try:
        if path.stat().st_size == 0:
            return pd.DataFrame(columns=columns)

        return pd.read_csv(path)

    except pd.errors.EmptyDataError:
        return pd.DataFrame(columns=columns)


def find_invalid_critical_tables(data: dict[str, pd.DataFrame]) -> list[str]:
    invalid = []
    for key in CRITICAL_NONEMPTY_TABLES:
        df = data.get(key, pd.DataFrame())
        if df.empty:
            invalid.append(key)
    return invalid


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
        data[key] = safe_read_csv(base / filename, key)

    for key, filename in OPTIONAL_FILES.items():
        data[key] = safe_read_csv(base / filename, key)

    return data
