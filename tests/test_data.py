"""Tests for app/data.py.

These tests verify the caching layer glue, scenario parameter clamping, and
the sop_summary assembly pipeline. They use mock DataFrames rather than a
live Postgres connection — the analytics functions themselves are tested in
tests/analytics/.

Pattern: monkeypatch the raw query functions with fixture DataFrames, then
verify the higher-level functions produce correctly assembled results.
"""

from __future__ import annotations

import pandas as pd
import pytest


# ---------------------------------------------------------------------------
# Scenario parameter clamping
# ---------------------------------------------------------------------------

class TestScenarioClamping:

    def test_clamp_promo_lift_above_one(self):
        from app.data import _clamp_scenario
        clamped, _, _ = _clamp_scenario(1.5, 0, 0)
        assert clamped == 1.0

    def test_clamp_promo_lift_below_zero(self):
        from app.data import _clamp_scenario
        clamped, _, _ = _clamp_scenario(-0.1, 0, 0)
        assert clamped == 0.0

    def test_clamp_new_doors_above_5000(self):
        from app.data import _clamp_scenario
        _, doors, _ = _clamp_scenario(0.0, 9999, 0)
        assert doors == 5000

    def test_clamp_new_doors_below_zero(self):
        from app.data import _clamp_scenario
        _, doors, _ = _clamp_scenario(0.0, -10, 0)
        assert doors == 0

    def test_clamp_lead_time_slip_above_12(self):
        from app.data import _clamp_scenario
        _, _, slip = _clamp_scenario(0.0, 0, 20)
        assert slip == 12

    def test_valid_params_pass_through_unchanged(self):
        from app.data import _clamp_scenario
        lift, doors, slip = _clamp_scenario(0.3, 200, 4)
        assert (lift, doors, slip) == (0.3, 200, 4)


# ---------------------------------------------------------------------------
# get_sop_summary — pipeline assembly (fully mocked)
# ---------------------------------------------------------------------------

class TestGetSopSummaryPipeline:
    """Verify get_sop_summary assembles the pipeline correctly using mock inputs."""

    def _make_forecast(self, n_skus: int = 3, n_weeks: int = 12) -> pd.DataFrame:
        rows = []
        for i in range(n_skus):
            sku = f"CHP-{i:04d}"
            for w in range(n_weeks):
                rows.append({
                    "sku": sku,
                    "week_ending": pd.Timestamp("2025-11-08") + pd.Timedelta(weeks=w),
                    "forecast_units": 50.0,
                    "is_projected": True,
                    "forecast_method": "stl",
                })
        return pd.DataFrame(rows)

    def _make_inventory(self, n_skus: int = 3, high: bool = True) -> pd.DataFrame:
        units = 10000 if high else 50
        return pd.DataFrame([
            {"sku": f"CHP-{i:04d}", "on_hand_units": units}
            for i in range(n_skus)
        ])

    def _make_sku_config(self, n_skus: int = 3) -> pd.DataFrame:
        return pd.DataFrame([
            {
                "sku": f"CHP-{i:04d}",
                "line_id": "LINE-A",
                "lead_time_weeks": 6,
                "product_name": f"Product {i}",
                "product_line": "Artisan Sauces",
            }
            for i in range(n_skus)
        ])

    def test_sop_summary_assembles_from_analytics_functions(self, monkeypatch):
        """Verify the pipeline calls the analytics functions correctly."""
        from app import data as data_module

        monkeypatch.setattr(data_module, "_LIVE_COMPUTE", True)

        forecast = self._make_forecast(n_skus=3)
        inventory = self._make_inventory(n_skus=3, high=True)
        config = self._make_sku_config(n_skus=3)
        empty_schedule = pd.DataFrame(
            columns=["sku", "line_id", "scheduled_week", "quantity_units", "status"]
        )

        monkeypatch.setattr(data_module, "get_forecast", lambda **kw: forecast)
        monkeypatch.setattr(data_module, "get_sku_inventory", lambda: inventory)
        monkeypatch.setattr(data_module, "get_production_schedule", lambda: empty_schedule)
        monkeypatch.setattr(data_module, "get_sku_config", lambda: config)

        result = data_module.get_sop_summary.__wrapped__(0.0, 0, 0)
        assert len(result) == 3
        assert "stockout_date" in result.columns
        assert "deadline_flag" in result.columns
        assert "shared_line_conflict" in result.columns

    def test_sop_returns_ok_when_inventory_is_high(self, monkeypatch):
        from app import data as data_module

        monkeypatch.setattr(data_module, "_LIVE_COMPUTE", True)

        forecast = self._make_forecast(n_skus=2)
        inventory = self._make_inventory(n_skus=2, high=True)
        config = self._make_sku_config(n_skus=2)
        empty_schedule = pd.DataFrame(
            columns=["sku", "line_id", "scheduled_week", "quantity_units", "status"]
        )

        monkeypatch.setattr(data_module, "get_forecast", lambda **kw: forecast)
        monkeypatch.setattr(data_module, "get_sku_inventory", lambda: inventory)
        monkeypatch.setattr(data_module, "get_production_schedule", lambda: empty_schedule)
        monkeypatch.setattr(data_module, "get_sku_config", lambda: config)

        result = data_module.get_sop_summary.__wrapped__(0.0, 0, 0)
        assert (result["deadline_flag"] == "OK").all()

    def test_sop_returns_empty_when_forecast_empty(self, monkeypatch):
        from app import data as data_module

        monkeypatch.setattr(data_module, "_LIVE_COMPUTE", True)

        monkeypatch.setattr(data_module, "get_forecast", lambda **kw: pd.DataFrame())
        monkeypatch.setattr(data_module, "get_sku_inventory", lambda: pd.DataFrame())
        monkeypatch.setattr(data_module, "get_production_schedule", lambda: pd.DataFrame())
        monkeypatch.setattr(data_module, "get_sku_config", lambda: pd.DataFrame())

        result = data_module.get_sop_summary.__wrapped__(0.0, 0, 0)
        assert result.empty

    def test_lead_time_slip_increases_lead_time_in_pipeline(self, monkeypatch):
        """lead_time_slip_weeks should add to each SKU's lead_time_weeks."""
        from app import data as data_module
        from app.analytics.capacity import compute_decision_deadline

        monkeypatch.setattr(data_module, "_LIVE_COMPUTE", True)

        captured_configs = []

        def mock_deadline(sop, config, as_of_date=None):
            captured_configs.append(config.copy())
            # Return minimal valid output
            sop = sop.copy()
            sop["decision_deadline"] = None
            sop["days_until_deadline"] = None
            sop["deadline_flag"] = "OK"
            return sop

        forecast = self._make_forecast(n_skus=2)
        inventory = self._make_inventory(n_skus=2, high=True)
        config = self._make_sku_config(n_skus=2)
        empty_schedule = pd.DataFrame(
            columns=["sku", "line_id", "scheduled_week", "quantity_units", "status"]
        )

        monkeypatch.setattr(data_module, "get_forecast", lambda **kw: forecast)
        monkeypatch.setattr(data_module, "get_sku_inventory", lambda: inventory)
        monkeypatch.setattr(data_module, "get_production_schedule", lambda: empty_schedule)
        monkeypatch.setattr(data_module, "get_sku_config", lambda: config)
        monkeypatch.setattr(data_module, "compute_decision_deadline", mock_deadline)

        data_module.get_sop_summary.__wrapped__(0.0, 0, lead_time_slip_weeks=4)
        assert len(captured_configs) == 1
        # All SKUs should have lead_time_weeks = 6 + 4 = 10
        assert (captured_configs[0]["lead_time_weeks"] == 10).all()


# ---------------------------------------------------------------------------
# Snapshot mode — per-week seasonal forecast + scenario stockout recompute
# ---------------------------------------------------------------------------

class TestSnapshotScenario:
    """The two snapshot-mode fixes:

    1. The snapshot draws the persisted per-week STL series (seasonal shape),
       not a flat mean line — and falls back to a flat line only when the
       per-week table is absent.
    2. A scenario recomputes stockout on the lifted forecast, so a big enough
       promo/new-door lift can push a HEALTHY SKU (no baseline stockout) red.
    """

    _AS_OF = pd.Timestamp("2025-11-01")

    def _seasonal_weeks(self) -> pd.DataFrame:
        vals = [30, 32, 35, 38, 42, 45, 48, 45, 42, 38, 35, 30]
        return pd.DataFrame([
            {"sku": "CHP-HEALTHY",
             "week_ending": self._AS_OF + pd.Timedelta(weeks=i + 1),
             "forecast_units": float(v)}
            for i, v in enumerate(vals)
        ])

    def _summary(self) -> pd.DataFrame:
        df = pd.DataFrame([{
            "sku": "CHP-HEALTHY",
            "product_name": "Healthy Product",
            "product_line": "Artisan Sauces",
            "weekly_forecast_mean": 40.0,
            "current_inventory": 600.0,      # 12wk baseline demand (~460) < 600
            "stockout_date": pd.NaT,
            "decision_deadline": pd.NaT,
            "days_until_deadline": None,
            "deadline_flag": "OK",
            "lead_time_weeks": 8,
            "shared_line_conflict": False,
            "conflict_skus": [],
            "median_store_velocity": 2.0,
        }])
        df["stockout_date"] = pd.to_datetime(df["stockout_date"])
        df["decision_deadline"] = pd.to_datetime(df["decision_deadline"])
        return df

    def _config(self) -> pd.DataFrame:
        return pd.DataFrame([{
            "sku": "CHP-HEALTHY",
            "line_id": "LINE-A",
            "lead_time_weeks": 8,
            "product_name": "Healthy Product",
            "product_line": "Artisan Sauces",
        }])

    def _patch(self, monkeypatch):
        from app import data as data_module
        monkeypatch.setattr(data_module, "_LIVE_COMPUTE", False)
        monkeypatch.setattr(data_module, "_read_forecast_snapshot", lambda: self._summary())
        monkeypatch.setattr(data_module, "_read_forecast_week_snapshot",
                            lambda: self._seasonal_weeks())
        monkeypatch.setattr(data_module, "get_production_schedule", lambda: pd.DataFrame())
        monkeypatch.setattr(data_module, "get_sku_config", lambda: self._config())
        return data_module

    def test_snapshot_forecast_shows_seasonality(self, monkeypatch):
        data_module = self._patch(monkeypatch)
        fc = data_module.get_forecast.__wrapped__(0.0, 0, 0)
        sku_fc = fc[fc["sku"] == "CHP-HEALTHY"].sort_values("week_ending")
        assert len(sku_fc) == 12
        # Not a flat line — the STL seasonal shape is preserved.
        assert sku_fc["forecast_units"].std() > 0
        assert sku_fc["forecast_units"].nunique() > 1
        assert (sku_fc["forecast_method"] == "snapshot_stl").all()

    def test_flat_fallback_when_week_table_missing(self, monkeypatch):
        data_module = self._patch(monkeypatch)
        # Older snapshot: per-week table unavailable → flat line at the mean.
        monkeypatch.setattr(data_module, "_read_forecast_week_snapshot",
                            lambda: pd.DataFrame())
        fc = data_module.get_forecast.__wrapped__(0.0, 0, 0)
        sku_fc = fc[fc["sku"] == "CHP-HEALTHY"]
        assert len(sku_fc) == 12
        assert sku_fc["forecast_units"].nunique() == 1     # flat
        assert (sku_fc["forecast_method"] == "snapshot_flat").all()

    def test_baseline_healthy_sku_is_ok(self, monkeypatch):
        data_module = self._patch(monkeypatch)
        sop = data_module.get_sop_summary.__wrapped__(0.0, 0, 0)
        row = sop[sop["sku"] == "CHP-HEALTHY"].iloc[0]
        assert pd.isna(row["stockout_date"])
        assert row["deadline_flag"] == "OK"

    def test_scenario_turns_healthy_sku_red(self, monkeypatch):
        data_module = self._patch(monkeypatch)
        # Big promo + new doors lifts the forecast far above the runway.
        sop = data_module.get_sop_summary.__wrapped__(0.5, 200, 0)
        row = sop[sop["sku"] == "CHP-HEALTHY"].iloc[0]
        assert pd.notna(row["stockout_date"]), "healthy SKU should now stock out"
        assert row["deadline_flag"] in ("PAST_DUE", "CRITICAL", "WARNING"), \
            f"expected a red/urgent flag, got {row['deadline_flag']}"
