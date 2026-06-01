import pandas as pd


def calculate_pnr_duo_score(row: pd.Series) -> float:
    """
    Sample/proxy composite for ranking PnR duos.

    This is not an official NBA metric. It is a transparent MVP placeholder
    that combines efficiency, lineup impact, volume, and passing/creation context.
    """
    ppp_component = row["ppp"] * 40
    impact_component = row["net_rating"] * 2
    volume_component = row["possessions"] / 10
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
    output["fg_pct_label"] = (output["fg_pct"] * 100).round(1).astype(str) + "%"
    return output
