import plotly.graph_objects as go
import pandas as pd


def draw_half_court(shot_df: pd.DataFrame) -> go.Figure:
    fig = go.Figure()

    line = dict(color="#D9DEE8", width=2)

    fig.add_shape(type="rect", x0=-250, y0=-47.5, x1=250, y1=422.5, line=line)
    fig.add_shape(type="circle", x0=-7.5, y0=-7.5, x1=7.5, y1=7.5, line=dict(color="#F58426", width=2))
    fig.add_shape(type="line", x0=-30, y0=-7.5, x1=30, y1=-7.5, line=line)
    fig.add_shape(type="rect", x0=-80, y0=-47.5, x1=80, y1=142.5, line=line)
    fig.add_shape(type="circle", x0=-60, y0=80, x1=60, y1=200, line=line)
    fig.add_shape(type="circle", x0=-40, y0=-40, x1=40, y1=40, line=line)
    fig.add_shape(
        type="path",
        path="M -220 -47.5 L -220 92.5 A 250 250 0 0 1 220 92.5 L 220 -47.5",
        line=line,
    )

    if not shot_df.empty:
        marker_size = shot_df.get("shot_volume", pd.Series([12] * len(shot_df))).clip(lower=9, upper=28)
        fig.add_trace(
            go.Scatter(
                x=shot_df["loc_x"],
                y=shot_df["loc_y"],
                mode="markers",
                marker=dict(
                    size=marker_size,
                    color=shot_df["efg_pct"] if "efg_pct" in shot_df.columns else shot_df["fg_pct"],
                    colorscale="RdYlGn",
                    cmin=0.35,
                    cmax=0.80,
                    showscale=True,
                    colorbar=dict(title="eFG%"),
                    line=dict(width=1, color="white"),
                ),
                customdata=shot_df[["zone", "fg_pct", "efg_pct", "shot_volume"]],
                hovertemplate=(
                    "<b>%{customdata[0]}</b><br>"
                    "FG%: %{customdata[1]:.1%}<br>"
                    "eFG%: %{customdata[2]:.1%}<br>"
                    "Volume Index: %{customdata[3]}<extra></extra>"
                ),
            )
        )

    fig.update_xaxes(range=[-260, 260], visible=False, fixedrange=True)
    fig.update_yaxes(range=[-60, 430], visible=False, fixedrange=True, scaleanchor="x", scaleratio=1)

    fig.update_layout(
        height=520,
        template="plotly_dark",
        paper_bgcolor="#0B0D10",
        plot_bgcolor="#0B0D10",
        margin=dict(l=0, r=0, t=45, b=0),
        title="Half-Court Shot Zone Map",
    )

    return fig
