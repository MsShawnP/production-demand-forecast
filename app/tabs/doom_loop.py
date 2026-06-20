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
from dash import dcc, html

from app.charts import base_chart_layout
from app.components import dark_card
from app.constants import (
    CANVAS, CHICAGO, FONT_SANS, FONT_SERIF, GREY_LIGHT, INK,
    SG_ORANGE, TEXT, TEXT_SEC, TEAL, TOKYO_ROSE,
)

logger = logging.getLogger(__name__)
TAB_ID = "tab-doom-loop"

# Hero case — CHP-PS-008 carries the strongest persistent-OOS signal in the
# scan data (dark in 76 of 78 weeks, the largest hidden-demand total). Stores
# span six retailers, so the story is "across the retail network", not one chain.
_HERO_SKU = "CHP-PS-008"


def layout() -> html.Div:
    hero_title, hero_subtitle, hero_chart, hero_cards = _build_hero_section()

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

        # ── Section 2: Hero case ───────────────────────────────────────────
        html.H2(
            hero_title,
            style={"fontFamily": FONT_SERIF, "fontWeight": "700",
                   "fontSize": "22px", "marginBottom": "4px", "color": INK},
        ),
        html.P(
            hero_subtitle,
            style={"fontSize": "14px", "color": TEXT_SEC, "marginBottom": "20px"},
        ),

        hero_chart,
        hero_cards,

    ], style={"padding": "24px"})


def register_callbacks(app) -> None:
    pass  # Layout is static (data loaded at render time, not via callbacks)


# ---------------------------------------------------------------------------
# Private: hero case section builder
# ---------------------------------------------------------------------------

def _build_hero_section() -> tuple[str, str, html.Div, html.Div]:
    """Build the reframed hero: title, subtitle, dark-store-weeks chart, cards.

    All figures come from the gap-based OOS computation for the hero SKU.
    Falls back to a safe message (never crashes) if the case is not found.
    """
    fallback_title = "The Hidden-Demand Case"
    try:
        from app.data import get_product_master, get_true_demand

        td = get_true_demand(sku=_HERO_SKU)
        if td.empty or "is_oos" not in td.columns or not bool(td["is_oos"].any()):
            return fallback_title, "", _fallback_chart(), html.Div()

        td = td.copy()
        td["week_ending"] = pd.to_datetime(td["week_ending"])

        # Weekly aggregates: total observed vs corrected, count of dark stores
        wk = (
            td.groupby("week_ending")
            .agg(
                observed=("units_sold", "sum"),
                corrected=("true_demand", "sum"),
                dark=("is_oos", "sum"),
            )
            .sort_index()
        )
        weekly_hidden = (
            td[td["is_oos"]].groupby("week_ending")["true_demand"].sum()
            .reindex(wk.index, fill_value=0.0)
        )
        cum_hidden = weekly_hidden.cumsum()

        # Headline stats — all derived, none hardcoded
        total_dark   = int(td["is_oos"].sum())
        hidden_units = float(td.loc[td["is_oos"], "true_demand"].sum())
        understate   = ((wk["corrected"] - wk["observed"])
                        / wk["observed"].where(wk["observed"] > 0)) * 100
        avg_under    = float(understate.mean())
        peak_under   = float(understate.max())
        weeks_dark   = int((wk["dark"] > 0).sum())
        n_weeks      = int(len(wk))
        window_start = wk.index.min().strftime("%b %Y")
        window_end   = wk.index.max().strftime("%b %Y")

        # Product name from the DB (do not invent one)
        name = _HERO_SKU
        pm = get_product_master()
        if not pm.empty and _HERO_SKU in pm["sku"].values:
            name = str(pm.loc[pm["sku"] == _HERO_SKU, "product_name"].iloc[0])

        title = f"The Hidden-Demand Case: {name}"
        subtitle = (
            f"{_HERO_SKU} across the retail network — "
            f"{n_weeks} weeks, {window_start} to {window_end}."
        )
        fig = _build_dark_weeks_chart(wk.index, wk["dark"], cum_hidden)
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
    ))
    fig.add_trace(go.Scatter(
        x=list(weeks), y=list(cum_hidden),
        name="Cumulative hidden demand (units)",
        yaxis="y2", mode="lines",
        line=dict(color=CHICAGO, width=2.5),
    ))

    layout_cfg = base_chart_layout(
        height=360,
        y_title="Stores with no scan row",
        show_legend=True,
    )
    fig.update_layout(**layout_cfg)
    fig.update_layout(
        margin=dict(l=10, r=70, t=30, b=50),
        yaxis2=dict(
            title="Cumulative hidden units",
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
                secondary=f"hidden across {total_dark:,} dark store-weeks",
                muted="demand the raw POS signal never recorded",
            ),
            dark_card(
                primary=f"{avg_under:.1f}%",
                secondary=f"average velocity understatement (peak {peak_under:.1f}%)",
                muted="how much out-of-stocks suppress the forecast input",
            ),
            dark_card(
                primary=f"{weeks_dark} of {n_weeks} weeks",
                secondary="had at least one authorized store dark",
                muted="persistent leakage, not a single event",
            ),
        ], style={"display": "flex", "flexWrap": "wrap", "gap": "16px",
                  "marginBottom": "16px"}),
        html.P(
            f"No single week looks like a crisis — the worst undercounts velocity "
            f"by {peak_under:.1f}%. But the leakage never stops: stores go dark in "
            f"{weeks_dark} of {n_weeks} weeks, hiding {hidden_units:,.0f} units of "
            f"demand from the forecast. The brand plans to the suppressed number, "
            f"underorders, and the next stockout is already booked. Correcting the "
            f"out-of-stock weeks before forecasting is what breaks the cycle.",
            style={**_prose_style(), "maxWidth": "660px", "marginTop": "0"},
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
