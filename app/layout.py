"""Top-level Dash layout — stub.

Tab children added as U7, U8, U9 are implemented.
"""

from __future__ import annotations

from dash import dcc, html

from app.constants import CANVAS, CHICAGO, FONT_SANS, GREY_LIGHT, TEXT_SEC
from app.tabs import doom_loop, scenario_controls, sop_view


def create_layout() -> html.Div:
    return html.Div(
        style={"backgroundColor": CANVAS, "fontFamily": FONT_SANS},
        children=[
            dcc.Store(id="scenario-params", data={}),

            # Global time-period selector
            _time_period_bar(),

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
                    dcc.Tab(
                        label="Scenario Controls",
                        value=scenario_controls.TAB_ID,
                        children=scenario_controls.layout(),
                        style=_tab_style(),
                        selected_style=_tab_selected_style(),
                    ),
                    dcc.Tab(
                        label="Doom Loop",
                        value=doom_loop.TAB_ID,
                        children=doom_loop.layout(),
                        style=_tab_style(),
                        selected_style=_tab_selected_style(),
                    ),
                ],
            ),
        ],
    )


def _time_period_bar() -> html.Div:
    return html.Div(
        [
            html.Span("Period:", style={
                "fontFamily": FONT_SANS, "fontSize": "13px", "fontWeight": "600",
                "color": TEXT_SEC, "marginRight": "12px",
            }),
            dcc.RadioItems(
                id="time-period-selector",
                options=[
                    {"label": "Full History", "value": "full"},
                    {"label": "Last 12 Months", "value": "12m"},
                    {"label": "Last 6 Months", "value": "6m"},
                    {"label": "Last 3 Months", "value": "3m"},
                ],
                value="full",
                inline=True,
                inputStyle={"marginRight": "4px"},
                labelStyle={
                    "fontFamily": FONT_SANS, "fontSize": "13px",
                    "marginRight": "16px", "cursor": "pointer",
                    "color": TEXT_SEC,
                },
            ),
        ],
        style={
            "padding": "10px 24px",
            "display": "flex",
            "alignItems": "center",
        },
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
