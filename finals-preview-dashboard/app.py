import streamlit as st
import pandas as pd
import plotly.express as px

from src.config import SEASON, SEASON_TYPE
from src.ingest.live_pipeline import build_dataset
from src.charts.radar import plot_team_radar
from src.charts.court import draw_half_court
from src.metrics.derived_metrics import calculate_pnr_duo_score, add_zone_labels

st.set_page_config(page_title="Knicks vs Spurs Finals Scouting", layout="wide")


CUSTOM_CSS = """
<style>
.block-container {
    padding-top: 2rem;
    padding-bottom: 3rem;
    max-width: 1180px;
}
[data-testid="stSidebar"] {
    background: #11151C;
}
h1 {
    font-size: 2.15rem !important;
    letter-spacing: -0.04em;
}
h2, h3 {
    letter-spacing: -0.02em;
}
.metric-card {
    background: linear-gradient(180deg, #171D27 0%, #11151C 100%);
    border: 1px solid #2B3442;
    border-radius: 16px;
    padding: 18px 18px 14px 18px;
    min-height: 112px;
}
.metric-label {
    color: #AAB3C2;
    font-size: 0.82rem;
    margin-bottom: 8px;
}
.metric-value {
    color: #FFFFFF;
    font-size: 1.7rem;
    font-weight: 800;
    line-height: 1.1;
}
.metric-sub {
    color: #F58426;
    font-size: 0.78rem;
    margin-top: 8px;
}
.section-note {
    background: #121822;
    border: 1px solid #293241;
    border-radius: 12px;
    padding: 12px 14px;
    color: #C9D2E3;
    font-size: 0.92rem;
}
div[data-testid="stDataFrame"] {
    border: 1px solid #273142;
    border-radius: 12px;
}
</style>
"""
st.markdown(CUSTOM_CSS, unsafe_allow_html=True)


@st.cache_data(ttl=60 * 60, show_spinner=False)
def load_dashboard_data(data_mode: str, season: str, season_type: str):
    # Use startswith instead of exact string comparison so future label edits
    # cannot silently push the app back into sample mode.
    prefer_live = data_mode.startswith("Live-first")
    return build_dataset(prefer_live=prefer_live, season=season, season_type=season_type)


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


def percent_cols(df, cols):
    out = df.copy()
    for col in cols:
        if col in out.columns:
            out[col] = out[col].map(lambda x: f"{x:.1%}" if pd.notna(x) else "")
    return out


def chart_config():
    return {"displayModeBar": False, "responsive": True}


st.sidebar.title("2026 NBA Finals")
st.sidebar.markdown("**Knicks vs. Spurs**")

data_mode = st.sidebar.radio(
    "Data mode",
    ["Live-first + cleaned fallback", "Cleaned sample data"],
    index=0,
    help=(
        "Live-first mode attempts NBA.com/stats, Basketball-Reference, and PBPStats, "
        "then falls back only for sources that fail. Cleaned sample data is available "
        "as a stable offline/demo mode."
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

team_stats = data["team_stats"]
player_stats = data["player_stats"]


if page == "Overview":
    st.title("Knicks vs. Spurs Finals Scouting Room")
    st.markdown(
        '<div class="section-note">Live-first mode is now the default. If a public source blocks Streamlit Cloud, only that table falls back to the cleaned local dataset and the Methods page will show the reason.</div>',
        unsafe_allow_html=True,
    )

    status_counts = source_manifest["Status"].value_counts().to_dict() if "Status" in source_manifest.columns else {}
    st.caption("Source status: " + " | ".join([f"{k}: {v}" for k, v in status_counts.items()]))

    knicks = team_stats[team_stats["team"] == "Knicks"].iloc[0] if "Knicks" in set(team_stats["team"]) else team_stats.iloc[0]
    spurs = team_stats[team_stats["team"] == "Spurs"].iloc[0] if "Spurs" in set(team_stats["team"]) else team_stats.iloc[-1]

    c1, c2, c3, c4 = st.columns(4)
    with c1:
        metric_card("Knicks Net Rating", f"{knicks['net_rating']:+.1f}", "half-court control")
    with c2:
        metric_card("Spurs Net Rating", f"{spurs['net_rating']:+.1f}", "rim pressure + length")
    with c3:
        metric_card("Knicks Pace", f"{knicks['pace']:.1f}", "slower possession profile")
    with c4:
        metric_card("Spurs Pace", f"{spurs['pace']:.1f}", "faster tempo profile")

    left, right = st.columns([1.05, 1])
    with left:
        st.plotly_chart(plot_team_radar(team_stats), use_container_width=True, config=chart_config())
    with right:
        st.subheader("Four Factors Snapshot")
        factors = team_stats[["team", "efg_pct", "ts_pct", "tov_pct", "oreb_pct", "dreb_pct"]].copy()
        st.dataframe(
            percent_cols(factors, ["efg_pct", "ts_pct", "tov_pct", "oreb_pct", "dreb_pct"]),
            use_container_width=True,
            hide_index=True,
            height=160,
        )

        st.subheader("Series Lens")
        st.markdown(
            """
            - **Knicks:** Brunson/Towns creation, wing size, offensive rebounding, and half-court shotmaking.
            - **Spurs:** Wembanyama rim gravity, Fox downhill pressure, Castle/Harper athletic creation, and length at every level.
            - **Key tension:** New York's spacing and rebounding versus San Antonio's rim deterrence and transition pressure.
            """
        )

elif page == "Teams":
    st.title("Team Comparison")

    st.dataframe(
        percent_cols(team_stats, ["efg_pct", "ts_pct", "tov_pct", "oreb_pct", "dreb_pct"]),
        use_container_width=True,
        hide_index=True,
        height=140,
    )

    col1, col2 = st.columns(2)
    with col1:
        fig_eff = px.bar(
            team_stats,
            x="team",
            y=["ortg", "drtg", "net_rating"],
            barmode="group",
            title="Efficiency Ratings",
            template="plotly_dark",
            height=390,
        )
        fig_eff.update_layout(legend_title_text="", paper_bgcolor="#0B0D10", plot_bgcolor="#0B0D10")
        st.plotly_chart(fig_eff, use_container_width=True, config=chart_config())

    with col2:
        fig_def = px.bar(
            team_stats,
            x="team",
            y=["paint_defense", "perimeter_defense"],
            barmode="group",
            title="Paint and Perimeter Defense Scores, Proxy",
            template="plotly_dark",
            height=390,
        )
        fig_def.update_layout(legend_title_text="", paper_bgcolor="#0B0D10", plot_bgcolor="#0B0D10")
        st.plotly_chart(fig_def, use_container_width=True, config=chart_config())

elif page == "Players":
    st.title("Player Scouting")

    teams = sorted(player_stats["team"].dropna().unique())
    col_filter1, col_filter2 = st.columns([1, 1])
    with col_filter1:
        team_filter = st.multiselect("Team", options=teams, default=teams)
    with col_filter2:
        status_filter = st.multiselect(
            "Status",
            options=sorted(player_stats["status"].dropna().unique()),
            default=sorted(player_stats["status"].dropna().unique()),
        )

    filtered = player_stats[
        player_stats["team"].isin(team_filter) & player_stats["status"].isin(status_filter)
    ].sort_values(["team", "min"], ascending=[True, False])

    st.dataframe(
        percent_cols(filtered, ["ts_pct", "ws48"]),
        use_container_width=True,
        hide_index=True,
        height=420,
    )

    fig = px.scatter(
        filtered,
        x="usg_pct",
        y="ts_pct",
        size="pts",
        color="team",
        hover_name="player",
        hover_data=["position", "role", "min", "per", "bpm"],
        title="Usage vs True Shooting",
        template="plotly_dark",
        height=420,
    )
    fig.update_layout(paper_bgcolor="#0B0D10", plot_bgcolor="#0B0D10")
    st.plotly_chart(fig, use_container_width=True, config=chart_config())

elif page == "Shot Zones":
    st.title("Shot Zones and Efficiency")

    shot_zones = add_zone_labels(data["shot_zones"])
    teams = sorted(shot_zones["team"].dropna().unique())
    selected_team = st.selectbox("Team", teams)
    team_players = sorted(shot_zones[shot_zones["team"] == selected_team]["player"].dropna().unique())
    player = st.selectbox("Player", team_players)

    player_shots = shot_zones[shot_zones["player"] == player].copy()

    col1, col2 = st.columns([1.2, 1])
    with col1:
        st.plotly_chart(draw_half_court(player_shots), use_container_width=True, config=chart_config())
    with col2:
        st.subheader(f"{player}: Zone Breakdown")
        zone_display = player_shots[["zone", "fg_pct", "efg_pct", "shot_volume", "volume_rank"]].sort_values("volume_rank")
        st.dataframe(
            percent_cols(zone_display, ["fg_pct", "efg_pct"]),
            use_container_width=True,
            hide_index=True,
            height=255,
        )

        if not player_shots.empty:
            best_zone = player_shots.sort_values("efg_pct", ascending=False).iloc[0]
            worst_zone = player_shots.sort_values("efg_pct", ascending=True).iloc[0]
            a, b = st.columns(2)
            with a:
                metric_card("Best eFG Zone", best_zone["zone"], f"{best_zone['efg_pct']:.1%}")
            with b:
                metric_card("Worst eFG Zone", worst_zone["zone"], f"{worst_zone['efg_pct']:.1%}")

elif page == "Pick-and-Roll":
    st.title("Pick-and-Roll Dashboard")

    pnr = data["pnr_duos"].copy()
    pnr["duo"] = pnr["ball_handler"].astype(str) + " + " + pnr["screener"].astype(str)
    pnr["duo_score"] = pnr.apply(calculate_pnr_duo_score, axis=1)

    st.dataframe(
        percent_cols(
            pnr.sort_values(by="duo_score", ascending=False),
            ["tov_pct", "assist_pct"],
        ),
        use_container_width=True,
        hide_index=True,
        height=330,
    )

    fig = px.scatter(
        pnr,
        x="ppp",
        y="net_rating",
        size="possessions",
        color="team",
        text="duo",
        hover_data=["tov_pct", "assist_pct", "shared_minutes", "coverage_note"],
        title="PnR Efficiency vs Lineup Impact",
        template="plotly_dark",
        height=460,
    )
    fig.update_traces(textposition="top center")
    fig.update_layout(paper_bgcolor="#0B0D10", plot_bgcolor="#0B0D10")
    st.plotly_chart(fig, use_container_width=True, config=chart_config())

    st.info(
        "Coverage labels remain proxy notes unless you add hand-charted data, Second Spectrum/Synergy access, or a validated possession-level classifier."
    )

elif page == "Lineups":
    st.title("Lineup Analysis")

    lineups = data["lineups"].sort_values("net_rating", ascending=False)
    st.dataframe(
        percent_cols(lineups, ["efg_pct", "tov_pct", "reb_pct"]),
        use_container_width=True,
        hide_index=True,
        height=300,
    )

    fig = px.bar(
        lineups,
        x="net_rating",
        y="lineup",
        color="team",
        orientation="h",
        title="Lineup Net Rating",
        template="plotly_dark",
        height=520,
    )
    fig.update_layout(yaxis={"categoryorder": "total ascending"}, paper_bgcolor="#0B0D10", plot_bgcolor="#0B0D10")
    st.plotly_chart(fig, use_container_width=True, config=chart_config())

elif page == "Matchups":
    st.title("Matchup Matrix")

    matchups = data["matchups"].sort_values("fg_pct_suppression")
    st.dataframe(
        percent_cols(matchups, ["fg_pct_allowed", "fg_pct_suppression"]),
        use_container_width=True,
        hide_index=True,
        height=360,
    )

    fig = px.bar(
        matchups,
        x="fg_pct_suppression",
        y="defender",
        color="team_defense",
        orientation="h",
        hover_data=["offender", "possessions", "pts_allowed", "notes"],
        title="FG% Suppression Proxy by Defender",
        template="plotly_dark",
        height=470,
    )
    fig.update_layout(yaxis={"categoryorder": "total ascending"}, paper_bgcolor="#0B0D10", plot_bgcolor="#0B0D10")
    st.plotly_chart(fig, use_container_width=True, config=chart_config())

elif page == "Methods & Sources":
    st.title("Methods & Sources")

    st.subheader("Current Data Status")
    st.dataframe(source_manifest, use_container_width=True, hide_index=True, height=260)

    methods = pd.DataFrame(
        [
            {
                "Metric": "ORTG, DRTG, Net Rating, Four Factors",
                "Intended Source": "NBA.com/stats via nba_api",
                "Current Behavior": "Live-first if selected, otherwise cleaned sample CSV",
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
                "Current Behavior": "Attempts Synergy rows; exact duo fallback remains proxy",
                "Type": "Derived/internal",
            },
            {
                "Metric": "Coverage Labels",
                "Intended Source": "No clean public direct source",
                "Current Behavior": "Proxy notes only",
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
    st.dataframe(methods, use_container_width=True, hide_index=True, height=300)

    st.warning(
        "The cleaned fallback data is still not final official scouting data. Treat it as UI-ready demo/proxy data unless the Methods table says a given table loaded live."
    )
