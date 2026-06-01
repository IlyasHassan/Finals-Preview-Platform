from __future__ import annotations

import pandas as pd
from src.config import SEASON, SEASON_TYPE
from src.ingest.http import cached_session


PBPSTATS_BASE_URL = "https://api.pbpstats.com"


def fetch_pbpstats_totals(entity_type: str = "Team", season: str = SEASON, season_type: str = SEASON_TYPE) -> tuple[pd.DataFrame, str]:
    params = {
        "EntityType": entity_type,
        "Season": season,
        "SeasonType": season_type,
        "Type": entity_type,
    }

    try:
        session = cached_session("data/raw/pbpstats_cache", expire_after=900)
        response = session.get(f"{PBPSTATS_BASE_URL}/get-totals/nba", params=params, timeout=20)
        response.raise_for_status()
        payload = response.json()
    except Exception as exc:
        return pd.DataFrame(), f"PBPStats unavailable: {exc}"

    if isinstance(payload, dict):
        for key in ["results", "data", "multi_row_table_data"]:
            value = payload.get(key)
            if isinstance(value, list):
                return pd.DataFrame(value), "PBPStats totals loaded."
            if isinstance(value, dict):
                try:
                    return pd.DataFrame(value.values()), "PBPStats totals loaded."
                except Exception:
                    pass

    return pd.DataFrame(), "PBPStats response shape was not recognized."
