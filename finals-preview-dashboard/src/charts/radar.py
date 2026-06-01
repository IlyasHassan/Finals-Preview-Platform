import plotly.graph_objects as go
import pandas as pd


def plot_team_radar(df: pd.DataFrame) -> go.Figure:
    fig = go.Figure()

    if df.empty:
        fig.update_layout(template="plotly_dark", title="Team radar unavailable")
        return fig

    categories = ["Offense", "Defense", "Rebounding", "Pace", "Shooting", "Turnover Care"]

    for _, row in df.iterrows():
        values = [
            row.get("off_rank", 50),
            row.get("def_rank", 50),
            row.get("reb_rank", 50),
            row.get("pace_rank", 50),
            row.get("shooting_rank", 50),
            row.get("turnover_rank", 50),
        ]

        fig.add_trace(
            go.Scatterpolar(
                r=values + [values[0]],
                theta=categories + [categories[0]],
                fill="toself",
                name=row["team"],
                opacity=0.72,
            )
        )

    fig.update_layout(
        polar=dict(
            bgcolor="#0B0D10",
            radialaxis=dict(visible=True, range=[0, 100], gridcolor="#2C3340"),
            angularaxis=dict(gridcolor="#2C3340"),
        ),
        showlegend=True,
        template="plotly_dark",
        height=420,
        margin=dict(l=30, r=30, t=55, b=30),
        title="Snapshot Team Strength Profile",
        legend=dict(orientation="h", yanchor="bottom", y=-0.15, xanchor="center", x=0.5),
        paper_bgcolor="#0B0D10",
        plot_bgcolor="#0B0D10",
    )

    return fig
