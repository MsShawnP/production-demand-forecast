"""Plotly chart helpers — Lailara Design System v2 styling.

Copied from competitive-shelf-intelligence/app/charts.py.
add_vline_at_date() is required for pandas 3.x + plotly 6.x compatibility
(plotly's built-in add_vline does integer arithmetic on Timestamp, which
raises TypeError on those versions).
"""

from __future__ import annotations

import plotly.graph_objects as go

from app.constants import (
    CANVAS,
    FONT_SANS,
    GREY_LIGHT,
    INK,
    TEXT_SEC,
)


def base_chart_layout(
    *,
    height: int,
    x_title: str | None = None,
    y_title: str | None = None,
    show_legend: bool = False,
    left_margin: int = 10,
) -> dict:
    return dict(
        template="simple_white",
        paper_bgcolor=CANVAS,
        plot_bgcolor=CANVAS,
        height=height,
        margin=dict(l=left_margin, r=90, t=40, b=50),
        yaxis=dict(
            title=y_title,
            tickfont=dict(family=FONT_SANS, size=12, color=TEXT_SEC),
            gridcolor=GREY_LIGHT,
            linecolor=GREY_LIGHT,
        ),
        xaxis=dict(
            title=x_title,
            title_font=dict(family=FONT_SANS, size=14, color=TEXT_SEC),
            tickfont=dict(family=FONT_SANS, size=12, color=TEXT_SEC),
            showgrid=False,
            linecolor=GREY_LIGHT,
            zerolinecolor=GREY_LIGHT,
        ),
        showlegend=show_legend,
        font=dict(family=FONT_SANS, size=14, color=INK),
        bargap=0.25,
    )


def add_vline_at_date(
    fig: go.Figure,
    x,
    label: str,
    *,
    color: str,
    dash: str = "dash",
    width: float = 1.5,
    annotation_position: str = "top",
) -> None:
    """Vertical reference line safe for pandas 3.x + plotly 6.x.

    plotly.add_vline() does integer arithmetic on Timestamp, which raises
    TypeError on those versions. This helper draws the line as a shape.
    """
    fig.add_shape(
        type="line", xref="x", yref="paper",
        x0=x, x1=x, y0=0, y1=1,
        line=dict(color=color, dash=dash, width=width),
    )
    pos = annotation_position
    y = 1.0
    yshift = -8
    y_anchor = "top"
    if pos.startswith("bottom"):
        y = 0.0
        yshift = 8
        y_anchor = "bottom"
    xanchor = "center"
    if "left" in pos:
        xanchor = "right"
    elif "right" in pos:
        xanchor = "left"
    fig.add_annotation(
        x=x, y=y, xref="x", yref="paper",
        text=label,
        showarrow=False,
        font=dict(family=FONT_SANS, size=12, color=INK),
        bgcolor="rgba(245,243,238,0.95)",
        bordercolor=GREY_LIGHT, borderwidth=1, borderpad=4,
        xanchor=xanchor, yanchor=y_anchor, yshift=yshift,
    )
