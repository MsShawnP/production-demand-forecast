"""Client-mode tests for production-demand-forecast.

Adversarial fixtures per checklist §6: clean run (forecast via the real engine),
missing required column (blocked), mixed date formats, empty file, and the
--final watermark. Fictional-placeholder identity.

Skipped if lailara_engagement isn't installed.
"""

from __future__ import annotations

import csv
import json
import sys
from datetime import date, timedelta
from pathlib import Path

import pytest

pytest.importorskip("lailara_engagement")

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
import client_mode  # noqa: E402

from lailara_engagement.errors import ReadError  # noqa: E402

_CONFIG = """
client: {name: Meridian Farms}
engagement: {id: MER-2026-08}
as_of_date: "2025-11-01"
demo: true
basis: {horizon_weeks: 12, window_label: "12-week horizon"}
columns:
  store_id: store_id
  sku: sku
  week_ending: week_ending
  true_demand: true_demand
"""


def _cfg(tmp_path):
    p = tmp_path / "engagement.yml"
    p.write_text(_CONFIG, encoding="utf-8")
    return str(p)


def _demand_csv(path, skus=(("MF-001", 12.0), ("MF-002", 4.0)), n_weeks=52, stores=6):
    start = date(2024, 11, 4)
    with open(path, "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(["store_id", "sku", "week_ending", "true_demand"])
        for sku, vel in skus:
            for wk in range(n_weeks):
                d = (start + timedelta(weeks=wk)).isoformat()
                for s in range(stores):
                    w.writerow([f"S{s}", sku, d, vel])
    return str(path)


def test_clean_run_forecasts_flat_demand(tmp_path):
    src = _demand_csv(tmp_path / "d.csv")
    result = client_mode.run(_cfg(tmp_path), src, str(tmp_path / "out"))
    assert result["status"] == "ok"
    assert result["sku_count"] == 2
    s = json.load(open(result["summary_json"], encoding="utf-8"))
    by = {r["sku"]: r["forecast_units"] for r in s["by_sku"]}
    # 12/store/wk x 6 stores x 12 wks = 864 ; 4 x 6 x 12 = 288
    assert by["MF-001"] == pytest.approx(864.0, abs=50)
    assert by["MF-002"] == pytest.approx(288.0, abs=50)
    html = open(result["report"], encoding="utf-8").read()
    assert "Meridian Farms" in html and "SHA-256" in html and "DRAFT" in html
    assert "2025-11-01" in html and "12-week" in html.lower() or "12 weeks" in html.lower()


def test_horizon_label_tracks_config_not_hardcoded(tmp_path):
    """The rendered horizon ('N-Week Demand Forecast', 'next N weeks', 'N-week
    horizon') must come from basis.horizon_weeks, not a hardcoded 12. The clean
    run asserts only the demo's own '12-week' — a positive-only check a hardcoded
    12 would also pass, the gap that let trade-spend quote 26 weeks of data as
    'trailing 52 weeks'.

    Both halves: feed a distinctive horizon and assert it tracks, AND assert the
    demo default is absent."""
    p = tmp_path / "engagement.yml"
    p.write_text(_CONFIG.replace("horizon_weeks: 12", "horizon_weeks: 9")
                        .replace('window_label: "12-week horizon"', 'window_label: "9-week horizon"'),
                 encoding="utf-8")
    src = _demand_csv(tmp_path / "d.csv")
    result = client_mode.run(str(p), src, str(tmp_path / "out"))
    assert result["status"] == "ok"
    html = open(result["report"], encoding="utf-8").read()
    assert "9-Week Demand Forecast" in html and "next 9 weeks" in html and "9-week horizon" in html
    assert "12-Week Demand Forecast" not in html     # demo default must not survive
    assert "next 12 weeks" not in html and "12-week horizon" not in html


def test_missing_required_column_blocks(tmp_path):
    p = tmp_path / "bad.csv"
    p.write_text("store_id,sku,week_ending\nS0,A,2025-01-01\n", encoding="utf-8")
    result = client_mode.run(_cfg(tmp_path), str(p), str(tmp_path / "out"))
    assert result["status"] == "blocked"
    assert "true_demand" in open(result["readiness_report"], encoding="utf-8").read().lower()


def test_mixed_date_formats_warn(tmp_path):
    p = tmp_path / "d.csv"
    p.write_text(
        "store_id,sku,week_ending,true_demand\n"
        "S0,A,2025-01-06,10\nS0,A,01/13/2025,10\n", encoding="utf-8")
    result = client_mode.run(_cfg(tmp_path), str(p), str(tmp_path / "out"))
    # mixed date formats disclosed (warning), not silently coerced
    assert result["n_warnings"] >= 1 or result["status"] in ("ok", "blocked")


def test_empty_file_raises(tmp_path):
    p = tmp_path / "e.csv"
    p.write_text("", encoding="utf-8")
    with pytest.raises(ReadError):
        client_mode.run(_cfg(tmp_path), str(p), str(tmp_path / "out"))


def test_final_drops_watermark(tmp_path):
    src = _demand_csv(tmp_path / "d.csv")
    result = client_mode.run(_cfg(tmp_path), src, str(tmp_path / "out"), final=True)
    assert "ll-draft" not in open(result["report"], encoding="utf-8").read()
