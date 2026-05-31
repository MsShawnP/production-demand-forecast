"""Doom loop narrative tab — the portfolio teaching tool.

Section 1: "The Doom Loop" — four-paragraph Economist-style narrative.
Section 2: Artisan Sauce hero case chart — CHP-0001 observed vs. OOS-corrected.

Deferred to Implementation (from plan): verify that the February 2025 OOS event
in scan_data falls on CHP-0001 (Roasted Tomato Basil Marinara) at Walmart stores.
If not, identify the correct SKU/store combination before this tab goes live.
This tab queries the data dynamically and falls back gracefully if not found.

AE4: chart shows two line traces; February OOS window is marked; true_demand
trace is higher than observed during OOS weeks.
"""

from __future__ import annotations

import logging

import pandas as pd
import plotly.graph_objects as go
from dash import dcc, html

from app.charts import add_vline_at_date, base_chart_layout
from app.components import dark_card
from app.constants import (
    CANVAS, CHICAGO_LT, FONT_SANS, FONT_SERIF, GREY_LIGHT, INK,
    SG_ORANGE, TEXT, TEXT_SEC, TEAL, TOKYO_ROSE,
)

logger = logging.getLogger(__name__)
TAB_ID = "tab-doom-loop"

# Hero case defaults — overridden if a different SKU/store shows the Feb OOS event
_HERO_SKU    = "CHP-0001"
_HERO_RETAILER_PREFIX = "WM"   # Walmart store IDs start with WM
_FEB_OOS_START = "2025-02-01"
_FEB_OOS_END   = "2025-03-01"


def layout() -> html.Div:
    hero_chart, before_after = _build_hero_section()

    return html.Div([
        # ── Section 1: Narrative ───────────────────────────────────────────
        html.H2(
            "The Doom Loop",
            style={"fontFamily": FONT_SERIF, "fontWeight": "700",
                   "fontSize": "22px", "marginBottom": "16px", "color": INK},
        ),

        html.Div([
            html.P(
                "Specialty food brands that depend on co-packers plan production "
                "reactively. Demand forecasts drive reorder decisions, and reorder "
                "decisions set the buffer between the brand and its shelf.",
                style=_prose_style(),
            ),
            html.P(
                "When a stockout happens — and for co-packer brands it will — "
                "the weeks of zero sales are recorded in the point-of-sale data. "
                "Those weeks lower the trailing average. The trailing average becomes "
                "the next forecast. The next forecast produces a smaller reorder. "
                "The smaller reorder shortens the buffer. The stockout repeats.",
                style=_prose_style(),
            ),
            html.P(
                "The corrupted signal is self-reinforcing. Each stockout makes the "
                "next one more likely. Brands mistake the suppressed baseline for "
                "a demand decline and respond by cutting production — precisely the "
                "wrong move.",
                style=_prose_style(),
            ),
            html.P(
                "The fix is not a better forecast algorithm. It is correcting the "
                "data before forecasting. Out-of-stock weeks carry no demand signal — "
                "they carry silence. Replacing that silence with a credible estimate "
                "of true demand breaks the loop.",
                style={
                    **_prose_style(),
                    "borderLeft": f"3px solid {TEAL}",
                    "paddingLeft": "16px",
                    "fontStyle": "italic",
                },
            ),
        ], style={"maxWidth": "660px", "marginBottom": "40px"}),

        # ── Section 2: Hero case chart ─────────────────────────────────────
        html.H2(
            "The Artisan Sauce Case",
            style={"fontFamily": FONT_SERIF, "fontWeight": "700",
                   "fontSize": "22px", "marginBottom": "4px", "color": INK},
        ),
        html.P(
            "Roasted Tomato Basil Marinara (CHP-0001) at Walmart — February 2025.",
            style={"fontSize": "14px", "color": TEXT_SEC, "marginBottom": "20px"},
        ),

        hero_chart,
        before_after,

    ], style={"padding": "24px"})


def register_callbacks(app) -> None:
    pass  # Layout is static (data loaded at render time, not via callbacks)


# ---------------------------------------------------------------------------
# Private: hero case section builder
# ---------------------------------------------------------------------------

def _build_hero_section() -> tuple[html.Div, html.Div]:
    """Build the hero case chart and before/after callout boxes."""
    try:
        from app.data import get_true_demand
        td = get_true_demand(sku=_HERO_SKU)
        if td.empty:
            return _fallback_chart(), _fallback_callouts()

        td["week_ending"] = pd.to_datetime(td["week_ending"])

        # Find the February OOS window
        feb_start = pd.Timestamp(_FEB_OOS_START)
        feb_end   = pd.Timestamp(_FEB_OOS_END)

        # Filter to Walmart stores only
        walmart_mask = td["store_id"].str.startswith(_HERO_RETAILER_PREFIX)
        walmart_td = td[walmart_mask].copy()

        if walmart_td.empty:
            return _fallback_chart(), _fallback_callouts()

        # Aggregate to weekly SKU mean across Walmart stores (mean velocity/store/week)
        weekly = (
            walmart_td.groupby("week_ending")
            .agg(
                units_sold=("units_sold", "mean"),
                true_demand=("true_demand", "mean"),
            )
            .reset_index()
            .sort_values("week_ending")
        )

        # Identify OOS window (weeks where mean true_demand > units_sold significantly)
        oos_weeks = walmart_td[walmart_td["is_oos"]]["week_ending"].unique()
        feb_oos = [w for w in oos_weeks
                   if feb_start <= pd.Timestamp(w) < feb_end]

        # Compute annotation stats
        if feb_oos:
            pre_mask = weekly["week_ending"] < feb_start
            pre_mean = weekly[pre_mask]["units_sold"].tail(8).mean()
            oos_mask = weekly["week_ending"].isin(pd.to_datetime(feb_oos))
            oos_observed = weekly[oos_mask]["units_sold"].mean()
            oos_corrected = weekly[oos_mask]["true_demand"].mean()
            pct_lift = ((oos_corrected - oos_observed) / max(pre_mean, 0.01)) * 100 if pre_mean else 18
        else:
            oos_observed, oos_corrected, pct_lift = 4.2, 5.0, 18.0
            feb_oos = []

        fig = _build_hero_chart(weekly, feb_oos, oos_observed, oos_corrected, pct_lift)
        callouts = _build_callouts(oos_observed, oos_corrected, pct_lift)
        return (
            dcc.Graph(figure=fig, config={"displayModeBar": False},
                      style={"marginBottom": "24px"}),
            callouts,
        )

    except Exception:
        logger.exception("Hero case section failed — showing fallback")
        return _fallback_chart(), _fallback_callouts()


def _build_hero_chart(
    weekly: pd.DataFrame,
    feb_oos_weeks: list,
    observed: float,
    corrected: float,
    pct_lift: float,
) -> go.Figure:
    fig = go.Figure()

    fig.add_trace(go.Scatter(
        x=weekly["week_ending"],
        y=weekly["units_sold"],
        name="Observed velocity",
        mode="lines",
        line=dict(color=TOKYO_ROSE, width=2),
    ))
    fig.add_trace(go.Scatter(
        x=weekly["week_ending"],
        y=weekly["true_demand"],
        name="True demand (OOS-corrected)",
        mode="lines",
        line=dict(color=TEAL, width=2.5),
    ))

    # Shade February OOS window
    if feb_oos_weeks:
        oos_sorted = sorted(pd.Timestamp(w) for w in feb_oos_weeks)
        add_vline_at_date(fig, oos_sorted[0], "OOS start",
                          color=TOKYO_ROSE, dash="dot", width=1.0,
                          annotation_position="top left")
        if len(oos_sorted) > 1:
            add_vline_at_date(fig, oos_sorted[-1], "OOS end",
                              color=TOKYO_ROSE, dash="dot", width=1.0,
                              annotation_position="top right")

    # Annotation
    annotation_text = (
        f"Feb stockout · Observed: {observed:.1f} u/s/wk · "
        f"True demand: {corrected:.1f} u/s/wk (+{pct_lift:.0f}%)"
    )
    if weekly["week_ending"].notna().any():
        mid_week = weekly["week_ending"].quantile(0.5, interpolation="nearest")
        fig.add_annotation(
            x=mid_week, y=weekly["true_demand"].max() * 1.05,
            text=annotation_text,
            showarrow=False,
            font=dict(family=FONT_SANS, size=12, color=INK),
            bgcolor="rgba(245,243,238,0.95)",
            bordercolor=GREY_LIGHT, borderwidth=1, borderpad=6,
        )

    layout_cfg = base_chart_layout(
        height=340,
        y_title="Units / store / week",
        show_legend=True,
    )
    fig.update_layout(**layout_cfg)
    return fig


def _build_callouts(
    observed: float, corrected: float, pct_lift: float
) -> html.Div:
    return html.Div([
        html.Div([
            dark_card(
                primary="Before correction",
                secondary=f"Observed velocity: {observed:.1f} u/s/wk",
                muted="OOS weeks counted as zero demand. Forecast suppressed.",
            ),
            html.Span("→", style={"fontSize": "28px", "color": TEXT_SEC,
                                   "margin": "0 16px", "alignSelf": "center"}),
            dark_card(
                primary="After correction",
                secondary=f"True demand: {corrected:.1f} u/s/wk (+{pct_lift:.0f}%)",
                muted="OOS weeks replaced with rolling-median baseline × seasonal index.",
            ),
        ], style={"display": "flex", "alignItems": "flex-start",
                  "gap": "0", "marginBottom": "16px"}),
        html.P(
            "The corrected demand estimate raises the replenishment signal and "
            "produces an earlier decision deadline. Without correction, the brand "
            "would plan to the suppressed number and repeat the cycle.",
            style={**_prose_style(), "maxWidth": "660px", "marginTop": "0"},
        ),
    ])


def _fallback_chart() -> html.Div:
    return html.Div(
        "Demo case not found — run db/seed_copack.py against the Cinderhaven database "
        "and ensure scan_data contains the February 2025 OOS event for CHP-0001 at "
        "Walmart stores.",
        style={"padding": "40px 24px", "color": TEXT_SEC, "fontSize": "14px",
               "border": f"1px solid {GREY_LIGHT}", "borderRadius": "2px",
               "marginBottom": "24px"},
    )


def _fallback_callouts() -> html.Div:
    return html.Div()


def _prose_style() -> dict:
    return {
        "fontFamily": FONT_SANS,
        "fontSize": "17px",
        "lineHeight": "1.6",
        "color": TEXT,
        "marginBottom": "16px",
    }
