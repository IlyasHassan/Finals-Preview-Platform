import pandas as pd


def status_table(rows):
    return pd.DataFrame(rows, columns=["Table", "Source", "Status", "Details"])


def empty_df(columns):
    return pd.DataFrame(columns=columns)
