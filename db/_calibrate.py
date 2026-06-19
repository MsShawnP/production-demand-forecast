"""Recalibrate SKU_INVENTORY for a differentiated S&OP demo.

Sizes each SKU's on-hand inventory so it stocks out at a target week (or
survives the 12-week horizon = "healthy"), verified against the real
OOS-corrected forecast and capacity analytics. Prints a seed-ready
SKU_INVENTORY block and the resulting flag distribution.

Usage (needs DATABASE_URL in env or .env, pointing at the Cinderhaven DB):
    PYTHONPATH=. python db/_calibrate.py

Re-run this whenever the demand data changes and paste the printed block
into seed_copack.py, then re-seed.
"""
from __future__ import annotations

import collections
import os
import pathlib

import pandas as pd
import psycopg2
from dotenv import load_dotenv

from app.analytics.capacity import (
    compute_decision_deadline,
    compute_stockout_date,
    detect_shared_line_conflicts,
)
from app.analytics.forecast import build_rolling_forecast
from app.analytics.oos_correction import correct_velocity, detect_oos_periods

load_dotenv(pathlib.Path(__file__).resolve().parent.parent / ".env")

AS_OF = "2025-11-01"
HISTORY_WEEKS = 78

# Target stockout week per SKU (None = survive the 12-week horizon = healthy).
# Combined with per-line lead times this drives the deadline-flag distribution.
TARGET = {
    "CHP-AS-001": 5, "CHP-AS-002": None, "CHP-AS-003": 11, "CHP-AS-004": 7, "CHP-AS-005": 12,
    "CHP-AS-006": 10, "CHP-AS-007": 8, "CHP-AS-008": None, "CHP-AS-009": 11, "CHP-AS-010": 6,
    "CHP-DG-001": None, "CHP-DG-002": 10, "CHP-DG-003": 9, "CHP-DG-004": 12, "CHP-DG-005": None,
    "CHP-DG-006": 11, "CHP-DG-007": 4, "CHP-DG-008": None, "CHP-DG-009": 10, "CHP-DG-010": 7,
    "CHP-PS-001": None, "CHP-PS-002": 10, "CHP-PS-003": 12, "CHP-PS-004": 6, "CHP-PS-005": None,
    "CHP-PS-006": 11, "CHP-PS-007": None, "CHP-PS-008": 12, "CHP-PS-009": 8, "CHP-PS-010": None,
    "CHP-SC-001": 8, "CHP-SC-002": 10, "CHP-SC-003": None, "CHP-SC-004": 11, "CHP-SC-005": 9,
    "CHP-SC-006": None, "CHP-SC-007": 10, "CHP-SC-008": 5, "CHP-SC-009": None, "CHP-SC-010": 11,
    "CHP-SB-001": None, "CHP-SB-002": 9, "CHP-SB-003": 10, "CHP-SB-004": 6, "CHP-SB-005": None,
    "CHP-SB-006": 8, "CHP-SB-007": 11, "CHP-SB-008": 7, "CHP-SB-009": None, "CHP-SB-010": 10,
}

_SCAN_SQL = """
    SELECT s.sku, s.store_id, s.week_ending, s.units_sold,
        CASE WHEN d.sku IS NOT NULL AND d.authorized_date <= s.week_ending
             AND (d.deauthorized_date IS NULL OR d.deauthorized_date > s.week_ending)
             THEN TRUE ELSE FALSE END AS is_authorized,
        CASE WHEN EXISTS (SELECT 1 FROM promotions p WHERE p.sku = s.sku
             AND s.week_ending BETWEEN p.start_week AND p.end_week)
             THEN TRUE ELSE FALSE END AS is_promo
    FROM scan_data s
    LEFT JOIN distribution_log d ON d.sku = s.sku AND d.store_id = s.store_id
    WHERE s.week_ending <= %(a)s AND s.week_ending > %(h)s
    ORDER BY s.sku, s.store_id, s.week_ending
"""


def main() -> None:
    url = os.environ["DATABASE_URL"]
    conn = psycopg2.connect(url, options="-c search_path=raw,public", connect_timeout=15)
    conn.autocommit = True
    hs = str((pd.Timestamp(AS_OF) - pd.Timedelta(weeks=HISTORY_WEEKS)).date())
    scan = pd.read_sql(_SCAN_SQL, conn, params={"a": AS_OF, "h": hs})
    cfg = pd.read_sql(
        "SELECT sku, line_id, lead_time_weeks, min_run_cases FROM sku_production_config", conn
    )
    meta = pd.read_sql(
        "SELECT sku, product_name, product_line, case_pack_qty FROM product_master", conn
    )
    conn.close()

    td = correct_velocity(detect_oos_periods(scan))
    last = str(pd.to_datetime(td["week_ending"]).max().date())
    fc = build_rolling_forecast(td, forecast_from_week=last)
    proj = fc[fc["is_projected"]].copy()
    proj["week_ending"] = pd.to_datetime(proj["week_ending"])
    cpq = meta.set_index("sku")["case_pack_qty"].to_dict()

    inv_cases, inv_units = {}, {}
    for sku, W in TARGET.items():
        cum = proj[proj["sku"] == sku].sort_values("week_ending")["forecast_units"].cumsum().tolist()
        if W is None:
            units = cum[-1] * 1.10
        else:
            lo = cum[W - 2] if W >= 2 else 0
            units = (lo + cum[W - 1]) / 2.0
        cases = max(1, round(units / cpq[sku]))
        inv_cases[sku] = cases
        inv_units[sku] = cases * cpq[sku]

    inv_df = pd.DataFrame({"sku": list(inv_units), "on_hand_units": list(inv_units.values())})
    sop = compute_stockout_date(fc, inv_df, pd.DataFrame())
    sop = compute_decision_deadline(sop, cfg, as_of_date=pd.Timestamp(AS_OF))
    sop = detect_shared_line_conflicts(sop, cfg)

    print("Flag distribution (inventory-only, no schedule):",
          dict(collections.Counter(sop["deadline_flag"])))
    print()
    print("SKU_INVENTORY = [")
    for ln in ["AS", "SC", "DG", "PS", "SB"]:
        print(f"    # --- {ln} ---")
        for sku in sorted(s for s in inv_cases if s.split('-')[1] == ln):
            W = TARGET[sku]
            note = "healthy" if W is None else f"stocks out ~week {W}"
            print(f"    ({sku!r}, \"{AS_OF}\", {inv_cases[sku]}, {note!r}),")
    print("]")


if __name__ == "__main__":
    main()
