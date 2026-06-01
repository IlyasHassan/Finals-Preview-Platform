import pandas as pd


def as_percent(df: pd.DataFrame, columns: list[str], decimals: int = 1) -> pd.DataFrame:
    out = df.copy()
    for col in columns:
        if col in out.columns:
            out[col] = out[col].apply(
                lambda x: f"{x:.{decimals}%}" if pd.notna(x) and x != "" else ""
            )
    return out


def normalize_percentile(series: pd.Series, higher_is_better: bool = True) -> pd.Series:
    numeric = pd.to_numeric(series, errors="coerce")
    if numeric.empty or numeric.nunique(dropna=True) <= 1:
        return pd.Series([50] * len(numeric), index=numeric.index)

    rank = numeric.rank(pct=True) * 100
    if not higher_is_better:
        rank = 100 - rank

    return rank.round(1)


def safe_columns(df: pd.DataFrame, columns: list[str]) -> pd.DataFrame:
    existing = [col for col in columns if col in df.columns]
    return df[existing].copy()
