"""Top-level Dash layout — stub.

Tab children added as U7, U8, U9 are implemented.
"""

from __future__ import annotations

from dash import dcc, html

from app.constants import CANVAS, CHICAGO, FONT_SANS, FONT_SERIF, GREY_LIGHT, INK, TEXT_SEC
from app.tabs import sop_view


def create_layout() -> html.Div:
    return html.Div(
        style={"backgroundColor": CANVAS, "minHeight": "100vh", "fontFamily": FONT_SANS},
        children=[
            dcc.Store(id="scenario-params", data={}),

            # Header
            html.Div(
                [
                    html.H1(
                        "Production Demand Forecast",
                        style={
                            "fontFamily": FONT_SERIF,
                            "fontWeight": "700",
                            "fontSize": "26px",
                            "color": INK,
                            "margin": "0 0 4px 0",
                        },
                    ),
                    html.P(
                        "S&OP · Scenario Modeling · Doom Loop",
                        style={
                            "fontFamily": FONT_SANS,
                            "fontSize": "13px",
                            "color": TEXT_SEC,
                            "letterSpacing": "0.04em",
                            "textTransform": "uppercase",
                            "margin": "0",
                        },
                    ),
                ],
                style={
                    "padding": "24px 32px 16px",
                    "borderBottom": f"1px solid {GREY_LIGHT}",
                    "backgroundColor": CANVAS,
                },
            ),

            # Tabs
            dcc.Tabs(
                id="main-tabs",
                value=sop_view.TAB_ID,
                style={"borderBottom": f"1px solid {GREY_LIGHT}"},
                colors={"border": GREY_LIGHT, "primary": CHICAGO, "background": CANVAS},
                children=[
                    dcc.Tab(
                        label="S&OP View",
                        value=sop_view.TAB_ID,
                        children=sop_view.layout(),
                        style=_tab_style(),
                        selected_style=_tab_selected_style(),
                    ),
                    # U8: Scenario Controls — added when implemented
                    # U9: Doom Loop — added when implemented
                ],
            ),
        ],
    )


def _tab_style() -> dict:
    return {
        "fontFamily": FONT_SANS,
        "fontSize": "14px",
        "padding": "12px 20px",
        "backgroundColor": CANVAS,
        "color": TEXT_SEC,
        "border": "none",
        "borderBottom": "2px solid transparent",
    }


def _tab_selected_style() -> dict:
    return {
        **_tab_style(),
        "color": CHICAGO,
        "fontWeight": "600",
        "borderBottom": f"2px solid {CHICAGO}",
    }
