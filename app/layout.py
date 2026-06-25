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

            # Tabs — story order: problem → data → stress-test
            dcc.Tabs(
                id="main-tabs",
                value=doom_loop.TAB_ID,
                style={"borderBottom": f"1px solid {GREY_LIGHT}"},
                colors={"border": GREY_LIGHT, "primary": CHICAGO, "background": CANVAS},
                children=[
                    dcc.Tab(
                        label="The Problem",
                        value=doom_loop.TAB_ID,
                        children=doom_loop.layout(),
                        style=_tab_style(),
                        selected_style=_tab_selected_style(),
                    ),
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
