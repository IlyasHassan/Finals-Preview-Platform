import streamlit as st
import pandas as pd
import plotly.express as px

from src.utils.snapshot_loader import load_snapshot, snapshot_exists, missing_snapshot_files
from src.metrics.formatting import as_percent, safe_columns
from src.charts.radar import plot_team_radar
from src.charts.court import draw_half_court

st.set_page_config(page_title="Knicks vs Spurs Snapshot Dashboard", layout="wide")

CUSTOM_CSS = """
<style>
.block-container { padding-top: 2rem; padding-bottom: 3rem; max-width: 1180px; }
[data-testid="stSidebar"] { background: #11151C; }
h1 { font-size: 2.15rem !important; letter-spacing: -0.04em; }
.metric-card {
    background: linear-gradient(180deg, #171D27 0%, #11151C 100%);
    border: 1px solid #2B3442;
    border-radius: 16px;
    padding: 18px 18px 14px 18px;
    min-height: 112px;
}
.metric-label { color: #AAB3C2; font-size: 0.82rem; margin-bottom: 8px; }
.metric-value { color: #FFFFFF; font-size: 1.7rem; font-weight: 800; line-height: 1.1; }
.metric-sub { color: #F58426; font-size: 0.78rem; margin-top: 8px; }
.section-note {
    background: #121822;
    border: 1px solid #293241;
    border-radius: 12px;
    padding: 12px 14px;
    color: #C9D2E3;
    font-size: 0.92rem;
}
</style>
"""
st.markdown(CUSTOM_CSS, unsafe_allow_html=True)


def metric_card(label, value, subtext=""):
    st.markdown(
        f"""
        <div class="metric-card">
            <div class="metric-label">{label}</div>
            <div class="metric-value">{value}</div>
            <div class="metric-sub">{subtext}</div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def plot_config():
    return {"displayModeBar": False, "responsive": True}


st.sidebar.title("Snapshot Dashboard")
st.sidebar.markdown("**Knicks vs. Spurs**")
st.sidebar.caption("Saved real-season data only. No live requests on page load.")

page = st.sidebar.radio(
    "Navigate",
    [
        "Overview",
        "Teams",
        "Players",
        "Shot Zones",
        "Pick-and-Roll",
        "Lineups",
        "Rosters",
        "Matchups",
        "Methods & Sources",
    ],
)

if not snapshot_exists():
    st.title("Snapshot data has not been built yet")
    st.error("The app uses saved real-season data only, but the snapshot CSV files are missing.")
    st.write("Missing files:")
    st.code("\\n".join(missing_snapshot_files()))

    st.write("Run this locally, then commit the generated `data/snapshot` folder to GitHub:")
    st.code('python scripts/build_snapshot.py --season 2025-26 --season-type "Regular Season"', language="bash")

    st.write("For more shot-chart players:")
    st.code('python scripts/build_snapshot.py --season 2025-26 --season-type "Regular Season" --max-shotchart-players 15', language="bash")
    st.stop()

data = load_snapshot()

team_stats = data["team_stats"]
player_stats = data["player_stats"]
roster = data["roster"]
lineups = data["lineups"]
shot_zones = data["shot_zones"]
pnr = data["pnr_play_types"]
matchups = data["matchups"]
manifest = data["source_manifest"]
metadata = data["snapshot_metadata"]

created = metadata["snapshot_created_utc"].iloc[0] if "snapshot_created_utc" in metadata.columns and not metadata.empty else "unknown"
season = metadata["season"].iloc[0] if "season" in metadata.columns and not metadata.empty else "unknown"
season_type = metadata["season_type"].iloc[0] if "season_type" in metadata.columns and not metadata.empty else "unknown"

if page == "Overview":
    st.title("Knicks vs. Spurs Finals Scouting Room")
    st.markdown(
        f'<div class="section-note">Snapshot-only architecture. No public data requests happen when visitors open this app. Snapshot: {season}, {season_type}. Created UTC: {created}.</div>',
        unsafe_allow_html=True,
    )

    if team_stats.empty:
        st.error("team_stats.csv is empty. Rebuild the snapshot and check source_manifest.csv.")
    else:
        knicks = team_stats[team_stats["team"] == "Knicks"].iloc[0] if "Knicks" in set(team_stats["team"]) else team_stats.iloc[0]
        spurs = team_stats[team_stats["team"] == "Spurs"].iloc[0] if "Spurs" in set(team_stats["team"]) else team_stats.iloc[-1]

        c1, c2, c3, c4 = st.columns(4)
        with c1:
            metric_card("Knicks Net Rating", f"{knicks['net_rating']:+.1f}", "saved snapshot")
        with c2:
            metric_card("Spurs Net Rating", f"{spurs['net_rating']:+.1f}", "saved snapshot")
        with c3:
            metric_card("Knicks Pace", f"{knicks['pace']:.1f}", "saved snapshot")
        with c4:
            metric_card("Spurs Pace", f"{spurs['pace']:.1f}", "saved snapshot")

        left, right = st.columns([1.1, 1])

        with left:
            st.plotly_chart(plot_team_radar(team_stats), use_container_width=True, config=plot_config())

        with right:
            st.subheader("Four Factors")
            show = safe_columns(team_stats, ["team", "efg_pct", "ts_pct", "tov_pct", "oreb_pct", "dreb_pct"])
            st.dataframe(
                as_percent(show, ["efg_pct", "ts_pct", "tov_pct", "oreb_pct", "dreb_pct"]),
                hide_index=True,
                use_container_width=True,
            )

elif page == "Teams":
    st.title("Team Comparison")

    if team_stats.empty:
        st.error("team_stats.csv is empty.")
    else:
        st.dataframe(
            as_percent(team_stats, ["efg_pct", "ts_pct", "tov_pct", "oreb_pct", "dreb_pct"]),
            hide_index=True,
            use_container_width=True,
        )

        c1, c2 = st.columns(2)

        with c1:
            fig = px.bar(
                team_stats,
                x="team",
                y=["ortg", "drtg", "net_rating"],
                barmode="group",
                template="plotly_dark",
                title="Efficiency Ratings",
            )
            fig.update_layout(paper_bgcolor="#0B0D10", plot_bgcolor="#0B0D10", legend_title_text="")
            st.plotly_chart(fig, use_container_width=True, config=plot_config())

        with c2:
            fig = px.bar(
                team_stats,
                x="team",
                y=["efg_pct", "ts_pct", "tov_pct"],
                barmode="group",
                template="plotly_dark",
                title="Shooting and Turnover Profile",
            )
            fig.update_layout(paper_bgcolor="#0B0D10", plot_bgcolor="#0B0D10", legend_title_text="")
            st.plotly_chart(fig, use_container_width=True, config=plot_config())

elif page == "Players":
    st.title("Player Scouting")

    if player_stats.empty:
        st.error("player_stats.csv is empty.")
    else:
        teams = sorted(player_stats["team"].dropna().unique())
        selected_teams = st.multiselect("Team", teams, default=teams)
        min_minutes = st.slider("Minimum minutes per game", 0.0, 40.0, 8.0, 1.0)

        filtered = player_stats[
            (player_stats["team"].isin(selected_teams))
            & (pd.to_numeric(player_stats["min"], errors="coerce").fillna(0) >= min_minutes)
        ].sort_values(["team", "min"], ascending=[True, False])

        st.dataframe(
            as_percent(filtered, ["fg_pct", "fg3_pct", "ft_pct", "ts_pct", "ws48", "ts_pct_reference"]),
            hide_index=True,
            use_container_width=True,
            height=430,
        )

        fig = px.scatter(
            filtered,
            x="usg_pct",
            y="ts_pct",
            size="pts",
            color="team",
            hover_name="player",
            hover_data=[col for col in ["position", "min", "pts", "ast", "reb", "net_rating", "per", "bpm", "vorp"] if col in filtered.columns],
            template="plotly_dark",
            title="Usage vs True Shooting",
        )
        fig.update_layout(paper_bgcolor="#0B0D10", plot_bgcolor="#0B0D10")
        st.plotly_chart(fig, use_container_width=True, config=plot_config())

elif page == "Shot Zones":
    st.title("Shot Zones")

    if shot_zones.empty:
        st.error("shot_zones.csv is empty. Rebuild the snapshot and check NBA ShotChartDetail results.")
    else:
        teams = sorted(shot_zones["team"].dropna().unique())
        selected_team = st.selectbox("Team", teams)
        players = sorted(shot_zones[shot_zones["team"] == selected_team]["player"].dropna().unique())
        selected_player = st.selectbox("Player", players)

        player_shots = shot_zones[
            (shot_zones["team"] == selected_team)
            & (shot_zones["player"] == selected_player)
        ].copy()

        c1, c2 = st.columns([1.15, 1])

        with c1:
            st.plotly_chart(draw_half_court(player_shots), use_container_width=True, config=plot_config())

        with c2:
            st.subheader(f"{selected_player}: Shot Zones")
            display = safe_columns(player_shots, ["zone", "fg_pct", "efg_pct", "shot_volume", "volume_rank"])
            st.dataframe(
                as_percent(display, ["fg_pct", "efg_pct"]),
                hide_index=True,
                use_container_width=True,
            )

            if not player_shots.empty:
                best = player_shots.sort_values("efg_pct", ascending=False).iloc[0]
                worst = player_shots.sort_values("efg_pct", ascending=True).iloc[0]
                a, b = st.columns(2)
                with a:
                    metric_card("Best Zone", best["zone"], f"{best['efg_pct']:.1%}")
                with b:
                    metric_card("Worst Zone", worst["zone"], f"{worst['efg_pct']:.1%}")

elif page == "Pick-and-Roll":
    st.title("Pick-and-Roll Play Types")

    st.info("This page shows saved NBA Synergy play-type rows. It does not invent exact handler-screener duos or coverage labels.")

    if pnr.empty:
        st.error("pnr_play_types.csv is empty. SynergyPlayTypes may have failed during the snapshot build.")
    else:
        teams = sorted(pnr["team"].dropna().unique())
        selected_teams = st.multiselect("Team", teams, default=teams)

        filtered = pnr[pnr["team"].isin(selected_teams)].copy()

        st.dataframe(
            as_percent(filtered, ["percentile", "tov_pct", "score_freq"]),
            hide_index=True,
            use_container_width=True,
            height=420,
        )

        fig = px.scatter(
            filtered,
            x="possessions",
            y="ppp",
            color="team",
            symbol="play_type",
            hover_name="player",
            hover_data=[col for col in ["percentile", "tov_pct", "score_freq"] if col in filtered.columns],
            template="plotly_dark",
            title="PnR Play-Type Efficiency",
        )
        fig.update_layout(paper_bgcolor="#0B0D10", plot_bgcolor="#0B0D10")
        st.plotly_chart(fig, use_container_width=True, config=plot_config())

elif page == "Lineups":
    st.title("Lineup Analysis")

    if lineups.empty:
        st.error("lineups.csv is empty.")
    else:
        st.dataframe(
            as_percent(lineups, ["efg_pct", "tov_pct", "reb_pct"]),
            hide_index=True,
            use_container_width=True,
            height=360,
        )

        fig = px.bar(
            lineups.sort_values("net_rating", ascending=False),
            x="net_rating",
            y="lineup",
            color="team",
            orientation="h",
            template="plotly_dark",
            title="Lineup Net Rating",
        )
        fig.update_layout(yaxis={"categoryorder": "total ascending"}, paper_bgcolor="#0B0D10", plot_bgcolor="#0B0D10")
        st.plotly_chart(fig, use_container_width=True, config=plot_config())

elif page == "Rosters":
    st.title("Rosters")

    if roster.empty:
        st.error("roster.csv is empty.")
    else:
        st.dataframe(roster, hide_index=True, use_container_width=True, height=500)

elif page == "Matchups":
    st.title("Matchups")

    if matchups.empty:
        st.warning("No matchup matrix is shown because no real matchup endpoint/parser has been integrated yet. The app does not fabricate matchup data.")
        st.write("To add this later, use a real NBA matchup endpoint or possession-level parser and write the result into `data/snapshot/matchups.csv`.")
    else:
        st.dataframe(
            as_percent(matchups, ["fg_pct_allowed", "fg_pct_suppression"]),
            hide_index=True,
            use_container_width=True,
            height=420,
        )

elif page == "Methods & Sources":
    st.title("Methods & Sources")

    st.subheader("Snapshot Metadata")
    st.dataframe(metadata, hide_index=True, use_container_width=True)

    st.subheader("Source Manifest")
    st.dataframe(manifest, hide_index=True, use_container_width=True, height=420)

    st.markdown(
        """
        **Snapshot policy**

        - The deployed app does not request public data on page load.
        - The regular-season data is pulled once by `scripts/build_snapshot.py`.
        - The generated CSV files are committed to GitHub.
        - No sample fallback data is used.
        - Missing/failed tables are shown as missing or empty, not replaced with fake values.
        - Pick-and-roll coverage labels such as drop, switch, hedge, blitz, and ICE are not fabricated.
        """
    )
