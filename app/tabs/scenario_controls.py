"""Scenario controls tab — promo lift, new doors, lead-time slip.

Controls write to the shared `dcc.Store(id="scenario-params")` which
triggers the S&OP view callback to recompute the table.

AE3: Adjusting any control and clicking "Apply" updates the S&OP table
within one server round-trip (no full page reload).
"""

from __future__ import annotations

import pandas as pd
from dash import Input, Output, State, dcc, html, no_update

from app.components import empty_state, loading_spinner
from app.constants import (
    CANVAS, CHICAGO, FONT_SANS, FONT_SERIF, GREY_LIGHT, INK,
    SG_ORANGE, SURFACE_FAIL, SURFACE_WARN, TEAL, TEXT, TEXT_SEC, TOKYO_ROSE,
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


def _controls_column() -> html.Div:
    return html.Div([
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
        ], style={"marginTop": "8px"}),
    ], style={"flex": "0 1 380px", "maxWidth": "380px", "minWidth": "0"})


def layout() -> html.Div:
    return html.Div([
        html.H2(
            "Scenario Controls",
            style={"fontFamily": FONT_SERIF, "fontWeight": "700",
                   "fontSize": "22px", "marginBottom": "4px", "color": INK},
        ),
        html.P(
            "Model how changes to demand or production constraints affect stockout timing. "
            "Adjust the inputs, then Apply — the impact appears on the right.",
            style={"fontSize": "14px", "color": TEXT_SEC, "marginBottom": "24px"},
        ),

        # Two columns: controls (left) + live results (right)
        html.Div(
            [
                _controls_column(),
                dcc.Loading(
                    custom_spinner=loading_spinner("Running scenario…"),
                    children=html.Div(
                        id="scenario-results",
                        style={"minWidth": "0"},
                    ),
                    style={"flex": "1 1 auto", "minWidth": "0"},
                ),
            ],
            style={"display": "flex", "gap": "40px", "flexWrap": "wrap",
                   "alignItems": "flex-start"},
        ),
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

    @app.callback(
        Output("scenario-results", "children"),
        Input("scenario-params", "data"),
    )
    def update_results(scenario_data):
        from app.data import get_sop_summary
        scenario = scenario_data or {}
        promo_lift_pct = float(scenario.get("promo_lift_pct", 0.0))
        new_doors      = int(scenario.get("new_doors", 0))
        lead_time_slip = int(scenario.get("lead_time_slip_weeks", 0))

        sop = get_sop_summary(
            promo_lift_pct=promo_lift_pct,
            new_doors=new_doors,
            lead_time_slip_weeks=lead_time_slip,
        )
        if sop.empty:
            return empty_state("No S&OP data available for this scenario.")

        baseline = get_sop_summary()
        return _build_results(sop, baseline, promo_lift_pct, new_doors, lead_time_slip)


def _build_results(sop, baseline, promo_lift_pct: float, new_doors: int,
                   lead_time_slip: int) -> html.Div:
    """Render the scenario impact: heading, KPIs with baseline deltas, and urgent SKUs."""
    is_scenario = promo_lift_pct > 0 or new_doors > 0 or lead_time_slip > 0

    if is_scenario:
        parts = []
        if promo_lift_pct > 0:
            parts.append(f"+{int(promo_lift_pct*100)}% promo lift")
        if new_doors > 0:
            parts.append(f"{new_doors:,} new doors")
        if lead_time_slip > 0:
            parts.append(f"+{lead_time_slip}wk lead-time slip")
        scenario_label = "Scenario: " + ", ".join(parts)
    else:
        scenario_label = "Scenario: Baseline"

    total_skus    = len(sop)
    need_action   = int(sop["deadline_flag"].isin(["PAST_DUE", "CRITICAL", "WARNING"]).sum())
    critical_conf = int(
        sop[sop["deadline_flag"].isin(["PAST_DUE", "CRITICAL"])]["shared_line_conflict"].sum()
    )

    # Baseline metrics for delta comparison
    bl_need_action = 0
    bl_critical_conf = 0
    if not baseline.empty:
        bl_need_action = int(baseline["deadline_flag"].isin(["PAST_DUE", "CRITICAL", "WARNING"]).sum())
        bl_critical_conf = int(
            baseline[baseline["deadline_flag"].isin(["PAST_DUE", "CRITICAL"])]["shared_line_conflict"].sum()
        )

    # Earliest stockouts — soonest decision deadlines first
    ranked = sop.copy()
    ranked["_days"] = pd.to_numeric(ranked.get("days_until_deadline"), errors="coerce")
    ranked = ranked.sort_values("_days", na_position="last").head(6)

    # Merge baseline flags for comparison column
    if is_scenario and not baseline.empty:
        bl_flags = baseline[["sku", "deadline_flag"]].rename(
            columns={"deadline_flag": "baseline_flag"}
        )
        ranked = ranked.merge(bl_flags, on="sku", how="left")
    else:
        ranked["baseline_flag"] = ranked["deadline_flag"]

    # Narrative line summarizing the shift
    narrative = None
    if is_scenario and not baseline.empty:
        narrative = _build_narrative(sop, baseline)

    children = [
        html.Div(scenario_label,
                 style={"fontSize": "13px", "color": TEXT_SEC, "marginBottom": "4px"}),
    ]

    if narrative:
        children.append(html.P(
            narrative,
            style={"fontSize": "13px", "color": INK, "marginBottom": "12px",
                   "fontStyle": "italic"},
        ))

    children.append(html.Div([
        _kpi_with_delta("Total SKUs", total_skus, total_skus, higher_is_worse=False),
        _kpi_with_delta("Need Action", need_action, bl_need_action, higher_is_worse=True),
        _kpi_with_delta("Critical Conflicts", critical_conf, bl_critical_conf, higher_is_worse=True),
    ], style={"marginBottom": "20px"}))

    children.append(html.H3(
        "Most urgent SKUs",
        style={"fontFamily": FONT_SERIF, "fontWeight": "700",
               "fontSize": "16px", "marginBottom": "8px", "color": INK},
    ))
    children.append(_urgent_table(ranked, show_baseline=is_scenario))

    return html.Div(children)


def _kpi_with_delta(label: str, value: int, baseline: int,
                    *, higher_is_worse: bool) -> html.Div:
    """KPI chip with baseline comparison. Shows delta when values differ."""
    from app.constants import TOKYO_ROSE, INK
    alert = higher_is_worse and value > 0
    color = TOKYO_ROSE if alert else INK
    delta = value - baseline

    children = [
        html.Span(str(value), style={"fontSize": "22px", "fontWeight": "700",
                                      "color": color, "fontFamily": FONT_SANS}),
        html.Span(label, style={"fontSize": "12px", "color": TEXT_SEC,
                                 "display": "block", "marginTop": "2px"}),
    ]

    if delta != 0:
        delta_color = TOKYO_ROSE if (higher_is_worse and delta > 0) or (not higher_is_worse and delta < 0) else TEAL
        sign = "+" if delta > 0 else ""
        children.append(html.Span(
            f"Baseline: {baseline} | {sign}{delta}",
            style={"fontSize": "11px", "color": delta_color, "display": "block",
                   "marginTop": "4px", "fontWeight": "600"},
        ))

    return html.Div(
        children,
        style={
            "background": "#ffffff",
            "border": f"1px solid {GREY_LIGHT}",
            "borderRadius": "2px",
            "padding": "12px 20px",
            "minWidth": "120px",
            "display": "inline-block",
            "marginRight": "12px",
            "verticalAlign": "top",
        },
    )


def _build_narrative(sop, baseline) -> str:
    """One-line summary of how the scenario shifted stockout timing."""
    sop_days = pd.to_numeric(sop.get("days_until_deadline"), errors="coerce")
    bl_days = pd.to_numeric(baseline.get("days_until_deadline"), errors="coerce")

    sop_mean = sop_days.mean()
    bl_mean = bl_days.mean()

    if pd.isna(sop_mean) or pd.isna(bl_mean):
        return ""

    diff = bl_mean - sop_mean
    need_action = int(sop["deadline_flag"].isin(["PAST_DUE", "CRITICAL", "WARNING"]).sum())

    if abs(diff) < 0.5:
        return ""

    if diff > 0:
        return (
            f"This scenario accelerates average stockout by {diff:.1f} days "
            f"across {need_action} affected SKUs."
        )
    return (
        f"This scenario delays average stockout by {abs(diff):.1f} days "
        f"across {need_action} affected SKUs."
    )


def _urgent_table(ranked, *, show_baseline: bool = False) -> html.Table:
    headers = ["SKU", "Product", "Stockout", "Decision By", "Days", "Flag"]
    if show_baseline:
        headers.append("Baseline")
    header_row = html.Tr([
        html.Th(h, style={"textAlign": "left", "fontFamily": FONT_SANS,
                          "fontSize": "12px", "color": TEXT_SEC, "fontWeight": "600",
                          "padding": "6px 10px", "borderBottom": f"1px solid {GREY_LIGHT}"})
        for h in headers
    ])
    rows = []
    for _, r in ranked.iterrows():
        flag = str(r.get("deadline_flag", ""))
        bg = (SURFACE_FAIL if flag in ("PAST_DUE", "CRITICAL")
              else SURFACE_WARN if flag == "WARNING" else "#ffffff")
        days = r.get("days_until_deadline")
        days_txt = str(int(days)) if days is not None and pd.notna(days) else "—"
        cells = [
            r.get("sku", ""),
            str(r.get("product_name", ""))[:26],
            _fmt(r.get("stockout_date")),
            _fmt(r.get("decision_deadline")),
            days_txt,
            flag,
        ]
        if show_baseline:
            cells.append(str(r.get("baseline_flag", "—")))
        rows.append(html.Tr([
            html.Td(c, style={"fontFamily": FONT_SANS, "fontSize": "13px",
                              "padding": "6px 10px",
                              "borderBottom": f"1px solid {GREY_LIGHT}"})
            for c in cells
        ], style={"backgroundColor": bg}))
    return html.Table([html.Thead(header_row), html.Tbody(rows)],
                      style={"borderCollapse": "collapse", "width": "100%"})


def _fmt(d) -> str:
    try:
        if d is None or (isinstance(d, float) and pd.isna(d)):
            return "—"
        ts = pd.Timestamp(d)
        return ts.strftime("%b ") + str(ts.day)
    except Exception:
        return str(d)[:10] if d else "—"
