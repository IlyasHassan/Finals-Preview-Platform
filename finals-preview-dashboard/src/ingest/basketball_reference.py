from __future__ import annotations

from io import StringIO
import pandas as pd

from src.config import SEASON
from src.ingest.http import cached_session


def _season_end_year(season: str) -> int:
    try:
        return int(season.split("-")[0]) + 1
    except Exception:
        return 2026


def fetch_bref_advanced(season: str = SEASON) -> tuple[pd.DataFrame, str]:
    year = _season_end_year(season)
    url = f"https://www.basketball-reference.com/leagues/NBA_{year}_advanced.html"

    try:
        session = cached_session("data/raw/bref_cache", expire_after=900)
        response = session.get(url, timeout=20)
        response.raise_for_status()
        tables = pd.read_html(StringIO(response.text))
    except Exception as exc:
        return pd.DataFrame(), f"Basketball-Reference unavailable: {exc}"

    if not tables:
        return pd.DataFrame(), "Basketball-Reference returned no tables."

    df = tables[0]
    if "Rk" in df.columns:
        df = df[df["Rk"] != "Rk"].copy()

    rename_map = {
        "Player": "player",
        "PER": "per",
        "TS%": "ts_pct_bref",
        "USG%": "usg_pct_bref",
        "BPM": "bpm",
        "VORP": "vorp",
        "WS/48": "ws48",
    }

    keep = [col for col in rename_map if col in df.columns]
    if not keep:
        return pd.DataFrame(), "Basketball-Reference advanced table missing expected columns."

    out = df[keep].rename(columns=rename_map)

    for col in ["per", "ts_pct_bref", "usg_pct_bref", "bpm", "vorp", "ws48"]:
        if col in out.columns:
            out[col] = pd.to_numeric(out[col], errors="coerce")

    return out.drop_duplicates(subset=["player"], keep="first"), "Basketball-Reference advanced table loaded."
