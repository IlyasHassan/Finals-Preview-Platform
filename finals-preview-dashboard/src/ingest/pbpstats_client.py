from __future__ import annotations

import pandas as pd

from src.config import SEASON, SEASON_TYPE
from src.ingest.cache import fetch_json

PBPSTATS_BASE_URL = "https://api.pbpstats.com"


def fetch_pbpstats_totals(entity_type: str = "Team", season: str = SEASON, season_type: str = SEASON_TYPE) -> pd.DataFrame:
    params = {
        "EntityType": entity_type,
        "Season": season,
        "SeasonType": season_type,
        "Type": entity_type,
    }

    try:
        payload = fetch_json(f"{PBPSTATS_BASE_URL}/get-totals/nba", params=params, timeout=20)
    except Exception:
        return pd.DataFrame()

    if isinstance(payload, dict):
        for key in ["results", "data", "multi_row_table_data"]:
            value = payload.get(key)
            if isinstance(value, list):
                return pd.DataFrame(value)
            if isinstance(value, dict):
                try:
                    return pd.DataFrame(value.values())
                except Exception:
                    pass

    return pd.DataFrame()


def fetch_lineup_enrichment(season: str = SEASON, season_type: str = SEASON_TYPE) -> pd.DataFrame:
    return fetch_pbpstats_totals(entity_type="Lineup", season=season, season_type=season_type)
