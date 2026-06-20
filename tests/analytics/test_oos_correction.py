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
# detect_oos_periods — gap-based detection
#
# Stockouts are encoded as MISSING rows: an authorized store has no scan row
# for the stocked-out week. Detection reconstructs each (sku, store) weekly
# calendar and inserts a synthetic OOS row for every authorized gap week.
# The global calendar is built from weeks present in the data, so fixtures use
# an "anchor" store/sku that reports every week (in production the 386-store
# panel guarantees this).
# ---------------------------------------------------------------------------

class TestDetectOosPeriods:

    def _gappy(self, present_idx: list[int], n: int = 5,
               sku: str = "CHP-0001", store: str = "RET-A-1",
               is_authorized: bool = True) -> pd.DataFrame:
        """One (sku, store) present only at `present_idx` of n weeks, plus an
        anchor store that covers every week so the calendar is complete."""
        weeks = _weeks("2024-01-06", n)
        rows = [
            {"sku": sku, "store_id": store, "week_ending": weeks[i],
             "units_sold": 5, "is_authorized": is_authorized}
            for i in present_idx
        ]
        rows += [  # anchor: a different store reporting every week
            {"sku": sku, "store_id": "RET-ANCHOR", "week_ending": w,
             "units_sold": 7, "is_authorized": True}
            for w in weeks
        ]
        return _make_scan_df(rows)

    def test_missing_authorized_week_inserted_as_oos(self):
        df = self._gappy(present_idx=[0, 1, 3])  # week 2 (and 4) missing
        out = detect_oos_periods(df)
        wk2 = pd.Timestamp(_weeks("2024-01-06", 5)[2])
        gap = out[(out["store_id"] == "RET-A-1") & (out["week_ending"] == wk2)]
        assert len(gap) == 1
        assert bool(gap["is_oos"].iloc[0])
        assert gap["units_sold"].iloc[0] == 0

    def test_present_rows_are_never_oos(self):
        df = self._gappy(present_idx=[0, 1, 2, 3, 4])  # fully present
        out = detect_oos_periods(df)
        assert not out["is_oos"].any()

    def test_nonzero_present_row_is_never_oos(self):
        df = _make_scan_df([{"units_sold": 10, "is_authorized": True}])
        out = detect_oos_periods(df)
        assert not out["is_oos"].iloc[0]

    def test_gap_for_unauthorized_store_not_flagged(self):
        # A store that is never authorized has no authorized window → no gaps.
        df = self._gappy(present_idx=[0, 1, 3], is_authorized=False)
        out = detect_oos_periods(df)
        a1 = out[out["store_id"] == "RET-A-1"]
        assert not a1["is_oos"].any()
        assert len(a1) == 3  # no rows inserted for the unauthorized store

    def test_aggregate_channel_gap_not_filled(self):
        weeks = _weeks("2024-01-06", 5)
        rows = [
            {"store_id": "UNFI-AGG", "week_ending": weeks[i],
             "units_sold": 100, "is_authorized": True}
            for i in (0, 1, 3)
        ]
        rows += [
            {"store_id": "RET-ANCHOR", "week_ending": w,
             "units_sold": 7, "is_authorized": True}
            for w in weeks
        ]
        out = detect_oos_periods(_make_scan_df(rows))
        assert not out[out["store_id"] == "UNFI-AGG"]["is_oos"].any()
        assert (out["store_id"] == "UNFI-AGG").sum() == 3  # no gap rows added

    def test_row_count_grows_by_gap_count(self):
        df = self._gappy(present_idx=[0, 1, 2, 4])  # one gap at week 3
        out = detect_oos_periods(df)
        assert len(out) == len(df) + 1
        assert int(out["is_oos"].sum()) == 1

    def test_gap_row_is_authorized_and_nonpromo(self):
        df = self._gappy(present_idx=[0, 2])  # gap at week 1
        out = detect_oos_periods(df)
        gap = out[out["is_oos"]]
        assert len(gap) == 1
        assert bool(gap["is_authorized"].iloc[0])
        assert not bool(gap["is_promo"].iloc[0])


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
