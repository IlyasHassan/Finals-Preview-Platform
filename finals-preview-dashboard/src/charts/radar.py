import plotly.graph_objects as go
import pandas as pd


def plot_team_radar(df: pd.DataFrame) -> go.Figure:
    categories = [
        "Offense",
        "Defense",
        "Rebounding",
        "Transition",
        "Rim Protection",
        "Perimeter Defense",
    ]

    fig = go.Figure()

    for _, row in df.iterrows():
        values = [
            row.get("off_rank", 50),
            row.get("def_rank", 50),
            row.get("reb_rank", 50),
            row.get("trans_rank", 50),
            row.get("rim_rank", 50),
            row.get("perimeter_rank", 50),
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
        height=430,
        margin=dict(l=30, r=30, t=55, b=30),
        title="Team Strength Profile, Percentile Rank",
        legend=dict(orientation="h", yanchor="bottom", y=-0.15, xanchor="center", x=0.5),
    )

    return fig
