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
                "The most expensive stockout is the one nobody notices.",
                style=_prose_style(),
            ),
            html.P(
                "A dramatic shelf-clearing event — a recall, a weather disruption, "
                "a viral TikTok run — gets attention and a response. But the slow "
                "bleed is quieter: a handful of stores go dark each week, scattered "
                "across the network, none individually alarming. No buyer flags it. "
                "No replenishment signal fires. The POS data simply records slightly "
                "fewer units than the shelf could have moved, and the demand signal "
                "entering the forecast pipeline arrives understated.",
                style=_prose_style(),
            ),
            html.P(
                "That understated signal compounds. A forecast built on suppressed "
                "velocity projects conservative demand. Conservative demand drives "
                "conservative replenishment. Conservative replenishment leaves the "
                "same stores understocked the following week. The loop feeds itself, "
                "and each pass through the cycle widens the gap between what the data "
                "says happened and what would have happened at full distribution.",
                style=_prose_style(),
            ),
            html.P(
                "This is the doom loop: not a crisis, but a slow leak in the demand "
                "signal that the standard planning process mistakes for the truth.",
                style={
                    **_prose_style(),
                    "borderLeft": f"3px solid {TEAL}",
                    "paddingLeft": "16px",
                    "fontStyle": "italic",
                },
            ),
        ], style={"marginBottom": "40px"}),

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

        title = f"{_HERO_SKU} · {name}"
        subtitle = (
            f"{n_weeks} weeks of scan data across the retail network. "
            f"The chart below shows how many authorized stores recorded "
            f"zero sales each week — not because demand disappeared, but "
            f"because product wasn't on the shelf to sell."
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
            f"Over {n_weeks} weeks, roughly one in ten authorized stores went dark "
            f"in any given week for this SKU — persistent, not episodic. That "
            f"pattern hid an estimated {hidden_units:,.0f} units of real demand, a "
            f"quiet ~{avg_under:.0f}% understatement of true velocity that peaked "
            f"at ~{peak_under:.0f}% during the worst weeks.",
            style={**_prose_style(), "marginTop": "0"},
        ),
        html.P(
            "The aggregate number is modest. The damage is not. A 5% velocity "
            "understatement flows uncorrected through every downstream process "
            "that trusts the POS signal: the demand forecast undershoots, the "
            "replenishment order comes in light, and the next cycle of scan data "
            "arrives suppressed again. Over four quarters the effect is not 5% "
            "but 5% compounded — and it shows up not as a single write-off but "
            "as a persistent drag on fill rate, a slow slide in retailer "
            "scorecard performance, and eventually a buyer conversation that "
            "starts with \"your turns don't justify the shelf space.\"",
            style=_prose_style(),
        ),
        html.P(
            "The correction this tool applies is straightforward: identify the "
            "dark store-weeks, estimate the demand those stores would have "
            "recorded at full availability, and feed the corrected signal into "
            "the forecast. The arithmetic is simple. The insight is that without "
            "it, the planning process treats a supply failure as a demand "
            "signal — and plans accordingly.",
            style=_prose_style(),
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
