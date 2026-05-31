"""Seed co-packer schema and synthetic data into Cinderhaven Postgres.

Idempotent — runs DDL (CREATE TABLE IF NOT EXISTS) then inserts with
ON CONFLICT DO NOTHING.  Safe to run multiple times.

Usage:
    python db/seed_copack.py

Requires DATABASE_URL in environment (or .env in project root).
"""

from __future__ import annotations

import os
import pathlib
import sys

from dotenv import load_dotenv

load_dotenv(pathlib.Path(__file__).resolve().parent.parent / ".env")

import psycopg2

DATABASE_URL = os.environ.get("DATABASE_URL")
if not DATABASE_URL:
    sys.exit("ERROR: DATABASE_URL is not set.")

# ---------------------------------------------------------------
# Reference data — keyed on the demo scenario date 2025-11-01.
# Week N = the Monday N weeks after 2025-11-03 (first Monday after
# the demo reference date of 2025-11-01).
# ---------------------------------------------------------------

CO_PACKERS = [
    ("COPACK-001", "Midwest Production Partners, LLC", "Racine, WI",
     "Single co-packer for all Cinderhaven product lines in v1"),
]

PRODUCTION_LINES = [
    # Line A: Artisan Sauces + top 5 Specialty Condiments (SHARED)
    # Shared line is the source of the conflict story.
    ("LINE-A", "COPACK-001", "Line A — Wet/Sauce",
     "Artisan Sauces; Specialty Condiments (top 5)",
     "Shared line. Artisan Sauces top 5 SKUs and Condiments top 5 SKUs "
     "compete for the same production window."),

    # Line B: remaining Condiments + all Pantry (DEDICATED)
    ("LINE-B", "COPACK-001", "Line B — Condiments/Dry",
     "Specialty Condiments (remaining); Pantry Staples",
     "Dedicated line. No shared-line conflicts in v1."),
]

# lead_time_weeks, min_run_cases per product line
LINE_A_SAUCE_LEAD    = 10
LINE_A_SAUCE_MIN     = 500
LINE_A_CONDIMENT_LEAD = 8
LINE_A_CONDIMENT_MIN  = 300
LINE_B_CONDIMENT_LEAD = 8
LINE_B_CONDIMENT_MIN  = 300
LINE_B_PANTRY_LEAD    = 12
LINE_B_PANTRY_MIN     = 400
LINE_B_DRY_LEAD       = 10
LINE_B_DRY_MIN        = 350
LINE_B_SNACK_LEAD     = 8
LINE_B_SNACK_MIN      = 300

# All 50 SKUs — (sku, line_id, lead_time_weeks, min_run_cases, notes)
# Actual Cinderhaven SKU format: CHP-{line}-{NNN}
# Product lines: AS=Artisan Sauces, SC=Specialty Condiments,
#                PS=Pantry Staples, DG=Dried Goods, SB=Snack Bites
SKU_PRODUCTION_CONFIG = [
    # --- Artisan Sauces (CHP-AS-001 to CHP-AS-010) → Line A ---
    ("CHP-AS-001", "LINE-A", LINE_A_SAUCE_LEAD, LINE_A_SAUCE_MIN,
     "Top-selling sauce. February 2025 OOS event. Hero demo SKU."),
    ("CHP-AS-002", "LINE-A", LINE_A_SAUCE_LEAD, LINE_A_SAUCE_MIN, None),
    ("CHP-AS-003", "LINE-A", LINE_A_SAUCE_LEAD, LINE_A_SAUCE_MIN, None),
    ("CHP-AS-004", "LINE-A", LINE_A_SAUCE_LEAD, LINE_A_SAUCE_MIN, None),
    ("CHP-AS-005", "LINE-A", LINE_A_SAUCE_LEAD, LINE_A_SAUCE_MIN, None),
    ("CHP-AS-006", "LINE-A", LINE_A_SAUCE_LEAD, LINE_A_SAUCE_MIN, None),
    ("CHP-AS-007", "LINE-A", LINE_A_SAUCE_LEAD, LINE_A_SAUCE_MIN, None),
    ("CHP-AS-008", "LINE-A", LINE_A_SAUCE_LEAD, LINE_A_SAUCE_MIN, None),
    ("CHP-AS-009", "LINE-A", LINE_A_SAUCE_LEAD, LINE_A_SAUCE_MIN, None),
    ("CHP-AS-010", "LINE-A", LINE_A_SAUCE_LEAD, LINE_A_SAUCE_MIN, None),

    # --- Specialty Condiments top 5 (CHP-SC-001 to CHP-SC-005) → Line A (shared) ---
    ("CHP-SC-001", "LINE-A", LINE_A_CONDIMENT_LEAD, LINE_A_CONDIMENT_MIN,
     "Shares Line A with Artisan Sauces. Conflict demo SKU."),
    ("CHP-SC-002", "LINE-A", LINE_A_CONDIMENT_LEAD, LINE_A_CONDIMENT_MIN, None),
    ("CHP-SC-003", "LINE-A", LINE_A_CONDIMENT_LEAD, LINE_A_CONDIMENT_MIN, None),
    ("CHP-SC-004", "LINE-A", LINE_A_CONDIMENT_LEAD, LINE_A_CONDIMENT_MIN, None),
    ("CHP-SC-005", "LINE-A", LINE_A_CONDIMENT_LEAD, LINE_A_CONDIMENT_MIN, None),

    # --- Specialty Condiments remaining (CHP-SC-006 to CHP-SC-010) → Line B ---
    ("CHP-SC-006", "LINE-B", LINE_B_CONDIMENT_LEAD, LINE_B_CONDIMENT_MIN, None),
    ("CHP-SC-007", "LINE-B", LINE_B_CONDIMENT_LEAD, LINE_B_CONDIMENT_MIN, None),
    ("CHP-SC-008", "LINE-B", LINE_B_CONDIMENT_LEAD, LINE_B_CONDIMENT_MIN, None),
    ("CHP-SC-009", "LINE-B", LINE_B_CONDIMENT_LEAD, LINE_B_CONDIMENT_MIN, None),
    ("CHP-SC-010", "LINE-B", LINE_B_CONDIMENT_LEAD, LINE_B_CONDIMENT_MIN, None),

    # --- Dried Goods (CHP-DG-001 to CHP-DG-010) → Line B ---
    ("CHP-DG-001", "LINE-B", LINE_B_DRY_LEAD, LINE_B_DRY_MIN, None),
    ("CHP-DG-002", "LINE-B", LINE_B_DRY_LEAD, LINE_B_DRY_MIN, None),
    ("CHP-DG-003", "LINE-B", LINE_B_DRY_LEAD, LINE_B_DRY_MIN, None),
    ("CHP-DG-004", "LINE-B", LINE_B_DRY_LEAD, LINE_B_DRY_MIN, None),
    ("CHP-DG-005", "LINE-B", LINE_B_DRY_LEAD, LINE_B_DRY_MIN, None),
    ("CHP-DG-006", "LINE-B", LINE_B_DRY_LEAD, LINE_B_DRY_MIN, None),
    ("CHP-DG-007", "LINE-B", LINE_B_DRY_LEAD, LINE_B_DRY_MIN, None),
    ("CHP-DG-008", "LINE-B", LINE_B_DRY_LEAD, LINE_B_DRY_MIN, None),
    ("CHP-DG-009", "LINE-B", LINE_B_DRY_LEAD, LINE_B_DRY_MIN, None),
    ("CHP-DG-010", "LINE-B", LINE_B_DRY_LEAD, LINE_B_DRY_MIN, None),

    # --- Pantry Staples (CHP-PS-001 to CHP-PS-010) → Line B ---
    ("CHP-PS-001", "LINE-B", LINE_B_PANTRY_LEAD, LINE_B_PANTRY_MIN, None),
    ("CHP-PS-002", "LINE-B", LINE_B_PANTRY_LEAD, LINE_B_PANTRY_MIN, None),
    ("CHP-PS-003", "LINE-B", LINE_B_PANTRY_LEAD, LINE_B_PANTRY_MIN, None),
    ("CHP-PS-004", "LINE-B", LINE_B_PANTRY_LEAD, LINE_B_PANTRY_MIN, None),
    ("CHP-PS-005", "LINE-B", LINE_B_PANTRY_LEAD, LINE_B_PANTRY_MIN, None),
    ("CHP-PS-006", "LINE-B", LINE_B_PANTRY_LEAD, LINE_B_PANTRY_MIN, None),
    ("CHP-PS-007", "LINE-B", LINE_B_PANTRY_LEAD, LINE_B_PANTRY_MIN, None),
    ("CHP-PS-008", "LINE-B", LINE_B_PANTRY_LEAD, LINE_B_PANTRY_MIN, None),
    ("CHP-PS-009", "LINE-B", LINE_B_PANTRY_LEAD, LINE_B_PANTRY_MIN, None),
    ("CHP-PS-010", "LINE-B", LINE_B_PANTRY_LEAD, LINE_B_PANTRY_MIN, None),

    # --- Snack Bites (CHP-SB-001 to CHP-SB-010) → Line B ---
    ("CHP-SB-001", "LINE-B", LINE_B_SNACK_LEAD, LINE_B_SNACK_MIN, None),
    ("CHP-SB-002", "LINE-B", LINE_B_SNACK_LEAD, LINE_B_SNACK_MIN, None),
    ("CHP-SB-003", "LINE-B", LINE_B_SNACK_LEAD, LINE_B_SNACK_MIN, None),
    ("CHP-SB-004", "LINE-B", LINE_B_SNACK_LEAD, LINE_B_SNACK_MIN, None),
    ("CHP-SB-005", "LINE-B", LINE_B_SNACK_LEAD, LINE_B_SNACK_MIN, None),
    ("CHP-SB-006", "LINE-B", LINE_B_SNACK_LEAD, LINE_B_SNACK_MIN, None),
    ("CHP-SB-007", "LINE-B", LINE_B_SNACK_LEAD, LINE_B_SNACK_MIN, None),
    ("CHP-SB-008", "LINE-B", LINE_B_SNACK_LEAD, LINE_B_SNACK_MIN, None),
    ("CHP-SB-009", "LINE-B", LINE_B_SNACK_LEAD, LINE_B_SNACK_MIN, None),
    ("CHP-SB-010", "LINE-B", LINE_B_SNACK_LEAD, LINE_B_SNACK_MIN, None),
]

# Production schedule — ~30 booked runs.
# Reference date: 2025-11-01.  Week N starts on Monday 2025-11-03 + (N-1)*7 days.
# KEY STORY:
#   CHP-AS-001: run in week 4 (2025-11-24), NO run in weeks 8-14.
#               stockout approximately week 9 with true demand.
#   CHP-SC-001: NO scheduled run → stockout approximately week 10.
#               decision deadline CRITICAL (past due given lead time = 8 wks).
#               shared_line_conflict = True for both.
# Line A booked at ~40% capacity through week 6.
# (run_id, sku, line_id, scheduled_week, quantity_cases, status)
PRODUCTION_SCHEDULE = [
    # --- Line A: weeks 1-6 (40% capacity booked) ---
    ("RUN-A001", "CHP-AS-002", "LINE-A", "2025-11-03", 500, "booked"),
    ("RUN-A002", "CHP-AS-003", "LINE-A", "2025-11-10", 500, "booked"),
    ("RUN-A003", "CHP-SC-002", "LINE-A", "2025-11-10", 300, "booked"),
    ("RUN-A004", "CHP-AS-004", "LINE-A", "2025-11-17", 500, "booked"),
    ("RUN-A005", "CHP-SC-003", "LINE-A", "2025-11-17", 300, "booked"),
    # KEY: CHP-AS-001 run in week 4 (last scheduled run before stockout)
    ("RUN-A006", "CHP-AS-001", "LINE-A", "2025-11-24", 500, "booked"),
    ("RUN-A007", "CHP-AS-005", "LINE-A", "2025-11-24", 500, "booked"),
    ("RUN-A008", "CHP-SC-004", "LINE-A", "2025-12-01", 300, "booked"),
    ("RUN-A009", "CHP-AS-006", "LINE-A", "2025-12-01", 500, "booked"),
    ("RUN-A010", "CHP-AS-007", "LINE-A", "2025-12-08", 500, "booked"),
    ("RUN-A011", "CHP-SC-005", "LINE-A", "2025-12-08", 300, "booked"),
    ("RUN-A012", "CHP-AS-008", "LINE-A", "2025-12-08", 500, "booked"),

    # --- Line A: weeks 8-14 (future runs — NOT CHP-AS-001 or CHP-SC-001) ---
    ("RUN-A013", "CHP-AS-009", "LINE-A", "2025-12-22", 500, "booked"),
    ("RUN-A014", "CHP-AS-010", "LINE-A", "2026-01-05", 500, "booked"),
    ("RUN-A015", "CHP-AS-002", "LINE-A", "2026-01-19", 500, "booked"),
    ("RUN-A016", "CHP-AS-003", "LINE-A", "2026-02-02", 500, "booked"),

    # --- Line B: weeks 1-6 ---
    ("RUN-B001", "CHP-DG-001", "LINE-B", "2025-11-03", 350, "booked"),
    ("RUN-B002", "CHP-PS-001", "LINE-B", "2025-11-03", 400, "booked"),
    ("RUN-B003", "CHP-DG-002", "LINE-B", "2025-11-10", 350, "booked"),
    ("RUN-B004", "CHP-SB-001", "LINE-B", "2025-11-10", 300, "booked"),
    ("RUN-B005", "CHP-SC-006", "LINE-B", "2025-11-17", 300, "booked"),
    ("RUN-B006", "CHP-PS-002", "LINE-B", "2025-11-24", 400, "booked"),
    ("RUN-B007", "CHP-DG-003", "LINE-B", "2025-12-01", 350, "booked"),
    ("RUN-B008", "CHP-SB-002", "LINE-B", "2025-12-01", 300, "booked"),
    ("RUN-B009", "CHP-SC-007", "LINE-B", "2025-12-08", 300, "booked"),
    ("RUN-B010", "CHP-PS-003", "LINE-B", "2025-12-08", 400, "booked"),

    # --- Line B: weeks 8-14 ---
    ("RUN-B011", "CHP-DG-004", "LINE-B", "2025-12-22", 350, "booked"),
    ("RUN-B012", "CHP-SB-003", "LINE-B", "2025-12-22", 300, "booked"),
    ("RUN-B013", "CHP-SC-008", "LINE-B", "2026-01-05", 300, "booked"),
    ("RUN-B014", "CHP-PS-004", "LINE-B", "2026-01-05", 400, "booked"),
]

# Current on-hand inventory as of 2025-11-01.
# CHP-0001 and CHP-0023 are intentionally low to produce the conflict story.
# CALIBRATION NOTE (HANDOFF.md): exact stockout timing depends on scan_data
# velocities.  Adjust on_hand_cases for CHP-0001 and CHP-0023 once the OOS
# correction module produces actual true_demand figures.
SKU_INVENTORY = [
    # Demo conflict SKUs — designed to stock out within the 12-week horizon
    ("CHP-AS-001", "2025-11-01", 50,  "Low inventory for demo story. Calibrate against scan_data."),
    ("CHP-SC-001", "2025-11-01", 120, "No scheduled run. Calibrate against scan_data."),

    # Artisan Sauces with recent production runs
    ("CHP-AS-002", "2025-11-01", 420, None),
    ("CHP-AS-003", "2025-11-01", 380, None),
    ("CHP-AS-004", "2025-11-01", 350, None),
    ("CHP-AS-005", "2025-11-01", 310, None),
    ("CHP-AS-006", "2025-11-01", 290, None),
    ("CHP-AS-007", "2025-11-01", 260, None),
    ("CHP-AS-008", "2025-11-01", 240, None),
    ("CHP-AS-009", "2025-11-01", 220, None),
    ("CHP-AS-010", "2025-11-01", 200, None),

    # Specialty Condiments top 5 (Line A)
    ("CHP-SC-002", "2025-11-01", 280, None),
    ("CHP-SC-003", "2025-11-01", 260, None),
    ("CHP-SC-004", "2025-11-01", 240, None),
    ("CHP-SC-005", "2025-11-01", 220, None),

    # Specialty Condiments remaining (Line B)
    ("CHP-SC-006", "2025-11-01", 320, None),
    ("CHP-SC-007", "2025-11-01", 300, None),
    ("CHP-SC-008", "2025-11-01", 280, None),
    ("CHP-SC-009", "2025-11-01", 260, None),
    ("CHP-SC-010", "2025-11-01", 240, None),

    # Dried Goods (Line B)
    ("CHP-DG-001", "2025-11-01", 380, None),
    ("CHP-DG-002", "2025-11-01", 360, None),
    ("CHP-DG-003", "2025-11-01", 340, None),
    ("CHP-DG-004", "2025-11-01", 300, None),
    ("CHP-DG-005", "2025-11-01", 280, None),
    ("CHP-DG-006", "2025-11-01", 260, None),
    ("CHP-DG-007", "2025-11-01", 240, None),
    ("CHP-DG-008", "2025-11-01", 220, None),
    ("CHP-DG-009", "2025-11-01", 200, None),
    ("CHP-DG-010", "2025-11-01", 180, None),

    # Pantry Staples (Line B)
    ("CHP-PS-001", "2025-11-01", 400, None),
    ("CHP-PS-002", "2025-11-01", 380, None),
    ("CHP-PS-003", "2025-11-01", 360, None),
    ("CHP-PS-004", "2025-11-01", 180, None),  # CHP-PS-004 is olive oil — smaller case
    ("CHP-PS-005", "2025-11-01", 340, None),
    ("CHP-PS-006", "2025-11-01", 320, None),
    ("CHP-PS-007", "2025-11-01", 300, None),
    ("CHP-PS-008", "2025-11-01", 280, None),
    ("CHP-PS-009", "2025-11-01", 260, None),
    ("CHP-PS-010", "2025-11-01", 240, None),

    # Snack Bites (Line B)
    ("CHP-SB-001", "2025-11-01", 350, None),
    ("CHP-SB-002", "2025-11-01", 320, None),
    ("CHP-SB-003", "2025-11-01", 300, None),
    ("CHP-SB-004", "2025-11-01", 280, None),
    ("CHP-SB-005", "2025-11-01", 260, None),
    ("CHP-SB-006", "2025-11-01", 240, None),
    ("CHP-SB-007", "2025-11-01", 220, None),
    ("CHP-SB-008", "2025-11-01", 200, None),
    ("CHP-SB-009", "2025-11-01", 180, None),
    ("CHP-SB-010", "2025-11-01", 160, None),
]


import re as _re

def _run_ddl(cur, schema_path: pathlib.Path) -> None:
    ddl = schema_path.read_text(encoding="utf-8")
    # Strip line comments before splitting so semicolons inside comments don't confuse the split
    ddl_no_comments = _re.sub(r"--[^\n]*", "", ddl)
    for statement in ddl_no_comments.split(";"):
        if statement.strip():
            cur.execute(statement.strip())


def seed(conn) -> None:
    cur = conn.cursor()
    schema_path = pathlib.Path(__file__).parent / "schema_copack.sql"
    _run_ddl(cur, schema_path)
    print("DDL applied.")

    cur.executemany(
        """
        INSERT INTO co_packers (co_packer_id, name, location, notes)
        VALUES (%s, %s, %s, %s)
        ON CONFLICT (co_packer_id) DO NOTHING
        """,
        CO_PACKERS,
    )
    print(f"  co_packers: {cur.rowcount} inserted")

    cur.executemany(
        """
        INSERT INTO production_lines (line_id, co_packer_id, line_name, product_line_affinity, notes)
        VALUES (%s, %s, %s, %s, %s)
        ON CONFLICT (line_id) DO NOTHING
        """,
        PRODUCTION_LINES,
    )
    print(f"  production_lines: {cur.rowcount} inserted")

    cur.executemany(
        """
        INSERT INTO sku_production_config (sku, line_id, lead_time_weeks, min_run_cases, notes)
        VALUES (%s, %s, %s, %s, %s)
        ON CONFLICT (sku) DO NOTHING
        """,
        SKU_PRODUCTION_CONFIG,
    )
    print(f"  sku_production_config: {cur.rowcount} inserted")

    cur.executemany(
        """
        INSERT INTO production_schedule (run_id, sku, line_id, scheduled_week, quantity_cases, status)
        VALUES (%s, %s, %s, %s, %s, %s)
        ON CONFLICT (run_id) DO NOTHING
        """,
        PRODUCTION_SCHEDULE,
    )
    print(f"  production_schedule: {cur.rowcount} inserted")

    cur.executemany(
        """
        INSERT INTO sku_inventory (sku, as_of_date, on_hand_cases, notes)
        VALUES (%s, %s, %s, %s)
        ON CONFLICT (sku) DO NOTHING
        """,
        SKU_INVENTORY,
    )
    print(f"  sku_inventory: {cur.rowcount} inserted")

    conn.commit()
    print("Seed complete.")


def verify(conn) -> None:
    cur = conn.cursor()

    cur.execute("SELECT COUNT(*) FROM sku_production_config")
    n = cur.fetchone()[0]
    assert n == 50, f"Expected 50 rows in sku_production_config, got {n}"

    cur.execute("SELECT COUNT(*) FROM production_schedule")
    n = cur.fetchone()[0]
    assert n == len(PRODUCTION_SCHEDULE), \
        f"Expected {len(PRODUCTION_SCHEDULE)} rows in production_schedule, got {n}"

    cur.execute("SELECT COUNT(*) FROM sku_inventory")
    n = cur.fetchone()[0]
    assert n == 50, f"Expected 50 rows in sku_inventory, got {n}"

    # Every product_master SKU must have exactly one sku_production_config row
    cur.execute("""
        SELECT COUNT(*)
        FROM product_master p
        LEFT JOIN sku_production_config c ON c.sku = p.sku
        WHERE c.sku IS NULL
    """)
    missing = cur.fetchone()[0]
    assert missing == 0, f"{missing} product_master SKUs have no sku_production_config row"

    # CHP-AS-001 should have exactly one production_schedule row (week 4 run)
    cur.execute("SELECT COUNT(*) FROM production_schedule WHERE sku = 'CHP-AS-001'")
    runs = cur.fetchone()[0]
    assert runs == 1, f"Expected 1 production run for CHP-AS-001, got {runs}"

    # At least two Line-A SKUs should share a scheduled_week (overlap → conflict candidate)
    cur.execute("""
        SELECT COUNT(*)
        FROM (
            SELECT scheduled_week, COUNT(DISTINCT sku) AS sku_count
            FROM production_schedule
            WHERE line_id = 'LINE-A'
            GROUP BY scheduled_week
            HAVING COUNT(DISTINCT sku) >= 2
        ) t
    """)
    conflict_weeks = cur.fetchone()[0]
    assert conflict_weeks >= 1, "Expected at least one week with 2+ Line-A SKUs scheduled"

    print("Verification passed.")


if __name__ == "__main__":
    conn = psycopg2.connect(DATABASE_URL, options="-c search_path=raw,public")
    conn.autocommit = False
    try:
        seed(conn)
        verify(conn)
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()
