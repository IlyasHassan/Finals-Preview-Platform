import pandas as pd


def calculate_pnr_duo_score(row: pd.Series) -> float:
    """
    Transparent composite for ranking PnR duos.

    This is not an official NBA metric. It combines efficiency, lineup impact,
    volume, and pass-connection context when available.
    """
    ppp_component = row.get("ppp", 0) * 40
    impact_component = row.get("net_rating", 0) * 2
    volume_component = row.get("possessions", 0) / 10
    passing_component = row.get("assist_pct", 0) * 20
    connection_component = row.get("pass_connections", 0) / 10

    return round(
        ppp_component
        + impact_component
        + volume_component
        + passing_component
        + connection_component,
        2,
    )


def get_efg(fgm: float, f3pm: float, fga: float) -> float:
    if fga == 0:
        return 0.0
    return round((fgm + 0.5 * f3pm) / fga, 3)


def add_zone_labels(df: pd.DataFrame) -> pd.DataFrame:
    output = df.copy()
    if "fg_pct" in output.columns:
        output["fg_pct_label"] = (output["fg_pct"] * 100).round(1).astype(str) + "%"
    if "efg_pct" in output.columns:
        output["efg_pct_label"] = (output["efg_pct"] * 100).round(1).astype(str) + "%"
    return output


def normalize_percentile(series: pd.Series, higher_is_better: bool = True) -> pd.Series:
    if series.empty or series.nunique(dropna=True) <= 1:
        return pd.Series([50] * len(series), index=series.index)

    rank = series.rank(pct=True) * 100
    if not higher_is_better:
        rank = 100 - rank
    return rank.round(1)
