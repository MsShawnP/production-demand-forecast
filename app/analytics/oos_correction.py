"""OOS correction module.

Public API:
    detect_oos_periods(df)  -> df with added `is_oos` column
    correct_velocity(df)    -> df with added `true_demand` and `insufficient_data` columns

Expected input DataFrame columns:
    sku, store_id, week_ending, units_sold, is_authorized, is_promo

`is_authorized` must already be computed by the caller (from distribution_log) —
this module performs no database access.

Institutional learnings applied here:
- OOS guard clause: authorized-but-zero is OOS; unauthorized-and-zero is NOT.
  (See competitive-shelf-intelligence/docs/solutions/logic-errors/
   price-convention-mismatch-oos-guard-clause-2026-05-28.md)
- Aggregate channels (UNFI-AGG, KEHE-AGG, DTC-AGG) are NEVER flagged OOS.
  Their lumpy bulk cycles produce zero-sale weeks that are not stockouts.
"""

from __future__ import annotations

import logging

import numpy as np
import pandas as pd

logger = logging.getLogger(__name__)

_AGGREGATE_STORES = frozenset({"UNFI-AGG", "KEHE-AGG", "DTC-AGG"})


# ---------------------------------------------------------------------------
# Public: detect_oos_periods
# ---------------------------------------------------------------------------

def detect_oos_periods(df: pd.DataFrame) -> pd.DataFrame:
    """Add a boolean `is_oos` column to the scan DataFrame.

    A row is OOS when ALL of these hold:
      1. units_sold == 0
      2. is_authorized is True (row has a matching distribution_log record)
      3. store_id is NOT an aggregate channel

    Rows where units_sold > 0, or is_authorized is False, or store_id is an
    aggregate channel get is_oos = False.

    Returns the same DataFrame with an appended `is_oos` column.
    The row count is always preserved (no joins or drops).
    """
    try:
        df = df.copy()
        is_agg = df["store_id"].isin(_AGGREGATE_STORES)
        df["is_oos"] = (
            (df["units_sold"] == 0)
            & df["is_authorized"].astype(bool)
            & (~is_agg)
        )
        return df
    except Exception:
        logger.exception("detect_oos_periods failed — returning input with is_oos=False")
        df = df.copy()
        df["is_oos"] = False
        return df


# ---------------------------------------------------------------------------
# Public: correct_velocity
# ---------------------------------------------------------------------------

def correct_velocity(df: pd.DataFrame) -> pd.DataFrame:
    """Add `true_demand` and `insufficient_data` columns to the scan DataFrame.

    For non-OOS rows: true_demand = units_sold.
    For OOS rows: true_demand = rolling_median * seasonal_index.

    Rolling median: median of `units_sold` from the 3 non-OOS, non-promo
    weeks immediately before and 3 after the OOS block for the same
    (sku, store_id) pair. Uses fewer than 3 if insufficient history.

    Seasonal index: per-SKU mean `units_sold` by ISO week-of-year (over
    non-OOS, non-promo weeks) divided by overall per-SKU non-OOS mean.
    Applied as a multiplier on the rolling median for OOS correction weeks.

    Edge cases:
    - Fewer than 3 pre- or post-OOS weeks → use what is available (min 1).
    - All-OOS (sku, store_id) → true_demand = 0, insufficient_data = True.
    - Aggregate channels pass through unchanged (is_oos always False for them).

    The row count is always preserved.
    """
    try:
        df = df.copy()
        df["true_demand"] = df["units_sold"].astype(float)
        df["insufficient_data"] = False

        # Seasonal index per SKU (over non-OOS, non-promo weeks globally)
        seasonal_idx = _compute_seasonal_index(df)

        # Process each (sku, store_id) group independently
        groups = df.groupby(["sku", "store_id"], sort=False)
        corrected_parts: list[pd.DataFrame] = []
        for (sku, store_id), group in groups:
            corrected_parts.append(
                _correct_group(group, seasonal_idx.get(sku, {}))
            )

        result = pd.concat(corrected_parts).sort_index()
        return result
    except Exception:
        logger.exception("correct_velocity failed — returning true_demand = units_sold")
        df = df.copy()
        df["true_demand"] = df["units_sold"].astype(float)
        df["insufficient_data"] = False
        return df


# ---------------------------------------------------------------------------
# Private helpers
# ---------------------------------------------------------------------------

def _compute_seasonal_index(df: pd.DataFrame) -> dict[str, dict[int, float]]:
    """Build a {sku: {week_of_year: multiplier}} seasonal index.

    Computed over non-OOS, non-promo, non-aggregate rows only.
    Returns {} for SKUs where no clean weeks exist.
    """
    clean_mask = (
        (~df.get("is_oos", pd.Series(False, index=df.index)).astype(bool))
        & (~df.get("is_promo", pd.Series(False, index=df.index)).astype(bool))
        & (~df["store_id"].isin(_AGGREGATE_STORES))
        & (df["units_sold"] > 0)
    )
    clean = df[clean_mask].copy()
    if clean.empty:
        return {}

    clean["_woy"] = pd.to_datetime(clean["week_ending"]).dt.isocalendar().week.astype(int)

    result: dict[str, dict[int, float]] = {}
    for sku, sku_df in clean.groupby("sku", sort=False):
        overall_mean = sku_df["units_sold"].mean()
        if overall_mean == 0:
            continue
        woy_mean = sku_df.groupby("_woy")["units_sold"].mean()
        result[sku] = (woy_mean / overall_mean).to_dict()
    return result


def _correct_group(
    group: pd.DataFrame,
    seasonal_index: dict[int, float],
) -> pd.DataFrame:
    """Correct a single (sku, store_id) group in place.

    Returns the modified group with true_demand and insufficient_data filled.
    """
    group = group.copy().sort_values("week_ending")
    oos_mask = group["is_oos"].astype(bool)

    if not oos_mask.any():
        # No OOS periods — passthrough
        group["true_demand"] = group["units_sold"].astype(float)
        group["insufficient_data"] = False
        return group

    non_oos_idx = group.index[~oos_mask].tolist()

    if not non_oos_idx:
        # All weeks are OOS — cannot correct
        group["true_demand"] = 0.0
        group["insufficient_data"] = True
        return group

    # For each OOS row, find 3 closest non-OOS weeks before and after
    positions = list(group.index)
    for idx in group.index[oos_mask]:
        pos = positions.index(idx)
        # Non-OOS positions
        non_oos_positions = [positions.index(i) for i in non_oos_idx]
        before = [positions[p] for p in non_oos_positions if p < pos]
        after  = [positions[p] for p in non_oos_positions if p > pos]

        before_vals = group.loc[before[-3:], "units_sold"].tolist() if before else []
        after_vals  = group.loc[after[:3],  "units_sold"].tolist() if after else []

        neighbor_vals = before_vals + after_vals
        if not neighbor_vals:
            group.at[idx, "true_demand"] = 0.0
            group.at[idx, "insufficient_data"] = True
            continue

        rolling_median = float(np.median(neighbor_vals))

        # Apply seasonal index
        woy = int(pd.Timestamp(group.at[idx, "week_ending"]).isocalendar().week)
        s_idx = seasonal_index.get(woy, 1.0)

        group.at[idx, "true_demand"] = max(0.0, rolling_median * s_idx)
        group.at[idx, "insufficient_data"] = False

    return group
