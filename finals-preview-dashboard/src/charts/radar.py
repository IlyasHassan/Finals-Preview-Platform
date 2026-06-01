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
            )
        )

    fig.update_layout(
        polar=dict(
            radialaxis=dict(
                visible=True,
                range=[0, 100],
                tickfont=dict(size=10),
            )
        ),
        showlegend=True,
        template="plotly_dark",
        title="Team Strength Profile, Percentile Rank",
        margin=dict(l=40, r=40, t=60, b=40),
    )

    return fig
