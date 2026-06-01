import pandas as pd


def normalize_percentile(series: pd.Series, higher_is_better: bool = True) -> pd.Series:
    if series.empty or series.nunique(dropna=True) <= 1:
        return pd.Series([50] * len(series), index=series.index)
    rank = series.rank(pct=True) * 100
    if not higher_is_better:
        rank = 100 - rank
    return rank.round(1)


def add_zone_labels(df: pd.DataFrame) -> pd.DataFrame:
    out = df.copy()
    if "fg_pct" in out.columns:
        out["fg_pct_label"] = (out["fg_pct"] * 100).round(1).astype(str) + "%"
    if "efg_pct" in out.columns:
        out["efg_pct_label"] = (out["efg_pct"] * 100).round(1).astype(str) + "%"
    return out
