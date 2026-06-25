"""Reusable Dash components — stub.

DarkCard, empty_state, red_flag_badge, kpi_chip added as views are built.
"""

from __future__ import annotations

from dash import html

from app.constants import (
    CARD_BG, CARD_BORDER, CARD_ITEM, CARD_MUTED, CARD_SEC, CARD_TEXT,
    FONT_SANS, GREY_LIGHT, TEXT_SEC, CHICAGO,
)


def empty_state(message: str) -> html.Div:
    return html.Div(
        message,
        style={
            "textAlign": "center",
            "color": TEXT_SEC,
            "padding": "60px 20px",
            "fontSize": "15px",
        },
    )


def dark_card(primary: str, secondary: str | None = None, muted: str | None = None) -> html.Div:
    """Dark callout card — Lailara Design System."""
    children = [
        html.Span(primary, style={"fontSize": "28px", "fontWeight": "700",
                                   "color": CARD_TEXT, "display": "block"}),
    ]
    if secondary:
        children.append(html.Span(secondary, style={"fontSize": "13px",
                                                     "color": CARD_SEC, "display": "block"}))
    if muted:
        children.append(html.Span(muted, style={"fontSize": "12px",
                                                 "color": CARD_MUTED, "display": "block"}))
    return html.Div(
        children,
        style={
            "background": CARD_BG,
            "border": f"1px solid {CARD_BORDER}",
            "borderRadius": "2px",
            "padding": "16px 24px",
            "flex": "1",
            "minWidth": "0",
        },
    )


def loading_spinner(message: str) -> html.Div:
    """Spinner with text shown while callbacks are loading."""
    return html.Div([
        html.Div(className="ll-loading-spinner"),
        html.P(message, style={
            "fontFamily": FONT_SANS, "fontSize": "14px",
            "color": TEXT_SEC, "textAlign": "center", "margin": "0",
        }),
    ], style={"textAlign": "center", "padding": "60px 0"})


def kpi_chip(label: str, value: str, *, alert: bool = False) -> html.Div:
    from app.constants import TOKYO_ROSE, INK
    color = TOKYO_ROSE if alert else INK
    return html.Div(
        [
            html.Span(value, style={"fontSize": "22px", "fontWeight": "700",
                                     "color": color, "fontFamily": FONT_SANS}),
            html.Span(label, style={"fontSize": "12px", "color": TEXT_SEC,
                                     "display": "block", "marginTop": "2px"}),
        ],
        style={
            "background": "#ffffff",
            "border": f"1px solid {GREY_LIGHT}",
            "borderRadius": "2px",
            "padding": "12px 20px",
            "minWidth": "120px",
            "display": "inline-block",
            "marginRight": "12px",
        },
    )
