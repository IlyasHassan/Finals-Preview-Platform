import streamlit as st
import pandas as pd
import plotly.express as px

from src.config import SEASON, SEASON_TYPE
from src.ingest.pipeline import load_live_core
from src.ingest.nba_live import fetch_shot_zones_for_player
from src.charts.radar import plot_team_radar
from src.charts.court import draw_half_court
from src.metrics.formatting import as_percent

st.set_page_config(page_title="Knicks vs Spurs Live Finals Scouting", layout="wide")

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


@st.cache_data(ttl=900, show_spinner=False)
def load_data(season, season_type):
    return load_live_core(season, season_type)


@st.cache_data(ttl=900, show_spinner=False)
def load_player_shots(player_id, team, player, season, season_type):
    return fetch_shot_zones_for_player(player_id, team, player, season, season_type)


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


st.sidebar.title("Live NBA Finals Dashboard")
st.sidebar.markdown("**Knicks vs. Spurs**")
st.sidebar.caption("Live-only build. No sample fallback.")

season = st.sidebar.text_input("Season", value=SEASON)
season_type = st.sidebar.selectbox(
    "Season type",
    ["Regular Season", "Playoffs"],
    index=0 if SEASON_TYPE == "Regular Season" else 1,
)

if st.sidebar.button("Clear cache and reload live data"):
    st.cache_data.clear()
    st.rerun()

with st.spinner("Requesting live data from public sources..."):
    data, source_status = load_data(season, season_type)

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

team_stats = data.get("team_stats", pd.DataFrame())
player_stats = data.get("player_stats", pd.DataFrame())
roster = data.get("roster", pd.DataFrame())
lineups = data.get("lineups", pd.DataFrame())
pnr = data.get("pnr", pd.DataFrame())

if page == "Overview":
    st.title("Knicks vs. Spurs Live Finals Scouting Room")
    st.markdown(
        '<div class="section-note">This version does not use placeholder/sample stats. If a source is blocked, the affected table appears as unavailable instead of being replaced with fake data.</div>',
        unsafe_allow_html=True,
    )

    status_counts = source_status["Status"].value_counts().to_dict() if not source_status.empty else {}
    st.caption("Live source status: " + " | ".join([f"{k}: {v}" for k, v in status_counts.items()]))

    if team_stats.empty:
        st.error("Team data is unavailable from the live source. Check Methods & Sources for the exact error.")
    else:
        knicks = team_stats[team_stats["team"] == "Knicks"].iloc[0] if "Knicks" in set(team_stats["team"]) else team_stats.iloc[0]
        spurs = team_stats[team_stats["team"] == "Spurs"].iloc[0] if "Spurs" in set(team_stats["team"]) else team_stats.iloc[-1]

        c1, c2, c3, c4 = st.columns(4)
        with c1:
            metric_card("Knicks Net Rating", f"{knicks['net_rating']:+.1f}", "NBA.com/stats")
        with c2:
            metric_card("Spurs Net Rating", f"{spurs['net_rating']:+.1f}", "NBA.com/stats")
        with c3:
            metric_card("Knicks Pace", f"{knicks['pace']:.1f}", "NBA.com/stats")
        with c4:
            metric_card("Spurs Pace", f"{spurs['pace']:.1f}", "NBA.com/stats")

        left, right = st.columns([1.1, 1])
        with left:
            st.plotly_chart(plot_team_radar(team_stats), use_container_width=True, config=plot_config())
        with right:
            st.subheader("Four Factors")
            cols = ["team", "efg_pct", "ts_pct", "tov_pct", "oreb_pct", "dreb_pct"]
            show = team_stats[[c for c in cols if c in team_stats.columns]]
            st.dataframe(as_percent(show, ["efg_pct", "ts_pct", "tov_pct", "oreb_pct", "dreb_pct"]), hide_index=True, use_container_width=True)

elif page == "Teams":
    st.title("Live Team Comparison")

    if team_stats.empty:
        st.error("Live team stats unavailable. No sample data is being used.")
    else:
        st.dataframe(
            as_percent(team_stats, ["efg_pct", "ts_pct", "tov_pct", "oreb_pct", "dreb_pct"]),
            hide_index=True,
            use_container_width=True,
        )

        col1, col2 = st.columns(2)
        with col1:
            fig = px.bar(team_stats, x="team", y=["ortg", "drtg", "net_rating"], barmode="group", template="plotly_dark", title="Live Efficiency Ratings")
            fig.update_layout(paper_bgcolor="#0B0D10", plot_bgcolor="#0B0D10", legend_title_text="")
            st.plotly_chart(fig, use_container_width=True, config=plot_config())
        with col2:
            fig = px.bar(team_stats, x="team", y=["efg_pct", "ts_pct", "tov_pct"], barmode="group", template="plotly_dark", title="Live Shooting and Turnover Profile")
            fig.update_layout(paper_bgcolor="#0B0D10", plot_bgcolor="#0B0D10", legend_title_text="")
            st.plotly_chart(fig, use_container_width=True, config=plot_config())

elif page == "Players":
    st.title("Live Player Scouting")

    if player_stats.empty:
        st.error("Live player stats unavailable. No sample data is being used.")
    else:
        teams = sorted(player_stats["team"].dropna().unique())
        selected_teams = st.multiselect("Team", teams, default=teams)
        min_minutes = st.slider("Minimum minutes per game", 0.0, 40.0, 8.0, 1.0)

        filtered = player_stats[
            (player_stats["team"].isin(selected_teams))
            & (pd.to_numeric(player_stats["min"], errors="coerce").fillna(0) >= min_minutes)
        ].sort_values(["team", "min"], ascending=[True, False])

        st.dataframe(
            as_percent(filtered, ["fg_pct", "fg3_pct", "ft_pct", "ts_pct", "ws48"]),
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
            hover_data=["position", "min", "pts", "ast", "reb", "net_rating", "per", "bpm"],
            template="plotly_dark",
            title="Live Usage vs True Shooting",
        )
        fig.update_layout(paper_bgcolor="#0B0D10", plot_bgcolor="#0B0D10")
        st.plotly_chart(fig, use_container_width=True, config=plot_config())

elif page == "Shot Zones":
    st.title("Live Shot Zones")

    if player_stats.empty:
        st.error("Player list unavailable, so shot charts cannot be requested.")
    else:
        teams = sorted(player_stats["team"].dropna().unique())
        team = st.selectbox("Team", teams)
        team_players = player_stats[player_stats["team"] == team].sort_values("min", ascending=False)
        player = st.selectbox("Player", team_players["player"].tolist())
        row = team_players[team_players["player"] == player].iloc[0]

        if st.button(f"Fetch live shot zones for {player}"):
            st.cache_data.clear()

        shots, msg = load_player_shots(int(row["player_id"]), team, player, season, season_type)

        st.caption(msg)

        if shots.empty:
            st.error("Live shot-zone data unavailable for this player. No sample chart is being shown.")
        else:
            col1, col2 = st.columns([1.15, 1])
            with col1:
                st.plotly_chart(draw_half_court(shots), use_container_width=True, config=plot_config())
            with col2:
                st.subheader(f"{player}: NBA ShotChartDetail")
                st.dataframe(
                    as_percent(shots[["zone", "fg_pct", "efg_pct", "shot_volume", "volume_rank"]], ["fg_pct", "efg_pct"]),
                    hide_index=True,
                    use_container_width=True,
                )

                best = shots.sort_values("efg_pct", ascending=False).iloc[0]
                worst = shots.sort_values("efg_pct", ascending=True).iloc[0]
                a, b = st.columns(2)
                with a:
                    metric_card("Best Zone", best["zone"], f"{best['efg_pct']:.1%}")
                with b:
                    metric_card("Worst Zone", worst["zone"], f"{worst['efg_pct']:.1%}")

elif page == "Pick-and-Roll":
    st.title("Live Pick-and-Roll Play Types")

    st.info(
        "This page shows live NBA Synergy play-type rows when available. It does not invent handler-screener duo data or coverage labels."
    )

    if pnr.empty:
        st.error("Live PnR/Synergy data unavailable. No sample PnR data is being used.")
    else:
        st.dataframe(as_percent(pnr, ["percentile", "tov_pct", "score_freq"]), hide_index=True, use_container_width=True, height=420)

        fig = px.scatter(
            pnr,
            x="possessions",
            y="ppp",
            color="team",
            symbol="play_type",
            hover_name="player",
            hover_data=["percentile", "tov_pct", "score_freq"],
            template="plotly_dark",
            title="Live PnR Play-Type Efficiency",
        )
        fig.update_layout(paper_bgcolor="#0B0D10", plot_bgcolor="#0B0D10")
        st.plotly_chart(fig, use_container_width=True, config=plot_config())

elif page == "Lineups":
    st.title("Live Lineup Analysis")

    if lineups.empty:
        st.error("Live lineup data unavailable. No sample lineup data is being used.")
    else:
        st.dataframe(as_percent(lineups, ["efg_pct", "tov_pct", "reb_pct"]), hide_index=True, use_container_width=True, height=360)

        fig = px.bar(
            lineups.sort_values("net_rating", ascending=False),
            x="net_rating",
            y="lineup",
            color="team",
            orientation="h",
            template="plotly_dark",
            title="Live Lineup Net Rating",
        )
        fig.update_layout(yaxis={"categoryorder": "total ascending"}, paper_bgcolor="#0B0D10", plot_bgcolor="#0B0D10")
        st.plotly_chart(fig, use_container_width=True, config=plot_config())

elif page == "Matchups":
    st.title("Live Matchups")

    st.warning(
        "This build does not show fake matchup data. Exact player-vs-player matchup rows require a stable matchup endpoint integration or a possession-level parser. No placeholder matrix is displayed."
    )

    if roster.empty:
        st.error("Roster unavailable.")
    else:
        st.subheader("Current live roster pool")
        st.dataframe(roster, hide_index=True, use_container_width=True, height=420)

elif page == "Methods & Sources":
    st.title("Methods & Sources")

    st.subheader("Live Source Status")
    st.dataframe(source_status, hide_index=True, use_container_width=True, height=360)

    st.subheader("Live-only policy")
    st.markdown(
        """
        - No sample CSV fallback is used.
        - If a source is blocked, the app shows the table as unavailable.
        - PnR coverage labels such as drop, switch, hedge, blitz, and ICE are not fabricated.
        - Exact PnR duos are not fabricated from unrelated pass data.
        - Basketball-Reference advanced stats are merged only if the live scrape succeeds.
        - PBPStats is attempted separately and reported in the source-status table.
        """
    )
