from __future__ import annotations

import pandas as pd

from src.config import SEASON, SEASON_TYPE
from src.ingest.cache import fetch_json


PBPSTATS_BASE_URL = "https://api.pbpstats.com"


def fetch_pbpstats_totals(
    entity_type: str = "Team",
    season: str = SEASON,
    season_type: str = SEASON_TYPE,
) -> pd.DataFrame:
    """Lightweight PBPStats API client.

    PBPStats endpoint parameters can change, so this client is intentionally
    defensive. If the response shape is not recognized, it returns an empty
    DataFrame and the app falls back to sample data.
    """
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

    # Common response shapes include dictionaries containing "results" or "data".
    if isinstance(payload, dict):
        for key in ["results", "data", "multi_row_table_data"]:
            value = payload.get(key)
            if isinstance(value, list):
                return pd.DataFrame(value)
            if isinstance(value, dict):
                # Some responses are keyed by entity id.
                try:
                    return pd.DataFrame(value.values())
                except Exception:
                    pass

    return pd.DataFrame()


def fetch_lineup_enrichment(season: str = SEASON, season_type: str = SEASON_TYPE) -> pd.DataFrame:
    """Placeholder for lineup-on-floor enrichment.

    This returns whatever PBPStats exposes through totals. A future hardening pass
    can join stints/play-by-play to lineups for richer matchup modeling.
    """
    return fetch_pbpstats_totals(entity_type="Lineup", season=season, season_type=season_type)
