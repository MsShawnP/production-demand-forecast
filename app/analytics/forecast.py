"""Rolling forecast module.

Public API:
    build_rolling_forecast(true_demand_df, forecast_from_week, n_weeks=12,
                           promo_lift_pct=0.0, new_retailer_doors=0,
                           new_doors_velocity_factor=None)
        -> DataFrame(sku, week_ending, forecast_units, is_projected, forecast_method)

Algorithm:
  1. Aggregate true_demand across stores to weekly SKU totals
     (physical stores only — aggregate channels excluded).
  2. Extract trailing 52 weeks ending at forecast_from_week.
  3. Apply STL(period=52, robust=True) for seasonal decomposition.
  4. Project trend forward: last trend value + mean trend delta (trailing 4 wks).
  5. Add seasonal component for the corresponding week-of-year.
  6. Clip to >= 0.
  7. Apply scenario parameters (promo lift, new doors).

Fallbacks:
  - Fewer than 52 weeks of history → 12-week rolling mean, no seasonal adj.
  - All-zero true_demand → forecast_units=0, forecast_method="insufficient_data".

Input DataFrame columns: sku, store_id, week_ending, true_demand
"""

from __future__ import annotations

import logging

import numpy as np
import pandas as pd

logger = logging.getLogger(__name__)

_AGGREGATE_STORES = frozenset({"UNFI-AGG", "KEHE-AGG", "DTC-AGG"})
_MIN_WEEKS_FOR_STL = 52
_ROLLING_MEAN_WINDOW = 12


def build_rolling_forecast(
    true_demand_df: pd.DataFrame,
    forecast_from_week: str,
    n_weeks: int = 12,
    promo_lift_pct: float = 0.0,
    new_retailer_doors: int = 0,
    new_doors_velocity_factor: float | None = None,
) -> pd.DataFrame:
    """Build a 12-week rolling forward demand forecast per SKU.

    Returns a DataFrame with columns:
        sku, week_ending, forecast_units, is_projected, forecast_method
    """
    try:
        cutoff = pd.Timestamp(forecast_from_week)

        # Aggregate to weekly SKU totals (exclude aggregate channels)
        weekly = _aggregate_to_sku_weekly(true_demand_df, cutoff)

        # Derive per-door velocity for new_retailer_doors scenario
        if new_retailer_doors > 0 and new_doors_velocity_factor is None:
            new_doors_velocity_factor = _median_per_door_velocity(
                true_demand_df, cutoff
            )

        parts: list[pd.DataFrame] = []
        for sku, sku_series in weekly.groupby("sku", sort=False):
            sku_series = sku_series.sort_values("week_ending").copy()
            projected = _forecast_one_sku(sku, sku_series, cutoff, n_weeks)
            # Scenario: promo lift
            if promo_lift_pct > 0 and "insufficient_data" not in projected["forecast_method"].values:
                projected.loc[projected["is_projected"], "forecast_units"] *= (1 + promo_lift_pct)
            # Scenario: new doors
            if new_retailer_doors > 0 and new_doors_velocity_factor is not None:
                door_contribution = new_retailer_doors * float(new_doors_velocity_factor)
                projected.loc[projected["is_projected"], "forecast_units"] += door_contribution
            # Clip to >= 0
            projected["forecast_units"] = projected["forecast_units"].clip(lower=0)
            parts.append(projected)

        if not parts:
            return pd.DataFrame(columns=["sku", "week_ending", "forecast_units",
                                          "is_projected", "forecast_method"])
        return pd.concat(parts, ignore_index=True)

    except Exception:
        logger.exception("build_rolling_forecast failed — returning empty DataFrame")
        return pd.DataFrame(
            columns=["sku", "week_ending", "forecast_units", "is_projected", "forecast_method"]
        )


# ---------------------------------------------------------------------------
# Private helpers
# ---------------------------------------------------------------------------

def _aggregate_to_sku_weekly(
    df: pd.DataFrame, cutoff: pd.Timestamp
) -> pd.DataFrame:
    """Sum true_demand across physical stores (not aggregate channels) by (sku, week_ending)."""
    physical = df[~df["store_id"].isin(_AGGREGATE_STORES)].copy()
    physical["week_ending"] = pd.to_datetime(physical["week_ending"])
    agg = (
        physical[physical["week_ending"] <= cutoff]
        .groupby(["sku", "week_ending"], sort=False)["true_demand"]
        .sum()
        .reset_index()
    )
    return agg


def _median_per_door_velocity(df: pd.DataFrame, cutoff: pd.Timestamp) -> float:
    """Median per-store weekly true_demand (physical stores, trailing 12 weeks)."""
    physical = df[~df["store_id"].isin(_AGGREGATE_STORES)].copy()
    physical["week_ending"] = pd.to_datetime(physical["week_ending"])
    recent = physical[
        (physical["week_ending"] <= cutoff)
        & (physical["week_ending"] > cutoff - pd.Timedelta(weeks=12))
    ]
    if recent.empty:
        return 1.0
    per_store = recent.groupby(["sku", "store_id"])["true_demand"].mean()
    return float(per_store.median()) if not per_store.empty else 1.0


def _forecast_one_sku(
    sku: str,
    sku_series: pd.DataFrame,
    cutoff: pd.Timestamp,
    n_weeks: int,
) -> pd.DataFrame:
    """Build the projection for a single SKU."""
    historical = sku_series[sku_series["week_ending"] <= cutoff].copy()
    series = historical["true_demand"].values.astype(float)

    # All-zero demand → insufficient data
    if series.sum() == 0:
        return _zero_forecast(sku, cutoff, n_weeks, method="insufficient_data")

    # Choose method based on history length
    if len(series) >= _MIN_WEEKS_FOR_STL:
        projected_vals, method = _stl_forecast(series, n_weeks)
    else:
        projected_vals, method = _rolling_mean_forecast(series, n_weeks)

    # Build the forward DataFrame
    future_weeks = [cutoff + pd.Timedelta(weeks=i + 1) for i in range(n_weeks)]
    proj_df = pd.DataFrame({
        "sku": sku,
        "week_ending": future_weeks,
        "forecast_units": projected_vals,
        "is_projected": True,
        "forecast_method": method,
    })

    # Include historical fitted values for chart display (optional)
    hist_df = pd.DataFrame({
        "sku": sku,
        "week_ending": historical["week_ending"].values,
        "forecast_units": series,
        "is_projected": False,
        "forecast_method": method,
    })

    return pd.concat([hist_df, proj_df], ignore_index=True)


def _stl_forecast(series: np.ndarray, n_weeks: int) -> tuple[np.ndarray, str]:
    """Project using STL decomposition (period=52, robust=True)."""
    try:
        from statsmodels.tsa.seasonal import STL
        stl = STL(series, period=52, robust=True).fit()

        # Trend projection: last value + mean delta of trailing 4 weeks
        trend = stl.trend
        delta = np.diff(trend[-4:]).mean() if len(trend) >= 5 else 0.0
        last_trend = trend[-1]
        projected_trend = last_trend + delta * np.arange(1, n_weeks + 1)

        # Seasonal component: map each future week to its corresponding
        # position in the last full seasonal cycle.
        seasonal = stl.seasonal
        period = 52
        projected_seasonal = np.array([
            seasonal[-(period - (i % period))]
            for i in range(n_weeks)
        ])

        projected = projected_trend + projected_seasonal
        return np.clip(projected, 0, None), "stl"
    except Exception:
        logger.warning("STL failed, falling back to rolling mean")
        return _rolling_mean_forecast(series, n_weeks)


def _rolling_mean_forecast(series: np.ndarray, n_weeks: int) -> tuple[np.ndarray, str]:
    """Fall back to the mean of the trailing window."""
    window = min(_ROLLING_MEAN_WINDOW, len(series))
    mean_val = float(np.mean(series[-window:]))
    return np.full(n_weeks, max(0.0, mean_val)), "rolling_mean_fallback"


def _zero_forecast(
    sku: str, cutoff: pd.Timestamp, n_weeks: int, method: str
) -> pd.DataFrame:
    future_weeks = [cutoff + pd.Timedelta(weeks=i + 1) for i in range(n_weeks)]
    return pd.DataFrame({
        "sku": sku,
        "week_ending": future_weeks,
        "forecast_units": 0.0,
        "is_projected": True,
        "forecast_method": method,
    })
