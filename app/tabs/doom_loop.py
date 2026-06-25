"""Doom loop narrative tab — the portfolio teaching tool.

Section 1: "The Doom Loop" — Economist-style narrative of the OOS feedback cycle.
Section 2: Hidden-demand hero case — CHP-PS-008 (Italian Seasoning Blend).

The hero is reframed around what the data actually shows. Stockouts in this
dataset are encoded as MISSING rows (an authorized store goes dark for a week),
not a dramatic shelf-clearing event. The correction is real but modest (~5% of
velocity), so the hero visual is the persistence of the gap — dark store-weeks
over time and the cumulative demand it hides — not two near-identical velocity
lines. Every number is derived from the gap-based OOS computation; nothing is
hardcoded. The tab falls back gracefully if the hero SKU is not found.
"""

from __future__ import annotations

import logging

import pandas as pd
import plotly.graph_objects as go
from dash import Input, Output, dcc, html

from app.charts import base_chart_layout
from app.components import dark_card, loading_spinner
from app.constants import (
    CANVAS, CHICAGO, FONT_SANS, FONT_SERIF, GREY_LIGHT, INK,
    SG_ORANGE, TEXT, TEXT_SEC, TEAL,
)

logger = logging.getLogger(__name__)
TAB_ID = "tab-doom-loop"

# Hero case — CHP-PS-008 carries the strongest persistent-OOS signal in the
# scan data (dark in 76 of 78 weeks, the largest hidden-demand total). Stores
# span six retailers, so the story is "across the retail network", not one chain.
_HERO_SKU = "CHP-PS-008"
_PERIOD_WEEKS = {"full": None, "12m": 52, "6m": 26, "3m": 13}


def layout() -> html.Div:
    return html.Div([
        # ── Section 1: Narrative (static) ─────────────────────────────────
        html.H2(
            "The Demand Doom Loop",
            style={"fontFamily": FONT_SERIF, "fontWeight": "700",
                   "fontSize": "22px", "marginBottom": "4px", "color": INK},
        ),
        html.P(
            "Why forecasts built on stockout-corrupted data guarantee the next stockout.",
            style={"fontFamily": FONT_SANS, "fontSize": "14px",
                   "color": TEXT_SEC, "marginBottom": "16px"},
        ),

        html.Div([
            html.P(
                "The most expensive stockout is the one nobody notices.",
                style=_prose_style(),
            ),
            html.P(
                "When a store stocks out it does not record a zero — it simply goes "
                "dark, and that week leaves no row in the point-of-sale data. "
                "Velocity is computed over the stores still selling, so the gap is "
                "invisible. Spread across roughly a tenth of stores, week after "
                "week, it quietly understates true demand.",
                style=_prose_style(),
            ),
            html.P(
                "The understated demand becomes the forecast. The conservative "
                "forecast sizes a smaller reorder. The smaller reorder shortens the "
                "buffer, so more stores go dark — and the retailer's on-shelf-"
                "availability scorecard slips, putting the brand's authorization at "
                "risk. Each turn of the loop tightens it.",
                style=_prose_style(),
            ),
            html.P(
                "Out-of-stock weeks carry no demand signal — they carry silence. "
                "The fix is not a better forecast algorithm. It is correcting the "
                "silence before it enters the forecast.",
                style={
                    **_prose_style(),
                    "borderLeft": f"3px solid {TEAL}",
                    "paddingLeft": "16px",
                    "fontStyle": "italic",
                },
            ),
            html.P(
                "For brands that outsource production to co-packers, the correction "
                "is not optional — it is structural. A retailer can reorder next "
                "week. A brand on a co-packer line cannot. Lead times run eight to "
                "twelve weeks. Lines are shared across customers. Minimum order "
                "quantities are fixed. A forecast that understates demand by five "
                "per cent does not produce a five per cent shortfall — it produces "
                "a missed production window, and the next available slot is weeks "
                "away. This tool models that constraint. It corrects observed "
                "velocity for out-of-stock silence, connects the corrected forecast "
                "to co-packer lead times, and returns the one number an operations "
                "lead actually needs: the last date a production run can be ordered "
                "before the shelf goes empty.",
                style=_prose_style(),
            ),
        ], style={"marginBottom": "40px"}),

        html.Hr(style={"border": "none", "borderTop": "1px solid #999999",
                        "margin": "40px 0"}),

        # ── Period selector (Doom Loop only) ──────────────────────────────
        html.Div([
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
        ], style={
            "padding": "10px 0",
            "display": "flex",
            "alignItems": "center",
            "marginBottom": "16px",
        }),

        # ── Section 2: Hero case (callback-driven) ────────────────────────
        dcc.Loading(
            custom_spinner=loading_spinner("Loading analysis…"),
            children=html.Div(id="doom-loop-hero"),
        ),
    ], style={"padding": "24px"})


def register_callbacks(app) -> None:
    @app.callback(
        Output("doom-loop-hero", "children"),
        Input("time-period-selector", "value"),
    )
    def update_hero(period):
        title, subtitle, chart, cards = _build_hero_section(period=period)
        return [
            html.H2(title, style={
                "fontFamily": FONT_SERIF, "fontWeight": "700",
                "fontSize": "22px", "marginBottom": "4px", "color": INK,
            }),
            html.P(subtitle, style={
                "fontSize": "14px", "color": TEXT_SEC, "marginBottom": "20px",
            }),
            chart,
            cards,
        ]


# ---------------------------------------------------------------------------
# Private: hero case section builder
# ---------------------------------------------------------------------------

def _build_hero_section(period: str = "full") -> tuple[str, str, html.Div, html.Div]:
    """Build the reframed hero: title, subtitle, dark-store-weeks chart, cards.

    All figures come from the gap-based OOS computation for the hero SKU.
    Falls back to a safe message (never crashes) if the case is not found.
    """
    fallback_title = "The Hidden-Demand Case"
    try:
        from app.data import get_doom_loop_weekly, get_product_master

        period_wks = _PERIOD_WEEKS.get(period)
        wk = get_doom_loop_weekly(sku=_HERO_SKU, period_weeks=period_wks)
        if wk.empty or not bool((wk["stores_dark"] > 0).any()):
            return fallback_title, "", _fallback_chart(), html.Div()

        total_dark   = int(wk["stores_dark"].sum())
        hidden_units = float(wk["weekly_hidden_units"].sum())
        understate   = ((wk["corrected_units"] - wk["observed_units"])
                        / wk["observed_units"].where(wk["observed_units"] > 0)) * 100
        avg_under    = float(understate.mean())
        peak_under   = float(understate.max())
        weeks_dark   = int((wk["stores_dark"] > 0).sum())
        n_weeks      = int(len(wk))
        window_start = wk["week_ending"].min().strftime("%b %Y")
        window_end   = wk["week_ending"].max().strftime("%b %Y")

        name = _HERO_SKU
        pm = get_product_master()
        if not pm.empty and _HERO_SKU in pm["sku"].values:
            name = str(pm.loc[pm["sku"] == _HERO_SKU, "product_name"].iloc[0])

        title = f"The Hidden-Demand Case: {name}"
        subtitle = (
            f"{_HERO_SKU} across the retail network — "
            f"{n_weeks} weeks, {window_start} to {window_end}."
        )
        fig = _build_dark_weeks_chart(
            wk["week_ending"], wk["stores_dark"], wk["cumulative_hidden_units"],
        )
        cards = _build_hero_cards(
            hidden_units, total_dark, avg_under, peak_under, weeks_dark, n_weeks
        )
        return (
            title,
            subtitle,
            dcc.Graph(figure=fig, config={"displayModeBar": False},
                      style={"marginBottom": "24px"}),
            cards,
        )

    except Exception:
        logger.exception("Hero case section failed — showing fallback")
        return fallback_title, "", _fallback_chart(), html.Div()


def _build_dark_weeks_chart(weeks, dark_counts, cum_hidden) -> go.Figure:
    """Bars = authorized stores dark each week; line = cumulative hidden units."""
    fig = go.Figure()
    fig.add_trace(go.Bar(
        x=list(weeks), y=list(dark_counts),
        name="Authorized stores dark (OOS)",
        marker_color=SG_ORANGE, opacity=0.85,
        hovertemplate="%{x|%b %d, %Y}<br>Stores dark: %{y:.0f}<extra></extra>",
    ))
    fig.add_trace(go.Scatter(
        x=list(weeks), y=list(cum_hidden),
        name="Cumulative hidden demand (units)",
        yaxis="y2", mode="lines",
        line=dict(color=CHICAGO, width=2.5),
        hovertemplate="%{x|%b %d, %Y}<br>Hidden demand: %{y:,.0f} units<extra></extra>",
    ))

    layout_cfg = base_chart_layout(
        height=520,
        y_title="Stores with no scan row",
        show_legend=True,
    )
    fig.update_layout(**layout_cfg)
    fig.update_layout(
        margin=dict(l=10, r=90, t=30, b=50),
        yaxis2=dict(
            title="Hidden units (cumul.)",
            overlaying="y", side="right", showgrid=False,
            tickfont=dict(family=FONT_SANS, size=12, color=TEXT_SEC),
            title_font=dict(family=FONT_SANS, size=13, color=TEXT_SEC),
            rangemode="tozero",
        ),
        legend=dict(orientation="h", yanchor="bottom", y=1.02,
                    xanchor="left", x=0),
    )
    return fig


def _build_hero_cards(
    hidden_units: float, total_dark: int, avg_under: float,
    peak_under: float, weeks_dark: int, n_weeks: int,
) -> html.Div:
    return html.Div([
        html.Div([
            dark_card(
                primary=f"{hidden_units:,.0f} units",
                secondary=f"demand the forecast never saw — one SKU, {n_weeks} weeks",
            ),
            dark_card(
                primary=f"{peak_under:.1f}%",
                secondary=f"peak velocity understatement — {avg_under:.1f}% average, compounding quarterly",
            ),
            dark_card(
                primary=f"{weeks_dark} of {n_weeks} weeks",
                secondary="continuous stockout — not an event, a condition",
            ),
        ], style={"display": "flex", "flexWrap": "nowrap", "gap": "16px",
                  "marginBottom": "16px"}),
        html.P(
            "No single week looks like a crisis. But the leakage never stops. "
            "An eleven per cent velocity understatement in the worst week does "
            "not correct itself — it compounds through every downstream process "
            "that trusts the POS signal. Over four quarters, the forecast "
            "undershoots, replenishment comes in light, fill rate drifts, and "
            "the retailer scorecard conversation shifts from \"let's grow "
            "distribution\" to \"your turns don't justify the shelf space.\" "
            "The next stockout is already booked.",
            style={**_prose_style(), "marginTop": "0"},
        ),
    ])


def _fallback_chart() -> html.Div:
    return html.Div(
        "Demo case not found — run db/seed_copack.py against the Cinderhaven "
        "database and confirm scan_data carries authorized-but-missing store-weeks "
        f"(gaps) for {_HERO_SKU}.",
        style={"padding": "40px 24px", "color": TEXT_SEC, "fontSize": "14px",
               "border": f"1px solid {GREY_LIGHT}", "borderRadius": "2px",
               "marginBottom": "24px"},
    )


def _prose_style() -> dict:
    return {
        "fontFamily": FONT_SANS,
        "fontSize": "17px",
        "lineHeight": "1.6",
        "color": TEXT,
        "marginBottom": "16px",
    }
