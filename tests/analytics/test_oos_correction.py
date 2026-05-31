"""Tests for app/analytics/oos_correction.py.

Written test-first per plan execution note: the authorized-but-zero vs.
unauthorized-and-zero guard condition must be locked in by these tests before
the correction step is built.

Input DataFrame columns consumed by this module:
    sku, store_id, week_ending, units_sold, is_authorized, is_promo
"""

from __future__ import annotations

import pandas as pd
import pytest

from app.analytics.oos_correction import correct_velocity, detect_oos_periods


# ---------------------------------------------------------------------------
# Fixtures and helpers
# ---------------------------------------------------------------------------

def _make_scan_df(rows: list[dict]) -> pd.DataFrame:
    """Build a minimal scan DataFrame from a list of row dicts."""
    defaults = {
        "sku": "CHP-TEST",
        "store_id": "WM-001",
        "week_ending": "2025-01-06",
        "units_sold": 5,
        "is_authorized": True,
        "is_promo": False,
    }
    records = [{**defaults, **r} for r in rows]
    df = pd.DataFrame(records)
    df["week_ending"] = pd.to_datetime(df["week_ending"])
    return df


def _weeks(start: str, n: int) -> list[str]:
    """Generate n consecutive Saturday-ending ISO week strings starting from start."""
    base = pd.Timestamp(start)
    return [(base + pd.Timedelta(weeks=i)).strftime("%Y-%m-%d") for i in range(n)]


# ---------------------------------------------------------------------------
# detect_oos_periods — detection logic (the subtle guard condition)
# ---------------------------------------------------------------------------

class TestDetectOosPeriods:

    def test_authorized_zero_units_is_flagged_oos(self):
        df = _make_scan_df([{"units_sold": 0, "is_authorized": True}])
        out = detect_oos_periods(df)
        assert out["is_oos"].iloc[0] is True or out["is_oos"].iloc[0] == True

    def test_unauthorized_zero_units_is_not_oos(self):
        # Zero units with no authorization record is a gap in distribution, not a stockout.
        df = _make_scan_df([{"units_sold": 0, "is_authorized": False}])
        out = detect_oos_periods(df)
        assert not out["is_oos"].iloc[0]

    def test_nonzero_units_is_never_oos(self):
        df = _make_scan_df([{"units_sold": 10, "is_authorized": True}])
        out = detect_oos_periods(df)
        assert not out["is_oos"].iloc[0]

    def test_aggregate_channel_store_is_never_oos(self):
        # UNFI-AGG, KEHE-AGG, DTC-AGG have lumpy bulk cycles, not stockout signals.
        for agg_id in ("UNFI-AGG", "KEHE-AGG", "DTC-AGG"):
            df = _make_scan_df([
                {"store_id": agg_id, "units_sold": 0, "is_authorized": True}
            ])
            out = detect_oos_periods(df)
            assert not out["is_oos"].iloc[0], f"{agg_id} should not be flagged OOS"

    def test_row_count_preserved(self):
        # Institutional learning: no silent row drops (inner-join anti-pattern).
        rows = [
            {"sku": "CHP-0001", "store_id": "WM-001", "units_sold": 0, "is_authorized": True},
            {"sku": "CHP-0001", "store_id": "WM-001", "units_sold": 5, "is_authorized": True},
            {"sku": "CHP-0002", "store_id": "WM-001", "units_sold": 0, "is_authorized": False},
        ]
        df = _make_scan_df(rows)
        out = detect_oos_periods(df)
        assert len(out) == len(df)

    def test_mixed_sku_store_pairs(self):
        rows = [
            {"sku": "CHP-0001", "store_id": "WM-001", "units_sold": 0, "is_authorized": True},
            {"sku": "CHP-0001", "store_id": "WM-002", "units_sold": 0, "is_authorized": False},
            {"sku": "CHP-0002", "store_id": "WM-001", "units_sold": 3, "is_authorized": True},
        ]
        df = _make_scan_df(rows)
        out = detect_oos_periods(df)
        row_by = out.set_index(["sku", "store_id"])["is_oos"]
        assert row_by[("CHP-0001", "WM-001")]      # authorized + zero → OOS
        assert not row_by[("CHP-0001", "WM-002")]  # unauthorized + zero → NOT OOS
        assert not row_by[("CHP-0002", "WM-001")]  # non-zero → NOT OOS


# ---------------------------------------------------------------------------
# correct_velocity — OOS correction logic
# ---------------------------------------------------------------------------

class TestCorrectVelocity:

    def _sku_history(self, units_pattern: list[int], oos_pattern: list[bool]) -> pd.DataFrame:
        """Build a single (sku, store) history with given unit/oos patterns."""
        n = len(units_pattern)
        weeks = _weeks("2024-01-06", n)
        rows = [
            {
                "sku": "CHP-0001",
                "store_id": "WM-001",
                "week_ending": w,
                "units_sold": u,
                "is_authorized": True,
                "is_promo": False,
                "is_oos": o,
            }
            for w, u, o in zip(weeks, units_pattern, oos_pattern)
        ]
        df = pd.DataFrame(rows)
        df["week_ending"] = pd.to_datetime(df["week_ending"])
        return df

    def test_non_oos_rows_are_unchanged(self):
        # Non-OOS weeks: true_demand == units_sold exactly.
        units = [5, 6, 4, 7, 5]
        oos   = [False] * 5
        df = self._sku_history(units, oos)
        out = correct_velocity(df)
        for i, row in out.iterrows():
            assert row["true_demand"] == pytest.approx(row["units_sold"]), \
                f"Row {i}: true_demand should equal units_sold for non-OOS week"

    def test_oos_weeks_get_positive_corrected_demand(self):
        # Classic 2-week OOS block in the middle: true_demand > 0 for those weeks.
        # Pattern: 5, 6, 0(OOS), 0(OOS), 5, 6
        units = [5, 6, 0, 0, 5, 6]
        oos   = [False, False, True, True, False, False]
        df = self._sku_history(units, oos)
        out = correct_velocity(df)
        oos_rows = out[out["is_oos"]]
        assert (oos_rows["true_demand"] > 0).all(), \
            "OOS weeks should receive positive corrected true_demand"

    def test_oos_corrected_demand_is_near_surrounding_median(self):
        # Surrounding velocity is 10 units/week → corrected should be ~10.
        units = [10, 10, 0, 0, 10, 10, 10]
        oos   = [False, False, True, True, False, False, False]
        df = self._sku_history(units, oos)
        out = correct_velocity(df)
        oos_rows = out[out["is_oos"]]
        for _, row in oos_rows.iterrows():
            # Allow for seasonal index scaling — should be within 50% of median
            assert 5 < row["true_demand"] < 20, \
                f"Corrected demand {row['true_demand']} is implausibly far from median 10"

    def test_oos_at_start_of_window_uses_post_oos_weeks(self):
        # OOS at the very beginning — no pre-OOS weeks available.
        # Should use post-OOS weeks only, no crash.
        units = [0, 0, 0, 8, 9, 10, 8]
        oos   = [True, True, True, False, False, False, False]
        df = self._sku_history(units, oos)
        out = correct_velocity(df)
        oos_rows = out[out["is_oos"]]
        assert (oos_rows["true_demand"] > 0).all(), \
            "OOS at start of window should still produce positive corrected demand"

    def test_oos_at_end_of_window_uses_pre_oos_weeks(self):
        # OOS at the very end — no post-OOS weeks available.
        units = [8, 9, 10, 9, 0, 0]
        oos   = [False, False, False, False, True, True]
        df = self._sku_history(units, oos)
        out = correct_velocity(df)
        oos_rows = out[out["is_oos"]]
        assert (oos_rows["true_demand"] > 0).all()

    def test_consecutive_oos_blocks_both_corrected(self):
        # Two separate OOS blocks with a non-OOS week between them.
        # Each block uses the non-OOS boundary on each side.
        units = [8, 0, 8, 0, 8]
        oos   = [False, True, False, True, False]
        df = self._sku_history(units, oos)
        out = correct_velocity(df)
        oos_rows = out[out["is_oos"]]
        assert len(oos_rows) == 2
        assert (oos_rows["true_demand"] > 0).all()

    def test_all_oos_returns_zero_with_flag(self):
        # If every week for a (sku, store) is OOS, we can't correct.
        # true_demand should be 0 and insufficient_data should be True.
        units = [0, 0, 0, 0]
        oos   = [True, True, True, True]
        df = self._sku_history(units, oos)
        out = correct_velocity(df)
        assert (out["true_demand"] == 0).all()
        assert "insufficient_data" in out.columns
        assert out["insufficient_data"].all()

    def test_aggregate_channel_oos_flag_false_demand_unchanged(self):
        # Aggregate channels are never OOS — their true_demand == units_sold.
        rows = [
            {
                "sku": "CHP-0001",
                "store_id": "UNFI-AGG",
                "week_ending": "2025-01-06",
                "units_sold": 150,
                "is_authorized": True,
                "is_promo": False,
                "is_oos": False,
            }
        ]
        df = pd.DataFrame(rows)
        df["week_ending"] = pd.to_datetime(df["week_ending"])
        out = correct_velocity(df)
        assert out["true_demand"].iloc[0] == pytest.approx(150)

    def test_row_count_preserved_after_correction(self):
        units = [5, 0, 0, 5, 5]
        oos   = [False, True, True, False, False]
        df = self._sku_history(units, oos)
        out = correct_velocity(df)
        assert len(out) == len(df)

    def test_oos_correction_raises_corrected_demand_above_suppressed(self):
        # The OOS-corrected demand should be HIGHER than the zero units_sold.
        # (This is the core value proposition of the module.)
        units = [10, 10, 10, 0, 0, 10, 10]
        oos   = [False, False, False, True, True, False, False]
        df = self._sku_history(units, oos)
        out = correct_velocity(df)
        oos_rows = out[out["is_oos"]]
        assert (oos_rows["true_demand"] > oos_rows["units_sold"]).all()
