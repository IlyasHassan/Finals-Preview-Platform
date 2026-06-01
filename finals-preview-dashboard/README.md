# Knicks vs Spurs Finals Scouting Dashboard

Final snapshot architecture.

The deployed Streamlit app does **not** request NBA.com/stats, Basketball-Reference, or PBPStats on page load.

Instead:

1. Run `scripts/build_snapshot.py` locally.
2. The script pulls real current-season data once.
3. The script writes CSV files into `data/snapshot/`.
4. Commit the generated `data/snapshot/` files to GitHub.
5. Streamlit reads the saved snapshot forever.

No sample fallback. No fake placeholder data. No silent substitution.

## Install

```bash
pip install -r requirements.txt
```

## Build the regular-season snapshot

```bash
python scripts/build_snapshot.py --season 2025-26 --season-type "Regular Season"
```

This writes:

```text
data/snapshot/team_stats.csv
data/snapshot/player_stats.csv
data/snapshot/roster.csv
data/snapshot/lineups.csv
data/snapshot/shot_zones.csv
data/snapshot/pnr_play_types.csv
data/snapshot/matchups.csv
data/snapshot/source_manifest.csv
data/snapshot/snapshot_metadata.csv
data/snapshot/README.md
```

## Build with more shot-chart players

```bash
python scripts/build_snapshot.py --season 2025-26 --season-type "Regular Season" --max-shotchart-players 30
```

## Run locally

```bash
streamlit run app.py
```

## Deploy

Commit the generated `data/snapshot/` folder to GitHub.

If these files are nested inside a `finals-preview-dashboard` folder in your repo, use this Streamlit main file path:

```text
finals-preview-dashboard/app.py
```

If these files are at the repo root, use:

```text
app.py
```

## Data philosophy

- Official/statistical layer: NBA.com/stats via `nba_api`.
- Reference layer: Basketball-Reference advanced metrics.
- Possession-enrichment layer: PBPStats where accessible.
- Tactical coverage labels: not fabricated. Drop/switch/hedge/blitz/ICE require manually charted or licensed data.
