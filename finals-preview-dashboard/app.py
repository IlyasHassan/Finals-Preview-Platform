import streamlit as st
import pandas as pd
import plotly.express as px

from src.config import SEASON, SEASON_TYPE
from src.ingest.live_pipeline import build_dataset
from src.charts.radar import plot_team_radar
from src.charts.court import draw_half_court
from src.metrics.derived_metrics import calculate_pnr_duo_score, add_zone_labels

st.set_page_config(page_title="2026 NBA Finals Scouting Room", layout="wide")


@st.cache_data(ttl=60 * 60, show_spinner=False)
def load_dashboard_data(data_mode: str, season: str, season_type: str):
    prefer_live = data_mode == "Live-first + sample fallback"
    return build_dataset(prefer_live=prefer_live, season=season, season_type=season_type)


st.sidebar.title("2026 NBA Finals")
st.sidebar.markdown("**Knicks vs. Spurs**")

data_mode = st.sidebar.radio(
    "Data mode",
    ["Sample data", "Live-first + sample fallback"],
    index=0,
    help=(
        "Sample data is guaranteed to work. Live-first mode attempts NBA.com/stats, "
        "Basketball-Reference, and PBPStats, then falls back to sample data if a source fails."
    ),
)

season = st.sidebar.text_input("Season", value=SEASON)
season_type = st.sidebar.selectbox(
    "Season type",
    ["Regular Season", "Playoffs"],
    index=0 if SEASON_TYPE == "Regular Season" else 1,
)

if st.sidebar.button("Clear cached data and rerun"):
    st.cache_data.clear()
    st.rerun()

with st.spinner("Loading dashboard data..."):
    data, source_manifest = load_dashboard_data(data_mode, season, season_type)

st.sidebar.caption(f"Mode: {data_mode}")

page = st.sidebar.radio(
    "Navigate",
    [
        "Overview",
        "Teams",
        "Players",
        "Shot Zones",
        "Pick-and-Roll",
        "Lineups",
        "Matchups",
        "Methods & Sources",
    ],
)

if page == "Overview":
    st.title("Series Overview: Knicks vs. Spurs")

    if data_mode == "Sample data":
        st.info("Sample mode is active. Switch to live-first mode in the sidebar to attempt live ingestion.")
    else:
        st.info("Live-first mode is active. Any blocked or failed source falls back to sample data.")

    team_stats = data["team_stats"]

    knicks = team_stats[team_stats["team"] == "Knicks"].iloc[0] if "Knicks" in set(team_stats["team"]) else team_stats.iloc[0]
    spurs = team_stats[team_stats["team"] == "Spurs"].iloc[0] if "Spurs" in set(team_stats["team"]) else team_stats.iloc[-1]

    col1, col2, col3, col4 = st.columns(4)
    col1.metric("Knicks Net Rating", f"{knicks['net_rating']:+.1f}")
    col2.metric("Spurs Net Rating", f"{spurs['net_rating']:+.1f}")
    col3.metric("Knicks Pace", f"{knicks['pace']:.1f}")
    col4.metric("Spurs Pace", f"{spurs['pace']:.1f}")

    st.plotly_chart(plot_team_radar(team_stats), use_container_width=True)

    st.subheader("Four Factors Snapshot")
    factors = team_stats[
        ["team", "efg_pct", "ts_pct", "tov_pct", "oreb_pct", "dreb_pct"]
    ].copy()
    st.dataframe(factors, use_container_width=True)

elif page == "Teams":
    st.title("Team Comparison")

    team_stats = data["team_stats"]
    st.dataframe(team_stats, use_container_width=True)

    fig_eff = px.bar(
        team_stats,
        x="team",
        y=["ortg", "drtg", "net_rating"],
        barmode="group",
        title="Team Efficiency Ratings",
    )
    st.plotly_chart(fig_eff, use_container_width=True)

    fig_def = px.bar(
        team_stats,
        x="team",
        y=["paint_defense", "perimeter_defense"],
        barmode="group",
        title="Paint and Perimeter Defense Proxy Scores",
    )
    st.plotly_chart(fig_def, use_container_width=True)

elif page == "Players":
    st.title("Player Scouting")

    player_stats = data["player_stats"].sort_values(by="per", ascending=False)
    team_filter = st.multiselect(
        "Filter by team",
        options=sorted(player_stats["team"].dropna().unique()),
        default=sorted(player_stats["team"].dropna().unique()),
    )
    filtered = player_stats[player_stats["team"].isin(team_filter)]

    st.dataframe(filtered, use_container_width=True)

    fig = px.scatter(
        filtered,
        x="usg_pct",
        y="ts_pct",
        size="pts",
        color="team",
        hover_name="player",
        title="Usage vs True Shooting",
    )
    st.plotly_chart(fig, use_container_width=True)

elif page == "Shot Zones":
    st.title("Shot Zones and Efficiency")

    shot_zones = add_zone_labels(data["shot_zones"])
    players = sorted(shot_zones["player"].dropna().unique())
    player = st.selectbox("Select player", players)

    player_shots = shot_zones[shot_zones["player"] == player].copy()

    col1, col2 = st.columns([1.25, 1])
    with col1:
        st.plotly_chart(draw_half_court(player_shots), use_container_width=True)
    with col2:
        st.subheader(f"Zone Breakdown: {player}")
        st.dataframe(
            player_shots[
                ["zone", "fg_pct_label", "efg_pct", "shot_volume", "volume_rank"]
            ].sort_values("volume_rank"),
            use_container_width=True,
        )

        if not player_shots.empty:
            best_zone = player_shots.sort_values("efg_pct", ascending=False).iloc[0]
            worst_zone = player_shots.sort_values("efg_pct", ascending=True).iloc[0]
            st.metric("Best Zone by eFG%", best_zone["zone"], f"{best_zone['efg_pct']:.1%}")
            st.metric("Worst Zone by eFG%", worst_zone["zone"], f"{worst_zone['efg_pct']:.1%}")

elif page == "Pick-and-Roll":
    st.title("Pick-and-Roll Dashboard")

    pnr = data["pnr_duos"].copy()
    pnr["duo"] = pnr["ball_handler"].astype(str) + " + " + pnr["screener"].astype(str)
    pnr["duo_score"] = pnr.apply(calculate_pnr_duo_score, axis=1)

    st.dataframe(
        pnr.sort_values(by="duo_score", ascending=False),
        use_container_width=True,
    )

    fig = px.scatter(
        pnr,
        x="ppp",
        y="net_rating",
        size="possessions",
        color="team",
        text="duo",
        hover_data=["tov_pct", "assist_pct", "shared_minutes", "coverage_note"],
        title="PnR Duo Efficiency and Lineup Impact",
    )
    fig.update_traces(textposition="top center")
    st.plotly_chart(fig, use_container_width=True)

    st.warning(
        "Public data generally does not expose true coverage labels like drop, switch, hedge, blitz, or ICE. "
        "This page uses play-type efficiency and proxy notes unless deeper charting data is added."
    )

elif page == "Lineups":
    st.title("Lineup Analysis")

    lineups = data["lineups"]
    st.dataframe(lineups, use_container_width=True)

    fig = px.bar(
        lineups.sort_values("net_rating", ascending=False),
        x="lineup",
        y="net_rating",
        color="team",
        title="Lineup Net Rating",
    )
    fig.update_layout(xaxis_tickangle=-25)
    st.plotly_chart(fig, use_container_width=True)

elif page == "Matchups":
    st.title("Matchup Matrix")

    matchups = data["matchups"]
    st.dataframe(matchups, use_container_width=True)

    fig = px.bar(
        matchups,
        x="defender",
        y="fg_pct_suppression",
        color="team_defense",
        hover_data=["offender", "possessions", "pts_allowed", "notes"],
        title="FG% Suppression Proxy by Defender",
    )
    st.plotly_chart(fig, use_container_width=True)

elif page == "Methods & Sources":
    st.title("Methods & Sources")

    st.subheader("Current Data Status")
    st.dataframe(source_manifest, use_container_width=True)

    methods = pd.DataFrame(
        [
            {
                "Metric": "ORTG, DRTG, Net Rating, Four Factors",
                "Intended Source": "NBA.com/stats via nba_api",
                "Current Behavior": "Live-first if selected, otherwise sample CSV",
                "Type": "Official when live",
            },
            {
                "Metric": "PER, BPM, VORP, WS/48",
                "Intended Source": "Basketball-Reference",
                "Current Behavior": "Merged into player table when scrape succeeds",
                "Type": "Scraped/reference when live",
            },
            {
                "Metric": "Shot Coordinates and Shot Zones",
                "Intended Source": "NBA ShotChartDetail",
                "Current Behavior": "Summarized by player/zone when request succeeds",
                "Type": "Official when live",
            },
            {
                "Metric": "PnR Duo Score",
                "Intended Source": "NBA SynergyPlayTypes + PBPStats enrichment",
                "Current Behavior": "Attempts Synergy play-type rows; exact duo fallback remains sample/proxy",
                "Type": "Derived/internal",
            },
            {
                "Metric": "Coverage Labels",
                "Intended Source": "No clean public direct source",
                "Current Behavior": "Proxy/caveat only",
                "Type": "Proxy/inferred",
            },
            {
                "Metric": "Lineups and On/Off",
                "Intended Source": "NBA.com/stats + PBPStats",
                "Current Behavior": "Attempts NBA lineup endpoint, optional PBPStats enrichment",
                "Type": "Official/derived when live",
            },
        ]
    )

    st.subheader("Metric Source Manifest")
    st.dataframe(methods, use_container_width=True)

    st.info(
        "Batch 2 adds live ingestion scaffolding and graceful fallbacks. "
        "For production-grade tactical coverage labels, you still need hand-charted data, Second Spectrum/Synergy access, or a validated possession-level classifier."
    )
