# Snapshot Data

Generated at UTC: `2026-06-01T22:40:25.402527+00:00`

Season: `2025-26`

Season type: `Regular Season`

## Source hierarchy

- NBA.com/stats when reachable.
- Basketball-Reference for team/player core stats when NBA.com/stats times out.
- ESPN site API for roster/team metadata backup.
- Basketball-Reference Shooting for shot-zone approximation when NBA ShotChartDetail is unavailable.

## Policy

This folder contains saved source data. The Streamlit app reads this folder only and does not request public data on page load.

The builder fails fast if core tables are empty, so empty CSVs should not replace a valid snapshot.
