from __future__ import annotations

import pandas as pd

from src.config import SEASON, SEASON_TYPE
from src.ingest.nba_live import (
    fetch_rosters,
    fetch_team_stats,
    fetch_player_stats,
    merge_bref_advanced,
    fetch_lineups,
    fetch_synergy_pnr,
)
from src.ingest.basketball_reference import fetch_bref_advanced
from src.ingest.pbpstats_client import fetch_pbpstats_totals


def load_live_core(season: str = SEASON, season_type: str = SEASON_TYPE):
    status = []
    tables = {}

    roster, msg = fetch_rosters(season)
    tables["roster"] = roster
    status.append({"Table": "roster", "Source": "NBA CommonTeamRoster", "Status": "Live" if not roster.empty else "Unavailable", "Details": msg})

    team_stats, msg = fetch_team_stats(season, season_type)
    tables["team_stats"] = team_stats
    status.append({"Table": "team_stats", "Source": "NBA LeagueDashTeamStats", "Status": "Live" if not team_stats.empty else "Unavailable", "Details": msg})

    player_stats, msg = fetch_player_stats(season, season_type, roster)
    status.append({"Table": "player_stats_nba", "Source": "NBA LeagueDashPlayerStats", "Status": "Live" if not player_stats.empty else "Unavailable", "Details": msg})

    bref, bref_msg = fetch_bref_advanced(season)
    status.append({"Table": "basketball_reference_advanced", "Source": "Basketball-Reference", "Status": "Live" if not bref.empty else "Unavailable", "Details": bref_msg})

    if not player_stats.empty and not bref.empty:
        player_stats = merge_bref_advanced(player_stats, bref)

    tables["player_stats"] = player_stats

    lineups, msg = fetch_lineups(season, season_type)
    tables["lineups"] = lineups
    status.append({"Table": "lineups", "Source": "NBA LeagueDashLineups", "Status": "Live" if not lineups.empty else "Unavailable", "Details": msg})

    pnr, msg = fetch_synergy_pnr(season, season_type)
    tables["pnr"] = pnr
    status.append({"Table": "pnr_play_types", "Source": "NBA SynergyPlayTypes", "Status": "Live" if not pnr.empty else "Unavailable", "Details": msg})

    pbp_team, msg = fetch_pbpstats_totals("Team", season, season_type)
    tables["pbp_team"] = pbp_team
    status.append({"Table": "pbpstats_team", "Source": "PBPStats get-totals", "Status": "Live" if not pbp_team.empty else "Unavailable", "Details": msg})

    # Exact player-vs-player matchup matrix is intentionally not fabricated.
    tables["matchups"] = pd.DataFrame()
    status.append({
        "Table": "matchups",
        "Source": "NBA matchup endpoints",
        "Status": "Unavailable",
        "Details": "Exact live matchup endpoint integration is not included in this live-only build. No sample/proxy matchup data is shown.",
    })

    return tables, pd.DataFrame(status)
