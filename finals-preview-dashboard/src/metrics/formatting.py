import pandas as pd


def as_percent(df: pd.DataFrame, columns: list[str], decimals: int = 1) -> pd.DataFrame:
    out = df.copy()
    for col in columns:
        if col in out.columns:
            out[col] = out[col].apply(lambda x: f"{x:.{decimals}%}" if pd.notna(x) else "")
    return out


def as_number(df: pd.DataFrame, columns: list[str], decimals: int = 1) -> pd.DataFrame:
    out = df.copy()
    for col in columns:
        if col in out.columns:
            out[col] = pd.to_numeric(out[col], errors="coerce").round(decimals)
    return out
