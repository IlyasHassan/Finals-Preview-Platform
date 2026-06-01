import os

SEASON = os.getenv("NBA_SEASON", "2025-26")
SEASON_TYPE = os.getenv("NBA_SEASON_TYPE", "Regular Season")

TEAM_IDS = {
    "Knicks": 1610612752,
    "Spurs": 1610612759,
}

TEAM_ABBREVIATIONS = {
    "Knicks": "NYK",
    "Spurs": "SAS",
}

TEAM_FULL_NAMES = {
    "Knicks": "New York Knicks",
    "Spurs": "San Antonio Spurs",
}

SAMPLE_PLAYER_NAMES = [
    "Jalen Brunson",
    "Victor Wembanyama",
    "OG Anunoby",
    "Devin Vassell",
    "Josh Hart",
    "Chris Paul",
    "Jeremy Sochan",
    "Mitchell Robinson",
]
