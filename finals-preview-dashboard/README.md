# 2026 NBA Finals: Knicks vs. Spurs Preview Platform

This is a Streamlit dashboard for a Knicks vs. Spurs NBA Finals scouting preview.

## Batch 2 update

This version adds a live-ingestion layer with safe fallback behavior.

The app has two modes:

1. **Sample data mode**  
   Guaranteed to work. Uses the CSV files in `data/sample`.

2. **Live-first mode**  
   Attempts to pull live/current data from:
   - NBA.com/stats via `nba_api`
   - Basketball-Reference through cached HTML table parsing
   - PBPStats through a lightweight API client scaffold

If any source fails, the app falls back to the sample CSVs so the deployed website stays online.

## Local setup

```bash
python -m venv venv
```

Windows:

```bash
venv\Scripts\activate
```

Mac/Linux:

```bash
source venv/bin/activate
```

Install dependencies:

```bash
pip install -r requirements.txt
```

Run the app:

```bash
streamlit run app.py
```

## Deploy to Streamlit Community Cloud

If the repository root contains `app.py`, use:

```text
app.py
```

If the app is inside a nested folder called `finals-preview-dashboard`, use:

```text
finals-preview-dashboard/app.py
```

## Data limitations

Public NBA data access can be inconsistent in cloud environments. NBA.com/stats may throttle or block requests. Basketball-Reference may rate-limit scraping. PBPStats endpoint availability can change.

This project is designed to degrade gracefully:
live source fails -> cached file if available -> sample data fallback.
