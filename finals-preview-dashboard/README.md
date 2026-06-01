# Knicks vs Spurs Finals Scouting Dashboard

Final snapshot architecture, version 2.

This version fixes the empty-CSV problem by making the snapshot builder fail fast.

## Key fixes

- The app never requests NBA.com/stats on page load.
- The builder pulls real data once and saves it.
- The builder does **not** overwrite a good snapshot with empty CSVs.
- Core data and slow shot charts are separated.
- If NBA.com/stats is blocked, the script stops and prints the actual source failure.
- No sample fallback data is used.

## Install

```bash
pip install -r requirements.txt
```

## Step 1: diagnose sources

Run this first:

```bash
python scripts/diagnose_sources.py --season 2025-26 --season-type "Regular Season"
```

This checks whether NBA.com/stats is reachable from your machine.

## Step 2: build fast core snapshot

Run:

```bash
python scripts/build_snapshot.py --season 2025-26 --season-type "Regular Season" --skip-shotcharts
```

This creates:

```text
team_stats.csv
player_stats.csv
roster.csv
lineups.csv
pnr_play_types.csv
matchups.csv
source_manifest.csv
snapshot_metadata.csv
```

## Step 3: add shot charts separately

Shot charts are slow because they require player-by-player requests.

Start small:

```bash
python scripts/build_snapshot.py --season 2025-26 --season-type "Regular Season" --only-shotcharts --max-shotchart-players 6
```

Then increase later:

```bash
python scripts/build_snapshot.py --season 2025-26 --season-type "Regular Season" --only-shotcharts --max-shotchart-players 12
```

This writes one combined file:

```text
data/snapshot/shot_zones.csv
```

## Step 4: run the app

```bash
streamlit run app.py
```

## Step 5: commit generated snapshot files

Commit the full `data/snapshot/` folder to GitHub.

## Important

If the CSVs are empty, do not deploy. Check:

```text
data/raw/latest_build_attempt/source_manifest.csv
data/raw/latest_build_attempt/build_errors.txt
```

The builder now preserves failure logs.


## ESPN API addition

This version also tries ESPN's public site API:

```text
https://site.api.espn.com/apis/site/v2/sports/basketball/nba/teams
```

It writes these audit/enrichment files when available:

```text
data/snapshot/espn_teams.csv
data/snapshot/espn_rosters.csv
```

ESPN is used as a real backup for roster/team metadata only. It is not a substitute for NBA.com/stats shot charts, lineups, Synergy play types, or Basketball-Reference advanced metrics.


## Version 4: Basketball-Reference core backup

Your diagnosis showed that `stats.nba.com` timed out for `LeagueDashTeamStats`, `LeagueDashPlayerStats`, `LeagueDashLineups`, and NBA roster endpoints, while ESPN and Basketball-Reference loaded successfully.

This version fixes that:

- If NBA.com/stats team stats fail, `team_stats.csv` is built from Basketball-Reference's league Miscellaneous Stats table.
- If NBA.com/stats player stats fail, `player_stats.csv` is built from Basketball-Reference Per Game + Advanced tables.
- ESPN remains the roster/team metadata backup.
- If NBA ShotChartDetail fails or NBA player IDs are missing, `shot_zones.csv` is built from Basketball-Reference Shooting distance zones.
- SynergyPlayTypes now uses the corrected `player_or_team_abbreviation` parameter, with a fallback for older nba_api versions.

This is not fake fallback data. It is an alternate real source.


## Version 4.1 fix

This patch fixes the `NameError` in `scripts/build_snapshot.py`.

The build script now correctly lets `fetch_player_stats()` handle the source hierarchy internally:

```text
NBA.com/stats player stats
→ if unavailable, Basketball-Reference Per Game + Advanced
```

Use:

```bash
python scripts/build_snapshot.py --season 2025-26 --season-type "Regular Season" --skip-shotcharts
```

Then:

```bash
python scripts/build_snapshot.py --season 2025-26 --season-type "Regular Season" --only-shotcharts --max-shotchart-players 6
```


## Version 4.2 fix

This patch fixes the Streamlit Cloud crash:

```text
pandas.errors.EmptyDataError
```

The app now safely handles zero-byte/headerless CSVs for non-critical tables like:

```text
lineups.csv
pnr_play_types.csv
matchups.csv
shot_zones.csv
```

Those tables can be empty if NBA.com/stats times out. The app will show warnings instead of crashing.

Critical tables still must be non-empty:

```text
team_stats.csv
player_stats.csv
roster.csv
```

If any of those are empty, the app stops with a clear message telling you to rebuild the snapshot.
