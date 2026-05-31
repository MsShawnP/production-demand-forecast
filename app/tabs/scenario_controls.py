"""Scenario controls tab — promo lift, new doors, lead-time slip.

Controls write to the shared `dcc.Store(id="scenario-params")` which
triggers the S&OP view callback to recompute the table.

AE3: Adjusting any control and clicking "Apply" updates the S&OP table
within one server round-trip (no full page reload).
"""

from __future__ import annotations

from dash import Input, Output, State, dcc, html, no_update

from app.constants import (
    CANVAS, CHICAGO, FONT_SANS, FONT_SERIF, GREY_LIGHT, INK,
    SG_ORANGE, TEXT, TEXT_SEC, TOKYO_ROSE,
)

TAB_ID = "tab-scenario"

_INPUT_STYLE = {
    "fontFamily": FONT_SANS,
    "fontSize": "15px",
    "border": f"1px solid {GREY_LIGHT}",
    "borderRadius": "2px",
    "padding": "6px 10px",
    "width": "100%",
    "boxSizing": "border-box",
}
_LABEL_STYLE = {
    "fontFamily": FONT_SANS,
    "fontSize": "13px",
    "color": TEXT_SEC,
    "display": "block",
    "marginBottom": "4px",
}
_GROUP_STYLE = {
    "marginBottom": "24px",
    "maxWidth": "460px",
}


def layout() -> html.Div:
    return html.Div([
        html.H2(
            "Scenario Controls",
            style={"fontFamily": FONT_SERIF, "fontWeight": "700",
                   "fontSize": "22px", "marginBottom": "4px", "color": INK},
        ),
        html.P(
            "Model how changes to demand or production constraints affect stockout timing.",
            style={"fontSize": "14px", "color": TEXT_SEC, "marginBottom": "24px"},
        ),

        # Inline validation message
        html.Div(id="scenario-validation-msg",
                 style={"color": TOKYO_ROSE, "fontSize": "13px",
                        "marginBottom": "12px", "minHeight": "18px"}),

        # Control group 1: Promo lift
        html.Div([
            html.Label("Promo demand lift (%)", style=_LABEL_STYLE),
            html.P(
                "Raise the forecast for all SKUs by this percentage for the full 12-week window.",
                style={"fontSize": "12px", "color": TEXT_SEC, "marginBottom": "8px"},
            ),
            dcc.Slider(
                id="scenario-promo-slider",
                min=0, max=50, step=5, value=0,
                marks={i: f"{i}%" for i in range(0, 51, 10)},
                tooltip={"placement": "bottom", "always_visible": False},
            ),
        ], style=_GROUP_STYLE),

        # Control group 2: New retailer doors
        html.Div([
            html.Label("New retailer doors launching in week 1", style=_LABEL_STYLE),
            html.P(
                "Additional retail doors adds demand at the median per-store velocity.",
                style={"fontSize": "12px", "color": TEXT_SEC, "marginBottom": "8px"},
            ),
            dcc.Input(
                id="scenario-doors-input",
                type="number", min=0, max=5000, step=50, value=0,
                debounce=True,
                style=_INPUT_STYLE,
            ),
        ], style=_GROUP_STYLE),

        # Control group 3: Lead-time slip
        html.Div([
            html.Label("Co-packer lead-time increase (weeks)", style=_LABEL_STYLE),
            html.P(
                "Adds N weeks to every SKU's lead time — simulating a co-packer delay.",
                style={"fontSize": "12px", "color": TEXT_SEC, "marginBottom": "8px"},
            ),
            dcc.Slider(
                id="scenario-leadtime-slider",
                min=0, max=12, step=1, value=0,
                marks={i: str(i) for i in range(0, 13, 2)},
                tooltip={"placement": "bottom", "always_visible": False},
            ),
        ], style=_GROUP_STYLE),

        # Action buttons
        html.Div([
            html.Button(
                "Apply Scenario",
                id="scenario-apply-btn",
                style={
                    "backgroundColor": CHICAGO,
                    "color": "#ffffff",
                    "fontFamily": FONT_SANS,
                    "fontWeight": "600",
                    "fontSize": "14px",
                    "border": "none",
                    "borderRadius": "2px",
                    "padding": "10px 24px",
                    "cursor": "pointer",
                    "marginRight": "12px",
                },
            ),
            html.Button(
                "Reset to Baseline",
                id="scenario-reset-btn",
                style={
                    "backgroundColor": "#ffffff",
                    "color": CHICAGO,
                    "fontFamily": FONT_SANS,
                    "fontWeight": "600",
                    "fontSize": "14px",
                    "border": f"1px solid {CHICAGO}",
                    "borderRadius": "2px",
                    "padding": "10px 24px",
                    "cursor": "pointer",
                },
            ),
        ], style={"marginBottom": "24px"}),

    ], style={"padding": "24px"})


def register_callbacks(app) -> None:

    @app.callback(
        Output("scenario-params", "data"),
        Output("scenario-validation-msg", "children"),
        Input("scenario-apply-btn", "n_clicks"),
        State("scenario-promo-slider", "value"),
        State("scenario-doors-input", "value"),
        State("scenario-leadtime-slider", "value"),
        prevent_initial_call=True,
    )
    def apply_scenario(n_clicks, promo_pct, doors, lead_slip):
        # Input validation
        if promo_pct is not None and promo_pct > 100:
            return no_update, "Promo lift cannot exceed 100%."
        if doors is not None and doors < 0:
            return no_update, "New doors cannot be negative."
        if lead_slip is not None and lead_slip < 0:
            return no_update, "Lead-time slip cannot be negative."

        promo_lift_pct = (promo_pct or 0) / 100.0
        new_doors = int(doors or 0)
        lead_slip_weeks = int(lead_slip or 0)

        return {
            "promo_lift_pct": promo_lift_pct,
            "new_doors": new_doors,
            "lead_time_slip_weeks": lead_slip_weeks,
        }, ""

    @app.callback(
        Output("scenario-promo-slider", "value"),
        Output("scenario-doors-input", "value"),
        Output("scenario-leadtime-slider", "value"),
        Input("scenario-reset-btn", "n_clicks"),
        prevent_initial_call=True,
    )
    def reset_scenario(n_clicks):
        return 0, 0, 0
