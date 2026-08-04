"""Demo golden lock — production-demand-forecast.

This tool reads live Postgres, so there is no committed demo data file to
byte-lock. Instead the golden locks the things that keep the demo stable and
honest: the demo's as-of anchor, the elimination of wall-clock dates on the
analysis path, and the determinism of the forecast/capacity engines on a fixed
fixture.
"""

from __future__ import annotations

import numpy as np
import pandas as pd
import pytest

from app.analytics.capacity import compute_decision_deadline
from app.analytics.forecast import build_rolling_forecast


def test_demo_as_of_anchor():
    from app import data
    # The demo story is anchored to a fixed date (the stockout narrative), never
    # the wall clock. If this moves, the demo's deadline flags shift.
    assert data._DEMO_AS_OF_DATE == "2025-11-01"


def test_capacity_requires_explicit_as_of_date():
    # Wall-clock elimination: the deadline math must not silently fall back to
    # today (which would drift every day the app runs).
    sop = pd.DataFrame({"sku": ["A"], "stockout_date": [pd.Timestamp("2025-12-01")]})
    cfg = pd.DataFrame({"sku": ["A"], "lead_time_weeks": [4]})
    with pytest.raises(ValueError):
        compute_decision_deadline(sop, cfg)   # no as_of_date


def _flat_demand(sku="CHP-0001", n_weeks=52, velocity=10.0, stores=5):
    start = pd.Timestamp("2024-11-04")
    rows = []
    for w in range(n_weeks):
        week = (start + pd.Timedelta(weeks=w)).strftime("%Y-%m-%d")
        for s in range(stores):
            rows.append({"sku": sku, "store_id": f"S{s}", "week_ending": week,
                         "true_demand": velocity})
    return pd.DataFrame(rows)


def test_forecast_is_deterministic_and_tracks_flat_demand():
    df = _flat_demand(velocity=10.0, stores=5)
    fc1 = build_rolling_forecast(df, forecast_from_week="2025-11-01", n_weeks=12)
    fc2 = build_rolling_forecast(df, forecast_from_week="2025-11-01", n_weeks=12)
    # deterministic: identical inputs -> identical forecast
    pd.testing.assert_frame_equal(fc1.reset_index(drop=True), fc2.reset_index(drop=True))
    proj = fc1[fc1["is_projected"]]
    assert len(proj) == 12                                   # 12-week horizon
    # flat 10/store/week x 5 stores = ~50/week; forecast should track it, not invent
    assert np.allclose(proj["forecast_units"].to_numpy(), 50.0, atol=5.0)
