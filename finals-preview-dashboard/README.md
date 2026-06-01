# 2026 NBA Finals: Knicks vs. Spurs Preview Platform

Cleaned Batch 2.1 Streamlit dashboard.

## What this version fixes

- Removes Chris Paul from the Spurs sample roster.
- Adds a fuller Knicks/Spurs Finals roster pool.
- Keeps live-first ingestion, but makes sample fallback cleaner.
- Improves the UI with cleaner spacing, cards, formatted tables, better charts, and better source status.
- Makes the Methods page explicit about which tables are live, fallback, sample, or proxy.

## Run locally

```bash
pip install -r requirements.txt
streamlit run app.py
```

## Streamlit Cloud main file path

If this folder is nested in your repo:

```text
finals-preview-dashboard/app.py
```

If these files are at the repo root:

```text
app.py
```

## Data note

The static CSVs are cleaned demo/proxy data built to make the app usable even when public sources are blocked. **Live-first + cleaned fallback** is now the default sidebar mode. Use **Cleaned sample data** only for offline/demo mode.


## Important Batch 2.2 fix

The app now defaults to live-first mode. The code uses `data_mode.startswith("Live-first")` instead of exact text matching, so changing the label in the sidebar will not accidentally force sample mode.

If the Methods page says **Manual sample mode**, you are using the sample-data radio option.

If it says **Attempted live, fell back**, the app tried the public source but Streamlit Cloud/source access failed for that table.
