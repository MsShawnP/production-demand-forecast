"""Tests for app/analytics/capacity.py.

The capacity module joins the rolling forecast against co-packer constraints
and current production schedule to produce per-SKU stockout dates, decision
deadlines, and shared-line conflict flags.

Unit note: these tests use abstract "units" — the analytics layer is unit-
agnostic; the data layer (U6) converts between units and cases using
product_master.case_pack_qty before calling these functions.
"""

from __future__ import annotations

from datetime import date, timedelta

import pandas as pd
import pytest

from app.analytics.capacity import (
    compute_decision_deadline,
    compute_stockout_date,
    detect_shared_line_conflicts,
)

# Reference "today" for tests
TODAY = pd.Timestamp("2025-11-01")


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

def _forecast_df(skus_and_demands: dict[str, float], n_weeks: int = 12) -> pd.DataFrame:
    """Build a projected forecast DataFrame for multiple SKUs."""
    rows = []
    for sku, demand in skus_and_demands.items():
        for i in range(n_weeks):
            rows.append({
                "sku": sku,
                "week_ending": TODAY + pd.Timedelta(weeks=i + 1),
                "forecast_units": demand,
                "is_projected": True,
                "forecast_method": "stl",
            })
    return pd.DataFrame(rows)


def _inventory_df(sku_inventory: dict[str, int]) -> pd.DataFrame:
    return pd.DataFrame([
        {"sku": sku, "on_hand_units": units}
        for sku, units in sku_inventory.items()
    ])


def _schedule_df(
    runs: list[tuple[str, str, int]]  # (sku, line_id, week_offset, qty)
) -> pd.DataFrame:
    rows = []
    for item in runs:
        sku, line_id, week_offset, qty = item
        rows.append({
            "sku": sku,
            "line_id": line_id,
            "scheduled_week": TODAY + pd.Timedelta(weeks=week_offset),
            "quantity_units": qty,
            "status": "booked",
        })
    return pd.DataFrame(rows) if rows else pd.DataFrame(
        columns=["sku", "line_id", "scheduled_week", "quantity_units", "status"]
    )


def _sku_config_df(sku_configs: dict[str, dict]) -> pd.DataFrame:
    rows = []
    for sku, cfg in sku_configs.items():
        rows.append({
            "sku": sku,
            "line_id": cfg.get("line_id", "LINE-A"),
            "lead_time_weeks": cfg.get("lead_time_weeks", 10),
        })
    return pd.DataFrame(rows)


# ---------------------------------------------------------------------------
# compute_stockout_date
# ---------------------------------------------------------------------------

class TestComputeStockoutDate:

    def test_no_production_runs_stockout_when_inventory_depletes(self):
        # 200 units inventory, 50 units/week demand, no scheduled runs
        # → stockout in week 4 (after 4 weeks: 200 - 4*50 = 0)
        forecast = _forecast_df({"CHP-0001": 50.0})
        inventory = _inventory_df({"CHP-0001": 200})
        schedule = _schedule_df([])
        result = compute_stockout_date(forecast, inventory, schedule)
        row = result[result["sku"] == "CHP-0001"].iloc[0]
        assert row["stockout_date"] is not None or pd.notna(row["stockout_date"])

    def test_sufficient_inventory_no_stockout(self):
        # 1000 units inventory, 50 units/week demand, 12-week horizon
        # → no stockout (1000 >> 50*12 = 600)
        forecast = _forecast_df({"CHP-SAFE": 50.0})
        inventory = _inventory_df({"CHP-SAFE": 1000})
        schedule = _schedule_df([])
        result = compute_stockout_date(forecast, inventory, schedule)
        row = result[result["sku"] == "CHP-SAFE"].iloc[0]
        assert row["stockout_date"] is None or pd.isna(row["stockout_date"])

    def test_production_run_extends_runway(self):
        # 50 units, 50/week → stockout in week 1 without run
        # Add run of 500 units in week 1 → stockout pushed far out
        forecast = _forecast_df({"CHP-0001": 50.0})
        inventory = _inventory_df({"CHP-0001": 50})
        schedule = _schedule_df([("CHP-0001", "LINE-A", 1, 500)])
        result_no_run = compute_stockout_date(
            forecast, _inventory_df({"CHP-0001": 50}), _schedule_df([])
        )
        result_with_run = compute_stockout_date(forecast, inventory, schedule)
        r_no = result_no_run[result_no_run["sku"] == "CHP-0001"].iloc[0]
        r_with = result_with_run[result_with_run["sku"] == "CHP-0001"].iloc[0]
        # With run: either no stockout or stockout is later
        if r_no["stockout_date"] is not None and pd.notna(r_no["stockout_date"]):
            if r_with["stockout_date"] is not None and pd.notna(r_with["stockout_date"]):
                assert r_with["stockout_date"] >= r_no["stockout_date"]
            # or no stockout is fine too (run prevents it)

    def test_row_count_equals_sku_count(self):
        # Institutional learning: LEFT JOIN spine — no silent drops.
        forecast = _forecast_df({"CHP-0001": 50.0, "CHP-0002": 30.0, "CHP-0003": 20.0})
        inventory = _inventory_df({"CHP-0001": 100, "CHP-0002": 500, "CHP-0003": 500})
        schedule = _schedule_df([])
        result = compute_stockout_date(forecast, inventory, schedule)
        assert len(result) == 3

    def test_stockout_at_last_week_is_captured(self):
        # Exactly enough for 12 weeks: inventory = 12 * weekly_demand - 1
        # Stockout should be at week 12.
        weekly_demand = 10.0
        forecast = _forecast_df({"CHP-TIGHT": weekly_demand})
        inventory = _inventory_df({"CHP-TIGHT": int(12 * weekly_demand - 1)})
        schedule = _schedule_df([])
        result = compute_stockout_date(forecast, inventory, schedule)
        row = result[result["sku"] == "CHP-TIGHT"].iloc[0]
        # Should show a stockout (inventory < 0 sometime in the window)
        assert row["stockout_date"] is not None and pd.notna(row["stockout_date"])


# ---------------------------------------------------------------------------
# compute_decision_deadline
# ---------------------------------------------------------------------------

class TestComputeDecisionDeadline:

    def _base_sop_df(self, sku: str, stockout_offset_weeks: int | None) -> pd.DataFrame:
        """Build a minimal sop_df with one SKU."""
        stockout = (
            TODAY + pd.Timedelta(weeks=stockout_offset_weeks)
            if stockout_offset_weeks is not None
            else None
        )
        return pd.DataFrame([{
            "sku": sku,
            "stockout_date": stockout,
            "current_inventory": 100,
            "weekly_forecast_mean": 10.0,
        }])

    def test_decision_deadline_equals_stockout_minus_lead_time(self):
        # Stockout in 9 weeks, lead time 6 weeks → deadline in 3 weeks
        sop = self._base_sop_df("CHP-0001", stockout_offset_weeks=9)
        config = _sku_config_df({"CHP-0001": {"lead_time_weeks": 6, "line_id": "LINE-A"}})
        result = compute_decision_deadline(sop, config, as_of_date=TODAY)
        row = result[result["sku"] == "CHP-0001"].iloc[0]
        expected_deadline = TODAY + pd.Timedelta(weeks=9) - pd.Timedelta(weeks=6)
        assert pd.Timestamp(row["decision_deadline"]) == expected_deadline

    def test_no_stockout_gives_no_deadline(self):
        sop = self._base_sop_df("CHP-SAFE", stockout_offset_weeks=None)
        config = _sku_config_df({"CHP-SAFE": {"lead_time_weeks": 10, "line_id": "LINE-A"}})
        result = compute_decision_deadline(sop, config, as_of_date=TODAY)
        row = result[result["sku"] == "CHP-SAFE"].iloc[0]
        assert row["decision_deadline"] is None or pd.isna(row["decision_deadline"])
        assert row["deadline_flag"] == "OK"

    def test_critical_flag_when_deadline_less_than_14_days(self):
        # Covers AE1: days_until_deadline = 10 → CRITICAL
        # Stockout = 10 + lead_time days from today
        lead_time = 10  # weeks
        stockout_weeks = lead_time + 1  # deadline is 1 week (7 days) from now
        sop = self._base_sop_df("CHP-CRITICAL", stockout_offset_weeks=stockout_weeks)
        sop.loc[0, "stockout_date"] = TODAY + pd.Timedelta(weeks=stockout_weeks)
        config = _sku_config_df({"CHP-CRITICAL": {"lead_time_weeks": lead_time, "line_id": "LINE-A"}})
        result = compute_decision_deadline(sop, config, as_of_date=TODAY)
        row = result[result["sku"] == "CHP-CRITICAL"].iloc[0]
        assert row["deadline_flag"] == "CRITICAL"
        assert 0 < row["days_until_deadline"] < 14

    def test_past_due_flag_when_deadline_in_past(self):
        # Stockout in 5 weeks, lead time 8 weeks → deadline 3 weeks ago
        sop = self._base_sop_df("CHP-LATE", stockout_offset_weeks=5)
        config = _sku_config_df({"CHP-LATE": {"lead_time_weeks": 8, "line_id": "LINE-A"}})
        result = compute_decision_deadline(sop, config, as_of_date=TODAY)
        row = result[result["sku"] == "CHP-LATE"].iloc[0]
        assert row["deadline_flag"] == "PAST_DUE"
        assert row["days_until_deadline"] < 0

    def test_warning_flag_for_14_to_28_days(self):
        # Deadline in 21 days (3 weeks) → WARNING
        lead_time = 6  # weeks
        stockout_weeks = lead_time + 3  # deadline in 3 weeks = 21 days
        sop = self._base_sop_df("CHP-WARN", stockout_offset_weeks=stockout_weeks)
        config = _sku_config_df({"CHP-WARN": {"lead_time_weeks": lead_time, "line_id": "LINE-A"}})
        result = compute_decision_deadline(sop, config, as_of_date=TODAY)
        row = result[result["sku"] == "CHP-WARN"].iloc[0]
        assert row["deadline_flag"] == "WARNING"
        assert 14 <= row["days_until_deadline"] <= 28

    def test_ok_flag_for_more_than_28_days(self):
        sop = self._base_sop_df("CHP-OK", stockout_offset_weeks=15)
        config = _sku_config_df({"CHP-OK": {"lead_time_weeks": 6, "line_id": "LINE-A"}})
        result = compute_decision_deadline(sop, config, as_of_date=TODAY)
        row = result[result["sku"] == "CHP-OK"].iloc[0]
        assert row["deadline_flag"] == "OK"


# ---------------------------------------------------------------------------
# detect_shared_line_conflicts
# ---------------------------------------------------------------------------

class TestDetectSharedLineConflicts:

    def test_two_skus_on_same_line_within_4_weeks_are_conflicted(self):
        # Covers AE2: deadline A = week 2 (14 days), deadline B = week 3 (21 days)
        # |21 - 14| = 7 days < 28 days → both conflicted
        sop = pd.DataFrame([
            {"sku": "CHP-0001", "decision_deadline": TODAY + pd.Timedelta(days=14),
             "deadline_flag": "CRITICAL", "days_until_deadline": 14},
            {"sku": "CHP-0023", "decision_deadline": TODAY + pd.Timedelta(days=21),
             "deadline_flag": "CRITICAL", "days_until_deadline": 21},
        ])
        config = _sku_config_df({
            "CHP-0001": {"line_id": "LINE-A", "lead_time_weeks": 10},
            "CHP-0023": {"line_id": "LINE-A", "lead_time_weeks": 8},
        })
        result = detect_shared_line_conflicts(sop, config)
        assert result[result["sku"] == "CHP-0001"]["shared_line_conflict"].iloc[0]
        assert result[result["sku"] == "CHP-0023"]["shared_line_conflict"].iloc[0]

    def test_two_skus_on_different_lines_no_conflict(self):
        sop = pd.DataFrame([
            {"sku": "CHP-0001", "decision_deadline": TODAY + pd.Timedelta(days=14),
             "deadline_flag": "CRITICAL", "days_until_deadline": 14},
            {"sku": "CHP-0039", "decision_deadline": TODAY + pd.Timedelta(days=21),
             "deadline_flag": "CRITICAL", "days_until_deadline": 21},
        ])
        config = _sku_config_df({
            "CHP-0001": {"line_id": "LINE-A", "lead_time_weeks": 10},
            "CHP-0039": {"line_id": "LINE-B", "lead_time_weeks": 12},
        })
        result = detect_shared_line_conflicts(sop, config)
        assert not result[result["sku"] == "CHP-0001"]["shared_line_conflict"].iloc[0]
        assert not result[result["sku"] == "CHP-0039"]["shared_line_conflict"].iloc[0]

    def test_sku_without_deadline_does_not_cause_false_conflict(self):
        # One SKU has a deadline; other has None (no stockout) → no conflict.
        sop = pd.DataFrame([
            {"sku": "CHP-0001", "decision_deadline": TODAY + pd.Timedelta(days=14),
             "deadline_flag": "CRITICAL", "days_until_deadline": 14},
            {"sku": "CHP-0023", "decision_deadline": None,
             "deadline_flag": "OK", "days_until_deadline": None},
        ])
        config = _sku_config_df({
            "CHP-0001": {"line_id": "LINE-A", "lead_time_weeks": 10},
            "CHP-0023": {"line_id": "LINE-A", "lead_time_weeks": 8},
        })
        result = detect_shared_line_conflicts(sop, config)
        assert not result[result["sku"] == "CHP-0001"]["shared_line_conflict"].iloc[0]
        assert not result[result["sku"] == "CHP-0023"]["shared_line_conflict"].iloc[0]

    def test_two_skus_on_same_line_beyond_4_weeks_no_conflict(self):
        # Deadline A = week 1 (7 days), B = week 6 (42 days) → gap 35 days > 28 → no conflict
        sop = pd.DataFrame([
            {"sku": "CHP-0001", "decision_deadline": TODAY + pd.Timedelta(days=7),
             "deadline_flag": "CRITICAL", "days_until_deadline": 7},
            {"sku": "CHP-0023", "decision_deadline": TODAY + pd.Timedelta(days=42),
             "deadline_flag": "WARNING", "days_until_deadline": 42},
        ])
        config = _sku_config_df({
            "CHP-0001": {"line_id": "LINE-A", "lead_time_weeks": 10},
            "CHP-0023": {"line_id": "LINE-A", "lead_time_weeks": 8},
        })
        result = detect_shared_line_conflicts(sop, config)
        assert not result[result["sku"] == "CHP-0001"]["shared_line_conflict"].iloc[0]
        assert not result[result["sku"] == "CHP-0023"]["shared_line_conflict"].iloc[0]

    def test_conflict_populates_conflict_line_and_skus(self):
        sop = pd.DataFrame([
            {"sku": "CHP-0001", "decision_deadline": TODAY + pd.Timedelta(days=14),
             "deadline_flag": "CRITICAL", "days_until_deadline": 14},
            {"sku": "CHP-0023", "decision_deadline": TODAY + pd.Timedelta(days=21),
             "deadline_flag": "CRITICAL", "days_until_deadline": 21},
        ])
        config = _sku_config_df({
            "CHP-0001": {"line_id": "LINE-A", "lead_time_weeks": 10},
            "CHP-0023": {"line_id": "LINE-A", "lead_time_weeks": 8},
        })
        result = detect_shared_line_conflicts(sop, config)
        for sku in ["CHP-0001", "CHP-0023"]:
            row = result[result["sku"] == sku].iloc[0]
            assert row["conflict_line_id"] == "LINE-A"
            assert len(row["conflict_skus"]) > 0
