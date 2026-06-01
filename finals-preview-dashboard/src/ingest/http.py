from pathlib import Path
import time
import requests_cache

DEFAULT_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/124.0.0.0 Safari/537.36"
    ),
    "Accept-Language": "en-US,en;q=0.9",
}


def cached_session(cache_name="data/raw/http_cache", expire_after=900):
    Path(cache_name).parent.mkdir(parents=True, exist_ok=True)
    session = requests_cache.CachedSession(cache_name, expire_after=expire_after)
    session.headers.update(DEFAULT_HEADERS)
    return session


def nba_headers():
    return {
        "Host": "stats.nba.com",
        "Connection": "keep-alive",
        "Accept": "application/json, text/plain, */*",
        "x-nba-stats-token": "true",
        "User-Agent": DEFAULT_HEADERS["User-Agent"],
        "x-nba-stats-origin": "stats",
        "Origin": "https://www.nba.com",
        "Referer": "https://www.nba.com/",
        "Accept-Language": "en-US,en;q=0.9",
    }


def polite_pause(seconds=0.4):
    time.sleep(seconds)
