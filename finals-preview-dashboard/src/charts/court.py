import plotly.graph_objects as go
import pandas as pd


def draw_half_court(shot_df: pd.DataFrame) -> go.Figure:
    fig = go.Figure()

    # Outer boundary
    fig.add_shape(type="rect", x0=-250, y0=-47.5, x1=250, y1=422.5, line_color="white")

    # Hoop and backboard
    fig.add_shape(type="circle", x0=-7.5, y0=-7.5, x1=7.5, y1=7.5, line_color="orange")
    fig.add_shape(type="line", x0=-30, y0=-7.5, x1=30, y1=-7.5, line_color="white")

    # Paint and free throw circle
    fig.add_shape(type="rect", x0=-80, y0=-47.5, x1=80, y1=142.5, line_color="white")
    fig.add_shape(type="circle", x0=-60, y0=80, x1=60, y1=200, line_color="white")

    # Restricted area approximation
    fig.add_shape(type="circle", x0=-40, y0=-40, x1=40, y1=40, line_color="white")

    # Simplified 3PT line
    fig.add_shape(
        type="path",
        path="M -220 -47.5 L -220 92.5 A 250 250 0 0 1 220 92.5 L 220 -47.5",
        line_color="white",
    )

    if not shot_df.empty:
        marker_size = shot_df.get("shot_volume", pd.Series([12] * len(shot_df))).clip(lower=8, upper=24)
        fig.add_trace(
            go.Scatter(
                x=shot_df["loc_x"],
                y=shot_df["loc_y"],
                mode="markers+text",
                text=shot_df["zone"],
                textposition="top center",
                marker=dict(
                    size=marker_size,
                    color=shot_df["fg_pct"],
                    colorscale="RdYlGn",
                    cmin=0.30,
                    cmax=0.80,
                    showscale=True,
                    colorbar=dict(title="FG%"),
                    line=dict(width=1, color="white"),
                ),
                hovertemplate=(
                    "<b>%{text}</b><br>"
                    "FG%: %{marker.color:.1%}<br>"
                    "Volume Index: %{marker.size}<extra></extra>"
                ),
            )
        )

    fig.update_xaxes(range=[-260, 260], visible=False, fixedrange=True)
    fig.update_yaxes(range=[-60, 430], visible=False, fixedrange=True, scaleanchor="x", scaleratio=1)

    fig.update_layout(
        width=650,
        height=620,
        template="plotly_dark",
        margin=dict(l=10, r=10, t=40, b=10),
        title="Half-Court Shot Zone Map",
    )

    return fig
