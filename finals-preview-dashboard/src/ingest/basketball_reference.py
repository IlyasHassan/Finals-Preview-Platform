from __future__ import annotations

from io import StringIO
from typing import Iterable

import pandas as pd

from src.config import SEASON


def _season_end_year(season: str) -> int:
    try:
        return int(season.split("-")[0]) + 1
    except Exception:
        return 2026


def fetch_bref_advanced(season: str = SEASON, player_names: Iterable[str] | None = None) -> pd.DataFrame:
    try:
        import requests_cache
    except Exception:
        return pd.DataFrame()

    year = _season_end_year(season)
    url = f"https://www.basketball-reference.com/leagues/NBA_{year}_advanced.html"

    try:
        session = requests_cache.CachedSession("data/raw/bref_cache", expire_after=6 * 60 * 60)
        response = session.get(
            url,
            headers={
                "User-Agent": (
                    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                    "AppleWebKit/537.36 (KHTML, like Gecko) "
                    "Chrome/124.0.0.0 Safari/537.36"
                )
            },
            timeout=20,
        )
        response.raise_for_status()
        tables = pd.read_html(StringIO(response.text))
    except Exception:
        return pd.DataFrame()

    if not tables:
        return pd.DataFrame()

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
        return pd.DataFrame()

    out = df[keep].rename(columns=rename_map)

    for col in ["per", "ts_pct_bref", "usg_pct_bref", "bpm", "vorp", "ws48"]:
        if col in out.columns:
            out[col] = pd.to_numeric(out[col], errors="coerce")

    if player_names is not None:
        wanted = set(player_names)
        out = out[out["player"].isin(wanted)].copy()

    return out.drop_duplicates(subset=["player"], keep="first")
