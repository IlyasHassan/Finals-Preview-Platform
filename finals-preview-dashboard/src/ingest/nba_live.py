from __future__ import annotations

import pandas as pd

from src.config import TEAM_IDS, SEASON, SEASON_TYPE
from src.ingest.http import nba_headers
from src.metrics.derived_metrics import normalize_percentile


def _safe_frame(endpoint_obj, index: int = 0) -> pd.DataFrame:
    frames = endpoint_obj.get_data_frames()
    if not frames:
        return pd.DataFrame()
    if index >= len(frames):
        return frames[0]
    return frames[index]


def _pick(row, *names, default=0):
    for name in names:
        if name in row and pd.notna(row[name]):
            return row[name]
    return default


def fetch_rosters(season: str = SEASON) -> tuple[pd.DataFrame, str]:
    try:
        from nba_api.stats.endpoints import commonteamroster
    except Exception as exc:
        return pd.DataFrame(), f"nba_api import failed: {exc}"

    rows = []
    messages = []

    for team, team_id in TEAM_IDS.items():
        try:
            endpoint = commonteamroster.CommonTeamRoster(
                team_id=team_id,
                season=season,
                headers=nba_headers(),
                timeout=20,
            )
            df = _safe_frame(endpoint)
        except Exception as exc:
            messages.append(f"{team} roster failed: {exc}")
            continue

        if df.empty:
            messages.append(f"{team} roster returned empty.")
            continue

        for _, row in df.iterrows():
            rows.append(
                {
                    "player_id": row.get("PLAYER_ID"),
                    "player": row.get("PLAYER", row.get("PLAYER_NAME", "")),
                    "team": team,
                    "position": row.get("POSITION", ""),
                    "jersey": row.get("NUM", ""),
                    "height": row.get("HEIGHT", ""),
                    "weight": row.get("WEIGHT", ""),
                    "birth_date": row.get("BIRTH_DATE", ""),
                    "age": row.get("AGE", ""),
                    "exp": row.get("EXP", ""),
                    "school": row.get("SCHOOL", ""),
                }
            )

    if not rows:
        return pd.DataFrame(), "; ".join(messages) if messages else "No roster rows returned."

    return pd.DataFrame(rows), "NBA CommonTeamRoster loaded."


def fetch_team_stats(season: str = SEASON, season_type: str = SEASON_TYPE) -> tuple[pd.DataFrame, str]:
    try:
        from nba_api.stats.endpoints import leaguedashteamstats
    except Exception as exc:
        return pd.DataFrame(), f"nba_api import failed: {exc}"

    try:
        adv_ep = leaguedashteamstats.LeagueDashTeamStats(
            season=season,
            season_type_all_star=season_type,
            measure_type_detailed_defense="Advanced",
            per_mode_detailed="PerGame",
            pace_adjust="N",
            headers=nba_headers(),
            timeout=20,
        )
        adv = _safe_frame(adv_ep)

        four_ep = leaguedashteamstats.LeagueDashTeamStats(
            season=season,
            season_type_all_star=season_type,
            measure_type_detailed_defense="Four Factors",
            per_mode_detailed="PerGame",
            pace_adjust="N",
            headers=nba_headers(),
            timeout=20,
        )
        four = _safe_frame(four_ep)
    except Exception as exc:
        return pd.DataFrame(), f"NBA LeagueDashTeamStats failed: {exc}"

    if adv.empty:
        return pd.DataFrame(), "NBA LeagueDashTeamStats returned empty."

    adv = adv[adv["TEAM_ID"].isin(set(TEAM_IDS.values()))].copy()

    if not four.empty and "TEAM_ID" in four.columns:
        four = four[four["TEAM_ID"].isin(set(TEAM_IDS.values()))].copy()
        merged = adv.merge(four, on=["TEAM_ID", "TEAM_NAME"], how="left", suffixes=("", "_FOUR"))
    else:
        merged = adv

    rows = []
    for _, row in merged.iterrows():
        team = next((name for name, tid in TEAM_IDS.items() if tid == row["TEAM_ID"]), row.get("TEAM_NAME", "Unknown"))
        rows.append(
            {
                "team": team,
                "ortg": float(_pick(row, "OFF_RATING", "E_OFF_RATING", default=0)),
                "drtg": float(_pick(row, "DEF_RATING", "E_DEF_RATING", default=0)),
                "net_rating": float(_pick(row, "NET_RATING", "E_NET_RATING", default=0)),
                "pace": float(_pick(row, "PACE", "PACE_PER40", default=0)),
                "efg_pct": float(_pick(row, "EFG_PCT", default=0)),
                "ts_pct": float(_pick(row, "TS_PCT", default=0)),
                "tov_pct": float(_pick(row, "TM_TOV_PCT", "TOV_PCT", default=0)),
                "oreb_pct": float(_pick(row, "OREB_PCT", default=0)),
                "dreb_pct": float(_pick(row, "DREB_PCT", default=0)),
            }
        )

    out = pd.DataFrame(rows)
    if out.empty:
        return out, "No Knicks/Spurs team rows found."

    out["off_rank"] = normalize_percentile(out["ortg"], True)
    out["def_rank"] = normalize_percentile(out["drtg"], False)
    out["reb_rank"] = normalize_percentile(out["dreb_pct"], True)
    out["pace_rank"] = normalize_percentile(out["pace"], True)
    out["shooting_rank"] = normalize_percentile(out["efg_pct"], True)
    out["turnover_rank"] = normalize_percentile(out["tov_pct"], False)

    return out, "NBA LeagueDashTeamStats loaded."


def fetch_player_stats(season: str = SEASON, season_type: str = SEASON_TYPE, roster: pd.DataFrame | None = None) -> tuple[pd.DataFrame, str]:
    try:
        from nba_api.stats.endpoints import leaguedashplayerstats
    except Exception as exc:
        return pd.DataFrame(), f"nba_api import failed: {exc}"

    try:
        base_ep = leaguedashplayerstats.LeagueDashPlayerStats(
            season=season,
            season_type_all_star=season_type,
            measure_type_detailed_defense="Base",
            per_mode_detailed="PerGame",
            headers=nba_headers(),
            timeout=20,
        )
        base = _safe_frame(base_ep)

        adv_ep = leaguedashplayerstats.LeagueDashPlayerStats(
            season=season,
            season_type_all_star=season_type,
            measure_type_detailed_defense="Advanced",
            per_mode_detailed="PerGame",
            headers=nba_headers(),
            timeout=20,
        )
        advanced = _safe_frame(adv_ep)
    except Exception as exc:
        return pd.DataFrame(), f"NBA LeagueDashPlayerStats failed: {exc}"

    if base.empty:
        return pd.DataFrame(), "NBA LeagueDashPlayerStats returned empty."

    base = base[base["TEAM_ID"].isin(set(TEAM_IDS.values()))].copy()

    if not advanced.empty and "PLAYER_ID" in advanced.columns:
        keep = [c for c in ["PLAYER_ID", "TS_PCT", "USG_PCT", "AST_PCT", "REB_PCT", "TOV_PCT", "NET_RATING"] if c in advanced.columns]
        base = base.merge(advanced[keep], on="PLAYER_ID", how="left")

    rows = []
    for _, row in base.iterrows():
        team = next((name for name, tid in TEAM_IDS.items() if tid == row["TEAM_ID"]), row.get("TEAM_ABBREVIATION", ""))
        usg = float(_pick(row, "USG_PCT", default=0))
        if usg <= 1:
            usg *= 100

        rows.append(
            {
                "player_id": row.get("PLAYER_ID"),
                "player": row.get("PLAYER_NAME", ""),
                "team": team,
                "gp": float(_pick(row, "GP", default=0)),
                "min": float(_pick(row, "MIN", default=0)),
                "pts": float(_pick(row, "PTS", default=0)),
                "reb": float(_pick(row, "REB", default=0)),
                "ast": float(_pick(row, "AST", default=0)),
                "stl": float(_pick(row, "STL", default=0)),
                "blk": float(_pick(row, "BLK", default=0)),
                "fg_pct": float(_pick(row, "FG_PCT", default=0)),
                "fg3_pct": float(_pick(row, "FG3_PCT", default=0)),
                "ft_pct": float(_pick(row, "FT_PCT", default=0)),
                "ts_pct": float(_pick(row, "TS_PCT", default=0)),
                "usg_pct": usg,
                "net_rating": float(_pick(row, "NET_RATING", default=0)),
                "per": None,
                "bpm": None,
                "vorp": None,
                "ws48": None,
            }
        )

    out = pd.DataFrame(rows)

    if roster is not None and not roster.empty:
        roster_keep = roster[["player_id", "position", "jersey", "exp", "school"]].copy()
        out = out.merge(roster_keep, on="player_id", how="left")
    else:
        out["position"] = ""

    return out.sort_values(["team", "min"], ascending=[True, False]).reset_index(drop=True), "NBA LeagueDashPlayerStats loaded."


def merge_bref_advanced(player_stats: pd.DataFrame, bref: pd.DataFrame) -> pd.DataFrame:
    if player_stats.empty or bref.empty:
        return player_stats

    out = player_stats.merge(bref, on="player", how="left", suffixes=("", "_bref"))

    for target, source in [
        ("per", "per_bref"),
        ("bpm", "bpm_bref"),
        ("vorp", "vorp_bref"),
        ("ws48", "ws48_bref"),
    ]:
        if source in out.columns:
            out[target] = out[source].combine_first(out[target])

    if "ts_pct_bref" in out.columns:
        out["ts_pct"] = out["ts_pct_bref"].combine_first(out["ts_pct"])

    if "usg_pct_bref" in out.columns:
        out["usg_pct"] = out["usg_pct_bref"].combine_first(out["usg_pct"])

    drop_cols = [c for c in out.columns if c.endswith("_bref") or c in ["ts_pct_bref", "usg_pct_bref"]]
    return out.drop(columns=drop_cols, errors="ignore")


def fetch_lineups(season: str = SEASON, season_type: str = SEASON_TYPE, group_quantity: int = 5) -> tuple[pd.DataFrame, str]:
    try:
        from nba_api.stats.endpoints import leaguedashlineups
    except Exception as exc:
        return pd.DataFrame(), f"nba_api import failed: {exc}"

    rows = []
    messages = []

    for team, team_id in TEAM_IDS.items():
        try:
            ep = leaguedashlineups.LeagueDashLineups(
                team_id_nullable=team_id,
                group_quantity=group_quantity,
                season=season,
                season_type_all_star=season_type,
                measure_type_detailed_defense="Advanced",
                per_mode_detailed="Per100Possessions",
                headers=nba_headers(),
                timeout=20,
            )
            df = _safe_frame(ep)
        except Exception as exc:
            messages.append(f"{team}: {exc}")
            continue

        if df.empty:
            messages.append(f"{team}: empty lineup table")
            continue

        for _, row in df.head(12).iterrows():
            rows.append(
                {
                    "lineup": row.get("GROUP_NAME", row.get("GROUP_ID", "")),
                    "team": team,
                    "min": float(_pick(row, "MIN", default=0)),
                    "ortg": float(_pick(row, "OFF_RATING", default=0)),
                    "drtg": float(_pick(row, "DEF_RATING", default=0)),
                    "net_rating": float(_pick(row, "NET_RATING", default=0)),
                    "efg_pct": float(_pick(row, "EFG_PCT", default=0)),
                    "tov_pct": float(_pick(row, "TM_TOV_PCT", "TOV_PCT", default=0)),
                    "reb_pct": float(_pick(row, "REB_PCT", default=0)),
                    "plus_minus": float(_pick(row, "PLUS_MINUS", default=0)),
                }
            )

    if not rows:
        return pd.DataFrame(), "; ".join(messages) if messages else "No lineup rows returned."

    return pd.DataFrame(rows), "NBA LeagueDashLineups loaded."


def fetch_shot_zones_for_player(player_id: int, team: str, player: str, season: str = SEASON, season_type: str = SEASON_TYPE) -> tuple[pd.DataFrame, str]:
    try:
        from nba_api.stats.endpoints import shotchartdetail
    except Exception as exc:
        return pd.DataFrame(), f"nba_api import failed: {exc}"

    try:
        ep = shotchartdetail.ShotChartDetail(
            team_id=0,
            player_id=int(player_id),
            season_nullable=season,
            season_type_all_star=season_type,
            context_measure_simple="FGA",
            headers=nba_headers(),
            timeout=20,
        )
        shots = _safe_frame(ep)
    except Exception as exc:
        return pd.DataFrame(), f"NBA ShotChartDetail failed: {exc}"

    if shots.empty:
        return pd.DataFrame(), "ShotChartDetail returned empty."

    zone_col = "SHOT_ZONE_BASIC" if "SHOT_ZONE_BASIC" in shots.columns else "SHOT_ZONE_AREA"
    if zone_col not in shots.columns:
        return pd.DataFrame(), "ShotChartDetail did not include shot zone columns."

    shots["SHOT_VALUE"] = shots.get("SHOT_TYPE", "").astype(str).str.contains("3PT").map({True: 3, False: 2})
    shots["POINTS"] = shots["SHOT_MADE_FLAG"] * shots["SHOT_VALUE"]

    grouped = (
        shots.groupby(zone_col)
        .agg(
            loc_x=("LOC_X", "mean"),
            loc_y=("LOC_Y", "mean"),
            fg_pct=("SHOT_MADE_FLAG", "mean"),
            points=("POINTS", "sum"),
            attempts=("SHOT_MADE_FLAG", "size"),
        )
        .reset_index()
        .rename(columns={zone_col: "zone", "attempts": "shot_volume"})
    )

    grouped["efg_pct"] = grouped["points"] / (2 * grouped["shot_volume"])
    grouped["player"] = player
    grouped["team"] = team
    grouped["volume_rank"] = grouped["shot_volume"].rank(ascending=False, method="dense").astype(int)

    return grouped[["player", "team", "zone", "loc_x", "loc_y", "fg_pct", "efg_pct", "shot_volume", "volume_rank"]], "NBA ShotChartDetail loaded."


def fetch_synergy_pnr(season: str = SEASON, season_type: str = SEASON_TYPE) -> tuple[pd.DataFrame, str]:
    try:
        from nba_api.stats.endpoints import synergyplaytypes
    except Exception as exc:
        return pd.DataFrame(), f"nba_api import failed: {exc}"

    frames = []
    messages = []

    for play_type in ["PRBallHandler", "PRRollman"]:
        try:
            ep = synergyplaytypes.SynergyPlayTypes(
                league_id="00",
                per_mode_simple="PerGame",
                play_type_nullable=play_type,
                player_or_team="P",
                season=season,
                season_type_all_star=season_type,
                type_grouping_nullable="offensive",
                headers=nba_headers(),
                timeout=20,
            )
            df = _safe_frame(ep)
            if not df.empty:
                df["play_type"] = play_type
                frames.append(df)
            else:
                messages.append(f"{play_type}: empty")
        except Exception as exc:
            messages.append(f"{play_type}: {exc}")

    if not frames:
        return pd.DataFrame(), "; ".join(messages) if messages else "Synergy returned no PnR rows."

    raw = pd.concat(frames, ignore_index=True)
    team_cols = [c for c in ["TEAM_ID", "TEAM_ABBREVIATION", "TEAM_NAME"] if c in raw.columns]
    name_col = next((c for c in ["PLAYER_NAME", "PLAYER", "NAME"] if c in raw.columns), None)
    if name_col is None:
        return raw, "Synergy loaded but expected player-name column was missing."

    team_ids = set(TEAM_IDS.values())
    if "TEAM_ID" in raw.columns:
        raw = raw[raw["TEAM_ID"].isin(team_ids)].copy()

    ppp_col = next((c for c in ["PPP", "POINTS_PER_POSSESSION", "POSS_PTS"] if c in raw.columns), None)
    poss_col = next((c for c in ["POSS", "POSS_COUNT"] if c in raw.columns), None)

    rows = []
    for _, row in raw.iterrows():
        team = next((name for name, tid in TEAM_IDS.items() if row.get("TEAM_ID") == tid), row.get("TEAM_ABBREVIATION", row.get("TEAM_NAME", "")))
        rows.append(
            {
                "team": team,
                "player": row.get(name_col, ""),
                "play_type": row.get("play_type", ""),
                "possessions": float(row.get(poss_col, 0)) if poss_col else 0,
                "ppp": float(row.get(ppp_col, 0)) if ppp_col else 0,
                "percentile": float(row.get("PERCENTILE", 0)) if "PERCENTILE" in row else None,
                "tov_pct": float(row.get("TOV_PCT", 0)) if "TOV_PCT" in row else None,
                "score_freq": float(row.get("SCORE_POSS_PCT", 0)) if "SCORE_POSS_PCT" in row else None,
            }
        )

    return pd.DataFrame(rows).sort_values(["team", "play_type", "ppp"], ascending=[True, True, False]), "NBA SynergyPlayTypes loaded."
