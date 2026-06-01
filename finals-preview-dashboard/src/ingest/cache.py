from pathlib import Path
import json
import time
from typing import Any

import requests
import requests_cache


DEFAULT_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/124.0.0.0 Safari/537.36"
    ),
    "Accept-Language": "en-US,en;q=0.9",
}


def get_cached_session(cache_name: str = "data/raw/http_cache", expire_after: int = 3600):
    Path(cache_name).parent.mkdir(parents=True, exist_ok=True)
    session = requests_cache.CachedSession(cache_name, expire_after=expire_after)
    session.headers.update(DEFAULT_HEADERS)
    return session


def fetch_json(url: str, params: dict | None = None, timeout: int = 20, sleep_seconds: float = 0.6) -> dict[str, Any]:
    session = get_cached_session()
    response = session.get(url, params=params or {}, timeout=timeout)
    time.sleep(sleep_seconds)
    response.raise_for_status()
    return response.json()


def save_json(payload: dict, path: str | Path) -> None:
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2), encoding="utf-8")
