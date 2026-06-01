from __future__ import annotations

from pathlib import Path
import time
import pandas as pd
import requests

ESPN_BASE = "https://site.api.espn.com/apis/site/v2/sports/basketball/nba"

TEAM_ALIASES = {
    "Knicks": ["ny", "nyk", "new-york-knicks", "18"],
    "Spurs": ["sa", "sas", "san-antonio-spurs", "24"],
}

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/124.0.0.0 Safari/537.36"
    ),
    "Accept": "application/json,text/plain,*/*",
}


def _get_json(url: str, timeout: int = 20) -> dict:
    response = requests.get(url, headers=HEADERS, timeout=timeout)
    response.raise_for_status()
    return response.json()


def fetch_espn_teams() -> tuple[pd.DataFrame, list[tuple[str, str, str, str]]]:
    """Fetch public ESPN team metadata.

    ESPN's site API is useful for rosters, team identity, logos, colors, and
    player bio metadata. It should not be treated as a replacement for NBA.com
    shot charts, lineup stats, or play-type data.
    """
    url = f"{ESPN_BASE}/teams"

    try:
        payload = _get_json(url)
    except Exception as exc:
        return pd.DataFrame(), [("espn_teams", "ESPN site API", "Failed", repr(exc))]

    rows = []

    for item in payload.get("sports", [{}])[0].get("leagues", [{}])[0].get("teams", []):
        team = item.get("team", item)

        rows.append(
            {
                "espn_team_id": team.get("id"),
                "uid": team.get("uid"),
                "slug": team.get("slug"),
                "abbreviation": team.get("abbreviation"),
                "display_name": team.get("displayName"),
                "short_display_name": team.get("shortDisplayName"),
                "name": team.get("name"),
                "location": team.get("location"),
                "color": team.get("color"),
                "alternate_color": team.get("alternateColor"),
                "logo": (team.get("logos") or [{}])[0].get("href"),
            }
        )

    df = pd.DataFrame(rows)

    # Keep the two teams for this project when possible, but still let the
    # full metadata help with alias discovery if ESPN changes abbreviations.
    if not df.empty:
        keep = df[
            df["display_name"].fillna("").str.contains("Knicks|Spurs", case=False, regex=True)
            | df["abbreviation"].fillna("").str.lower().isin(["ny", "nyk", "sa", "sas"])
        ].copy()

        if not keep.empty:
            df = keep

    return df, [("espn_teams", "ESPN site API teams", "Loaded" if not df.empty else "Unavailable", f"{len(df)} rows")]


def _parse_espn_roster_payload(payload: dict, team_name: str) -> pd.DataFrame:
    rows = []

    for athlete in payload.get("athletes", []):
        pos = athlete.get("position") or {}
        headshot = athlete.get("headshot") or {}
        status = athlete.get("status") or {}
        contract = athlete.get("contract") or {}
        exp = athlete.get("experience") or {}
        birth_place = athlete.get("birthPlace") or {}

        rows.append(
            {
                "espn_id": athlete.get("id"),
                "player": athlete.get("displayName") or athlete.get("fullName"),
                "team": team_name,
                "position": pos.get("abbreviation") or pos.get("displayName"),
                "jersey": athlete.get("jersey"),
                "height": athlete.get("displayHeight"),
                "weight": athlete.get("displayWeight"),
                "age": athlete.get("age"),
                "date_of_birth": athlete.get("dateOfBirth"),
                "birth_city": birth_place.get("city"),
                "birth_state": birth_place.get("state"),
                "birth_country": birth_place.get("country"),
                "college": (athlete.get("college") or {}).get("name"),
                "experience": exp.get("years"),
                "status": status.get("name") or status.get("type"),
                "headshot": headshot.get("href"),
                "espn_url": next(
                    (
                        link.get("href")
                        for link in athlete.get("links", [])
                        if "playercard" in link.get("rel", [])
                    ),
                    None,
                ),
                "salary": contract.get("salary"),
            }
        )

    return pd.DataFrame(rows)


def fetch_espn_roster_for_team(team_name: str) -> tuple[pd.DataFrame, list[tuple[str, str, str, str]]]:
    """Try multiple public ESPN roster aliases.

    ESPN's site API aliases are not perfectly standardized across sports. For
    the Knicks, `ny` is known to work. For Spurs, `sa` is the likely ESPN alias.
    The code tries a few candidates and stops at the first non-empty roster.
    """
    attempts = []

    for alias in TEAM_ALIASES.get(team_name, []):
        url = f"{ESPN_BASE}/teams/{alias}/roster"
        try:
            payload = _get_json(url)
            df = _parse_espn_roster_payload(payload, team_name)
            attempts.append((alias, len(df)))

            if not df.empty:
                return df, [("espn_roster", "ESPN site API roster", "Loaded", f"{team_name}: alias `{alias}`, {len(df)} rows")]

        except Exception as exc:
            attempts.append((alias, repr(exc)))

        time.sleep(0.25)

    return pd.DataFrame(), [("espn_roster", "ESPN site API roster", "Failed", f"{team_name}: all aliases failed or empty: {attempts}")]


def fetch_espn_rosters() -> tuple[pd.DataFrame, list[tuple[str, str, str, str]]]:
    frames = []
    status = []

    for team_name in TEAM_ALIASES:
        df, rows = fetch_espn_roster_for_team(team_name)
        status.extend(rows)

        if not df.empty:
            frames.append(df)

    if not frames:
        return pd.DataFrame(), status

    return pd.concat(frames, ignore_index=True), status
