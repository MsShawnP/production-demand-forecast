"""S&OP view tab — per-SKU forward view with stockout dates and decision deadlines.

Tab structure follows competitive-shelf-intelligence/app/tabs/oos_tracker.py:
    TAB_ID, layout(), register_callbacks(app)

Layout:
    1. Summary row: 3 KPI chips (total SKUs, SKUs needing action, critical conflicts)
    2. AG Grid: per-SKU table with conditional row formatting
    3. Detail panel: inventory runway chart + doom loop framing (on row click)
    4. Export buttons (wired in U10 — stubs here)
"""

from __future__ import annotations

import logging

import pandas as pd
import plotly.graph_objects as go
from dash import Input, Output, State, dcc, html, no_update

logger = logging.getLogger(__name__)

import base64

import dash_ag_grid as dag

from app.charts import add_vline_at_date, base_chart_layout
from app.components import empty_state, kpi_chip, loading_spinner
from app.constants import (
    CANVAS, CHICAGO, DEADLINE_CRITICAL, DEADLINE_WARNING, FONT_SANS,
    FONT_SERIF, GREY_LIGHT, INK, SG_ORANGE, SURFACE_FAIL, SURFACE_PASS,
    SURFACE_WARN, TEXT_SEC, TEAL, TOKYO_ROSE,
)
from app.data import _DEMO_AS_OF_DATE

_REVIEW_DATE_LABEL = (
    pd.Timestamp(_DEMO_AS_OF_DATE).strftime("%B ")
    + str(pd.Timestamp(_DEMO_AS_OF_DATE).day)
    + pd.Timestamp(_DEMO_AS_OF_DATE).strftime(", %Y")
)

TAB_ID = "tab-sop"

_COLUMN_DEFS = [
    {"field": "sku",                "headerName": "SKU",         "width": 110,
     "headerTooltip": "SKU code"},
    {"field": "product_name",       "headerName": "Product",     "flex": 1,
     "headerTooltip": "Product name"},
    {"field": "weekly_forecast_mean", "headerName": "Fcst/wk",   "width": 75,
     "type": "numericColumn", "headerTooltip": "Forecast units per week",
     "valueFormatter": {"function": "params.value ? params.value.toFixed(0) : '—'"}},
    {"field": "stockout_week_label", "headerName": "Stockout",   "width": 90,
     "headerTooltip": "Projected stockout date"},
    {"field": "deadline_label",     "headerName": "Decide By",   "width": 90,
     "headerTooltip": "Last date to order production"},
    {"field": "days_until_deadline", "headerName": "Days",       "width": 55,
     "type": "numericColumn", "headerTooltip": "Days until decision deadline",
     "valueFormatter": {"function": "params.value != null ? params.value : '—'"}},
    {"field": "deadline_flag",      "headerName": "Flag",        "width": 85,
     "headerTooltip": "PAST_DUE / CRITICAL / WARNING / OK"},
    {"field": "conflict_label",     "headerName": "Conflict",    "width": 100,
     "headerTooltip": "Shared line: AS=Artisan Sauces, DG=Dried Goods, PS=Pantry Staples, SB=Snack Bites, SC=Specialty Condiments"},
]

_LINE_ABBREV = {
    "Artisan Sauces": "AS",
    "Dried Goods": "DG",
    "Pantry Staples": "PS",
    "Snack Bites": "SB",
    "Specialty Condiments": "SC",
}

_ROW_STYLE = {
    "styleConditions": [
        {
            "condition": "params.data.deadline_flag === 'PAST_DUE' || params.data.deadline_flag === 'CRITICAL'",
            "style": {"backgroundColor": SURFACE_FAIL, "color": "#7a0906"},
        },
        {
            "condition": "params.data.deadline_flag === 'WARNING'",
            "style": {"backgroundColor": SURFACE_WARN},
        },
        {
            "condition": "params.data.deadline_flag === 'OK' || params.data.deadline_flag == null",
            "style": {"backgroundColor": SURFACE_PASS},
        },
    ]
}


def layout() -> html.Div:
    return html.Div([
        html.H2(
            "S&OP Decision View",
            style={"fontFamily": FONT_SERIF, "fontWeight": "700",
                   "fontSize": "22px", "marginBottom": "4px", "color": INK},
        ),
        html.P(
            "Which SKUs stock out, when, and when is the last date to act.",
            style={"fontSize": "14px", "color": TEXT_SEC, "marginBottom": "8px"},
        ),
        html.P(
            f"S&OP review, {_REVIEW_DATE_LABEL}. All deadlines relative to this date.",
            style={"fontSize": "12px", "color": TEXT_SEC, "marginBottom": "20px"},
        ),

        dcc.Loading(
            custom_spinner=loading_spinner("Calculating forecasts…"),
            children=[
                html.Div(id="sop-lead-text", style={"marginBottom": "20px"}),
                html.Div(id="sop-kpi-row", style={"marginBottom": "20px"}),
                html.Div(id="sop-scenario-chip",
                         style={"marginBottom": "12px", "fontSize": "13px",
                                "color": TEXT_SEC}),
                dag.AgGrid(
                    id="sop-grid",
                    columnDefs=_COLUMN_DEFS,
                    rowData=[],
                    defaultColDef={
                        "sortable": True, "filter": True, "resizable": True,
                        "suppressHeaderMenuButton": True,
                        "cellStyle": {"fontFamily": FONT_SANS, "fontSize": "13px"},
                    },
                    rowStyle=_ROW_STYLE,
                    style={"height": "500px", "width": "100%"},
                    dashGridOptions={
                        "rowSelection": "single",
                        "animateRows": True,
                        "domLayout": "normal",
                        "suppressHorizontalScroll": True,
                    },
                    className="ag-theme-alpine",
                ),
                html.Div([
                    html.Button(
                        "Download MPS Workbook (.xlsx)",
                        id="sop-export-xlsx-btn",
                        style=_btn_style(),
                    ),
                    html.Button(
                        "Download Decision Brief (.pdf)",
                        id="sop-export-pdf-btn",
                        style={**_btn_style(), "marginLeft": "8px",
                               "backgroundColor": TEXT_SEC},
                    ),
                    dcc.Download(id="sop-download-xlsx"),
                    dcc.Download(id="sop-download-pdf"),
                ], style={"marginTop": "16px", "marginBottom": "24px"}),
                html.Div(id="sop-detail-panel"),
            ],
        ),

    ], style={"padding": "24px"})


def register_callbacks(app) -> None:

    @app.callback(
        Output("sop-lead-text", "children"),
        Output("sop-grid", "rowData"),
        Output("sop-kpi-row", "children"),
        Output("sop-scenario-chip", "children"),
        Input("scenario-params", "data"),
    )
    def update_table(scenario_data):
        from app.data import get_sop_summary
        scenario = scenario_data or {}
        promo_lift_pct    = float(scenario.get("promo_lift_pct", 0.0))
        new_doors         = int(scenario.get("new_doors", 0))
        lead_time_slip    = int(scenario.get("lead_time_slip_weeks", 0))

        sop = get_sop_summary(
            promo_lift_pct=promo_lift_pct,
            new_doors=new_doors,
            lead_time_slip_weeks=lead_time_slip,
        )

        if sop.empty:
            return "", [], empty_state("No S&OP data available."), ""

        # Prepare display columns
        sop = sop.copy()
        sop["stockout_week_label"] = sop["stockout_date"].apply(
            lambda d: _format_date(d) if d is not None and pd.notna(d) else "—"
        )
        sop["deadline_label"] = sop["decision_deadline"].apply(
            lambda d: _format_date(d) if d is not None and pd.notna(d) else "—"
        )
        sop["conflict_label"] = sop.apply(
            lambda r: f"⚠ {_LINE_ABBREV.get(r.get('product_line', ''), r.get('product_line', '?'))}"
            if r.get("shared_line_conflict") else "",
            axis=1,
        )

        row_data = sop.to_dict("records")

        # KPI chips
        total_skus    = len(sop)
        need_action   = int(sop["deadline_flag"].isin(["PAST_DUE", "CRITICAL", "WARNING"]).sum())
        critical_conf = int(sop["shared_line_conflict"].sum())
        kpi_row = html.Div([
            kpi_chip("SKUs in the plan", str(total_skus)),
            kpi_chip("Need a production order now", str(need_action), alert=need_action > 0),
            kpi_chip("Competing for the same line", str(critical_conf), alert=critical_conf > 0),
        ])

        lead_text = html.Div([
            html.P(
                "Outsourcing production lowers fixed costs, but it replaces a "
                "production problem with a planning problem. Every SKU below "
                "depends on a co-packer with shared lines, fixed minimums, and "
                "lead times that punish late decisions.",
                style={"fontFamily": FONT_SANS, "fontSize": "15px",
                       "lineHeight": "1.6", "color": TEXT_SEC,
                       "marginBottom": "12px"},
            ),
            html.P(
                f"Of {total_skus} SKUs in the plan, {need_action} will stock out "
                f"unless a production run is placed — and for most, the ordering "
                f"window has already closed. {critical_conf} of those {need_action} "
                f"share a co-packer production line. You cannot run them all at once: "
                f"scheduling one pushes the others back. The table is sorted by "
                f"urgency. Negative days mean the deadline has passed.",
                style={"fontFamily": FONT_SANS, "fontSize": "15px",
                       "lineHeight": "1.6", "color": TEXT_SEC},
            ),
        ])

        # Scenario chip
        if promo_lift_pct > 0 or new_doors > 0 or lead_time_slip > 0:
            parts = []
            if promo_lift_pct > 0:
                parts.append(f"+{int(promo_lift_pct*100)}% promo lift")
            if new_doors > 0:
                parts.append(f"{new_doors:,} new doors")
            if lead_time_slip > 0:
                parts.append(f"+{lead_time_slip}wk lead-time slip")
            chip_text = f"Scenario: {', '.join(parts)}"
        else:
            chip_text = "Scenario: Baseline"

        return lead_text, row_data, kpi_row, chip_text

    @app.callback(
        Output("sop-download-xlsx", "data"),
        Input("sop-export-xlsx-btn", "n_clicks"),
        State("scenario-params", "data"),
        prevent_initial_call=True,
    )
    def download_xlsx(n_clicks, scenario_data):
        from app.data import export_sop_excel, get_sop_summary
        scenario = scenario_data or {}
        sop = get_sop_summary(
            promo_lift_pct=float(scenario.get("promo_lift_pct", 0.0)),
            new_doors=int(scenario.get("new_doors", 0)),
            lead_time_slip_weeks=int(scenario.get("lead_time_slip_weeks", 0)),
        )
        if sop.empty:
            return no_update
        xlsx_bytes = export_sop_excel(sop, scenario_params=scenario)
        return dcc.send_bytes(xlsx_bytes, "production_decision_brief.xlsx")

    @app.callback(
        Output("sop-download-pdf", "data"),
        Input("sop-export-pdf-btn", "n_clicks"),
        State("scenario-params", "data"),
        prevent_initial_call=True,
    )
    def download_pdf(n_clicks, scenario_data):
        from app.data import export_sop_pdf, get_sop_summary
        scenario = scenario_data or {}
        sop = get_sop_summary(
            promo_lift_pct=float(scenario.get("promo_lift_pct", 0.0)),
            new_doors=int(scenario.get("new_doors", 0)),
            lead_time_slip_weeks=int(scenario.get("lead_time_slip_weeks", 0)),
        )
        if sop.empty:
            return no_update
        try:
            pdf_bytes = export_sop_pdf(sop, scenario_params=scenario)
            return dcc.send_bytes(pdf_bytes, "production_decision_brief.pdf")
        except ImportError:
            # WeasyPrint not available in this environment (Windows dev, not Fly.io)
            logger.warning("PDF export unavailable: WeasyPrint native libs not installed")
            return no_update

    @app.callback(
        Output("sop-detail-panel", "children"),
        Input("sop-grid", "selectedRows"),
        State("scenario-params", "data"),
    )
    def update_detail_panel(selected_rows, scenario_data):
        if not selected_rows:
            return html.Div()
        row = selected_rows[0]
        scenario = scenario_data or {}
        return _build_detail_panel(row, scenario)


def _build_detail_panel(row: dict, scenario: dict) -> html.Div:
    """Inventory runway chart for a selected SKU row.

    Uses the active scenario params so the runway chart matches the table.
    """
    from app.data import get_forecast, get_sku_inventory, get_production_schedule

    sku = row.get("sku", "")
    product_name = row.get("product_name", sku)

    forecast = get_forecast(
        promo_lift_pct=float(scenario.get("promo_lift_pct", 0.0)),
        new_doors=int(scenario.get("new_doors", 0)),
    )
    inventory = get_sku_inventory()
    schedule = get_production_schedule()

    if forecast.empty:
        return empty_state(f"No forecast data for {sku}.")

    sku_fcst = forecast[
        (forecast["sku"] == sku) & forecast["is_projected"]
    ].sort_values("week_ending")

    if sku_fcst.empty:
        return empty_state(f"No projected weeks for {sku}.")

    # Starting inventory
    start_inv = 0.0
    if not inventory.empty and sku in inventory["sku"].values:
        start_inv = float(inventory.loc[inventory["sku"] == sku, "on_hand_units"].iloc[0])

    # Build running inventory trace
    weeks = pd.to_datetime(sku_fcst["week_ending"]).tolist()
    demands = sku_fcst["forecast_units"].tolist()
    sched_map = {}
    if not schedule.empty:
        sku_sched = schedule[schedule["sku"] == sku]
        for _, r in sku_sched.iterrows():
            wk = pd.Timestamp(r["scheduled_week"])
            sched_map[wk] = sched_map.get(wk, 0) + float(r["quantity_units"])

    running_inv = []
    current = start_inv
    for wk, demand in zip(weeks, demands):
        current += sched_map.get(wk, 0)
        current -= demand
        current = max(0.0, current)   # clamp the running total, not just the display value
        running_inv.append(current)

    fig = go.Figure()
    fig.add_trace(go.Bar(
        x=weeks, y=running_inv,
        name="Projected Inventory",
        marker_color=TEAL,
    ))
    fig.add_trace(go.Scatter(
        x=weeks, y=demands,
        name="Weekly Forecast Demand",
        mode="lines+markers",
        line=dict(color=TOKYO_ROSE, width=2),
        marker=dict(size=5),
    ))

    # Add stockout vline if present
    stockout = row.get("stockout_date")
    if stockout and str(stockout) not in ("None", "nan", ""):
        try:
            add_vline_at_date(fig, pd.Timestamp(stockout), "Stockout",
                              color=TOKYO_ROSE, dash="solid")
        except Exception:
            pass

    deadline = row.get("decision_deadline")
    if deadline and str(deadline) not in ("None", "nan", ""):
        try:
            add_vline_at_date(fig, pd.Timestamp(deadline), "Decision Deadline",
                              color=SG_ORANGE, dash="dash")
        except Exception:
            pass

    layout_cfg = base_chart_layout(height=280, y_title="Units", show_legend=True)
    fig.update_layout(**layout_cfg)

    doom_text = (
        f"If this SKU's inventory follows the OOS-corrected forecast, "
        f"stockout occurs {row.get('stockout_week_label', '—')} and "
        f"the decision deadline {'was ' + row.get('deadline_label', '—') if row.get('deadline_flag') == 'PAST_DUE' else 'is ' + row.get('deadline_label', '—')}. "
        f"The corrected forecast raised the demand estimate above the observed "
        f"velocity — accounting for periods when zero sales masked true demand."
    )

    return html.Div([
        html.H3(product_name, style={"fontFamily": FONT_SERIF, "fontWeight": "700",
                                     "fontSize": "18px", "marginBottom": "8px"}),
        dcc.Graph(figure=fig, config={"displayModeBar": False}),
        html.P(doom_text, style={
            "fontSize": "14px", "color": TEXT_SEC,
            "borderLeft": f"3px solid {GREY_LIGHT}", "paddingLeft": "12px",
            "marginTop": "12px",
        }),
    ], style={"padding": "16px", "backgroundColor": "#ffffff",
              "border": f"1px solid {GREY_LIGHT}", "borderRadius": "2px",
              "marginTop": "8px"})


def _format_date(d) -> str:
    try:
        ts = pd.Timestamp(d)
        return ts.strftime("%b ") + str(ts.day) + ts.strftime(" '%y")
    except Exception:
        return str(d)[:10] if d else "—"


def _btn_style() -> dict:
    return {
        "backgroundColor": CHICAGO,
        "color": "#ffffff",
        "fontFamily": FONT_SANS,
        "fontWeight": "600",
        "fontSize": "13px",
        "border": "none",
        "borderRadius": "2px",
        "padding": "8px 16px",
        "cursor": "pointer",
    }
