"""Capacity overlay and decision deadline module.

Public API:
    compute_stockout_date(forecast_df, inventory_df, schedule_df) -> DataFrame
    compute_decision_deadline(sop_df, sku_config_df) -> DataFrame
    detect_shared_line_conflicts(sop_df, sku_config_df) -> DataFrame

All three functions are unit-agnostic — the data layer (U6 get_sop_summary)
is responsible for converting between units and cases before calling here.

The full S&OP summary flow in U6:
  1. compute_stockout_date(forecast, inventory, schedule)
  2. compute_decision_deadline(sop, sku_config)
  3. detect_shared_line_conflicts(sop, sku_config)

Shared-line conflict definition: two or more SKUs on the same production line
have a non-None decision_deadline within the same 28-day (4-week) window.
"""

from __future__ import annotations

import logging
from datetime import timedelta

import pandas as pd

logger = logging.getLogger(__name__)

_CONFLICT_WINDOW_DAYS = 28
_CRITICAL_DAYS = 14
_WARNING_DAYS  = 28


def compute_stockout_date(
    forecast_df: pd.DataFrame,
    inventory_df: pd.DataFrame,
    schedule_df: pd.DataFrame,
) -> pd.DataFrame:
    """Compute the week each SKU first runs out of inventory.

    Args:
        forecast_df:   columns sku, week_ending, forecast_units, is_projected
        inventory_df:  columns sku, on_hand_units
        schedule_df:   columns sku, scheduled_week, quantity_units, status, line_id

    Returns a DataFrame with columns:
        sku, current_inventory, weekly_forecast_mean, stockout_date
    where stockout_date is None if inventory never hits 0 in the forecast window.
    """
    try:
        forecast_df = forecast_df.copy()
        forecast_df["week_ending"] = pd.to_datetime(forecast_df["week_ending"])

        projected = forecast_df[forecast_df["is_projected"]].copy()
        skus = projected["sku"].unique()

        # Index inputs
        inv_map = (
            inventory_df.set_index("sku")["on_hand_units"].to_dict()
            if not inventory_df.empty else {}
        )

        sched_map: dict[str, pd.DataFrame] = {}
        if not schedule_df.empty:
            sched_df = schedule_df.copy()
            sched_df["scheduled_week"] = pd.to_datetime(sched_df["scheduled_week"])
            for sku, grp in sched_df.groupby("sku"):
                sched_map[sku] = grp

        rows = []
        for sku in skus:
            sku_forecast = (
                projected[projected["sku"] == sku]
                .sort_values("week_ending")
                .copy()
            )
            inventory = float(inv_map.get(sku, 0))
            weekly_mean = sku_forecast["forecast_units"].mean()
            sku_sched = sched_map.get(sku, pd.DataFrame())

            stockout_date = None
            running = inventory
            for _, row in sku_forecast.iterrows():
                week = row["week_ending"]
                demand = float(row["forecast_units"])
                # Add any production arriving this week
                if not sku_sched.empty:
                    arriving = sku_sched[sku_sched["scheduled_week"] == week][
                        "quantity_units"
                    ].sum()
                    running += float(arriving)
                running -= demand
                if running < 0 and stockout_date is None:
                    stockout_date = week

            rows.append({
                "sku": sku,
                "current_inventory": inventory,
                "weekly_forecast_mean": round(weekly_mean, 2),
                "stockout_date": stockout_date,
            })

        return pd.DataFrame(rows)
    except Exception:
        logger.exception("compute_stockout_date failed")
        return pd.DataFrame(columns=["sku", "current_inventory",
                                      "weekly_forecast_mean", "stockout_date"])


def compute_decision_deadline(
    sop_df: pd.DataFrame,
    sku_config_df: pd.DataFrame,
    as_of_date: pd.Timestamp | None = None,
) -> pd.DataFrame:
    """Add decision_deadline, days_until_deadline, and deadline_flag columns.

    decision_deadline = stockout_date - lead_time_weeks (in calendar days).
    deadline_flag:
        "PAST_DUE"  — decision_deadline < today
        "CRITICAL"  — 0 ≤ days_until_deadline < 14
        "WARNING"   — 14 ≤ days_until_deadline < 28
        "OK"        — days_until_deadline ≥ 28 or no stockout
    """
    try:
        today = (as_of_date or pd.Timestamp.today()).normalize()
        sop = sop_df.copy()
        config_map = (
            sku_config_df.set_index("sku")[["lead_time_weeks"]].to_dict("index")
            if not sku_config_df.empty else {}
        )

        deadlines, days_list, flags = [], [], []
        for _, row in sop.iterrows():
            sku = row["sku"]
            stockout = row.get("stockout_date")
            lead_weeks = config_map.get(sku, {}).get("lead_time_weeks", 0)

            if stockout is None or pd.isna(stockout):
                deadlines.append(None)
                days_list.append(None)
                flags.append("OK")
                continue

            deadline = pd.Timestamp(stockout) - pd.Timedelta(weeks=lead_weeks)
            days = (deadline - today).days
            deadlines.append(deadline)
            days_list.append(days)

            if days < 0:
                flags.append("PAST_DUE")
            elif days < _CRITICAL_DAYS:
                flags.append("CRITICAL")
            elif days < _WARNING_DAYS:
                flags.append("WARNING")
            else:
                flags.append("OK")

        sop["decision_deadline"] = deadlines
        sop["days_until_deadline"] = days_list
        sop["deadline_flag"] = flags
        return sop
    except Exception:
        logger.exception("compute_decision_deadline failed")
        sop = sop_df.copy()
        sop["decision_deadline"] = None
        sop["days_until_deadline"] = None
        sop["deadline_flag"] = "OK"
        return sop


def detect_shared_line_conflicts(
    sop_df: pd.DataFrame,
    sku_config_df: pd.DataFrame,
) -> pd.DataFrame:
    """Flag SKUs with decision deadlines within 28 days of another SKU on the same line.

    Only SKUs with a non-None decision_deadline are considered.
    Adds columns: shared_line_conflict (bool), conflict_line_id (str),
    conflict_skus (list[str]).
    """
    try:
        sop = sop_df.copy()
        sop["shared_line_conflict"] = False
        sop["conflict_line_id"] = None
        sop["conflict_skus"] = [[] for _ in range(len(sop))]

        line_map = (
            sku_config_df.set_index("sku")["line_id"].to_dict()
            if not sku_config_df.empty else {}
        )
        sop["_line_id"] = sop["sku"].map(line_map)

        # Only SKUs with a real (non-None) decision_deadline
        has_deadline = sop[
            sop["decision_deadline"].notna()
        ].copy()

        if has_deadline.empty:
            return sop.drop(columns=["_line_id"])

        has_deadline["_deadline_ts"] = pd.to_datetime(has_deadline["decision_deadline"])

        for line_id, line_grp in has_deadline.groupby("_line_id"):
            if len(line_grp) < 2:
                continue
            # Check all pairs on this line
            for i, (idx_a, row_a) in enumerate(line_grp.iterrows()):
                for idx_b, row_b in line_grp.iloc[i + 1:].iterrows():
                    diff = abs((row_a["_deadline_ts"] - row_b["_deadline_ts"]).days)
                    if diff <= _CONFLICT_WINDOW_DAYS:
                        # Mark both SKUs as conflicted
                        for idx, other_sku in [(idx_a, row_b["sku"]),
                                               (idx_b, row_a["sku"])]:
                            pos = sop.index.get_loc(idx)
                            sop.at[idx, "shared_line_conflict"] = True
                            sop.at[idx, "conflict_line_id"] = line_id
                            existing = sop.at[idx, "conflict_skus"] or []
                            if other_sku not in existing:
                                sop.at[idx, "conflict_skus"] = existing + [other_sku]

        return sop.drop(columns=["_line_id"])
    except Exception:
        logger.exception("detect_shared_line_conflicts failed")
        sop = sop_df.copy()
        sop["shared_line_conflict"] = False
        sop["conflict_line_id"] = None
        sop["conflict_skus"] = [[] for _ in range(len(sop))]
        return sop
