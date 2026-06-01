# Knicks vs Spurs Finals Scouting Dashboard, Live-Only Build

This version removes sample-data fallback.

The app attempts to use real current-season data only:
- NBA.com/stats through `nba_api`
- Basketball-Reference advanced stats through HTML table parsing
- PBPStats documentation-compatible client scaffold for play-by-play/lineup enrichment

If a public source blocks or fails, that table is shown as unavailable instead of being replaced with sample data.

## Run locally

```bash
pip install -r requirements.txt
streamlit run app.py
```

## Streamlit Cloud

If this folder is nested inside your repo, use:

```text
finals-preview-dashboard/app.py
```

If these files are at the repo root, use:

```text
app.py
```

## Important

This is live-only. No fake placeholder data is used. If NBA.com/stats or Basketball-Reference blocks the request from Streamlit Cloud, the app will show a source error.
