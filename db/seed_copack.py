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

# All 50 SKUs — (sku, line_id, lead_time_weeks, min_run_cases, notes)
SKU_PRODUCTION_CONFIG = [
    # --- Artisan Sauces (CHP-0001 to CHP-0022) → Line A ---
    ("CHP-0001", "LINE-A", LINE_A_SAUCE_LEAD, LINE_A_SAUCE_MIN,
     "Top-selling sauce. February 2025 OOS event. Hero demo SKU."),
    ("CHP-0002", "LINE-A", LINE_A_SAUCE_LEAD, LINE_A_SAUCE_MIN, None),
    ("CHP-0003", "LINE-A", LINE_A_SAUCE_LEAD, LINE_A_SAUCE_MIN, None),
    ("CHP-0004", "LINE-A", LINE_A_SAUCE_LEAD, LINE_A_SAUCE_MIN, None),
    ("CHP-0005", "LINE-A", LINE_A_SAUCE_LEAD, LINE_A_SAUCE_MIN, None),
    ("CHP-0006", "LINE-A", LINE_A_SAUCE_LEAD, LINE_A_SAUCE_MIN, None),
    ("CHP-0007", "LINE-A", LINE_A_SAUCE_LEAD, LINE_A_SAUCE_MIN, None),
    ("CHP-0008", "LINE-A", LINE_A_SAUCE_LEAD, LINE_A_SAUCE_MIN, None),
    ("CHP-0009", "LINE-A", LINE_A_SAUCE_LEAD, LINE_A_SAUCE_MIN, None),
    ("CHP-0010", "LINE-A", LINE_A_SAUCE_LEAD, LINE_A_SAUCE_MIN, None),
    ("CHP-0011", "LINE-A", LINE_A_SAUCE_LEAD, LINE_A_SAUCE_MIN, None),
    ("CHP-0012", "LINE-A", LINE_A_SAUCE_LEAD, LINE_A_SAUCE_MIN, None),
    ("CHP-0013", "LINE-A", LINE_A_SAUCE_LEAD, LINE_A_SAUCE_MIN, None),
    ("CHP-0014", "LINE-A", LINE_A_SAUCE_LEAD, LINE_A_SAUCE_MIN, None),
    ("CHP-0015", "LINE-A", LINE_A_SAUCE_LEAD, LINE_A_SAUCE_MIN, None),
    ("CHP-0016", "LINE-A", LINE_A_SAUCE_LEAD, LINE_A_SAUCE_MIN, None),
    ("CHP-0017", "LINE-A", LINE_A_SAUCE_LEAD, LINE_A_SAUCE_MIN, None),
    ("CHP-0018", "LINE-A", LINE_A_SAUCE_LEAD, LINE_A_SAUCE_MIN, None),
    ("CHP-0019", "LINE-A", LINE_A_SAUCE_LEAD, LINE_A_SAUCE_MIN, None),
    ("CHP-0020", "LINE-A", LINE_A_SAUCE_LEAD, LINE_A_SAUCE_MIN, None),
    ("CHP-0021", "LINE-A", LINE_A_SAUCE_LEAD, LINE_A_SAUCE_MIN, None),
    ("CHP-0022", "LINE-A", LINE_A_SAUCE_LEAD, LINE_A_SAUCE_MIN, None),

    # --- Specialty Condiments top 5 (CHP-0023 to CHP-0027) → Line A (shared) ---
    ("CHP-0023", "LINE-A", LINE_A_CONDIMENT_LEAD, LINE_A_CONDIMENT_MIN,
     "Shares Line A with Artisan Sauces. Conflict demo SKU."),
    ("CHP-0024", "LINE-A", LINE_A_CONDIMENT_LEAD, LINE_A_CONDIMENT_MIN, None),
    ("CHP-0025", "LINE-A", LINE_A_CONDIMENT_LEAD, LINE_A_CONDIMENT_MIN, None),
    ("CHP-0026", "LINE-A", LINE_A_CONDIMENT_LEAD, LINE_A_CONDIMENT_MIN, None),
    ("CHP-0027", "LINE-A", LINE_A_CONDIMENT_LEAD, LINE_A_CONDIMENT_MIN, None),

    # --- Specialty Condiments remaining (CHP-0028 to CHP-0038) → Line B ---
    ("CHP-0028", "LINE-B", LINE_B_CONDIMENT_LEAD, LINE_B_CONDIMENT_MIN, None),
    ("CHP-0029", "LINE-B", LINE_B_CONDIMENT_LEAD, LINE_B_CONDIMENT_MIN, None),
    ("CHP-0030", "LINE-B", LINE_B_CONDIMENT_LEAD, LINE_B_CONDIMENT_MIN, None),
    ("CHP-0031", "LINE-B", LINE_B_CONDIMENT_LEAD, LINE_B_CONDIMENT_MIN, None),
    ("CHP-0032", "LINE-B", LINE_B_CONDIMENT_LEAD, LINE_B_CONDIMENT_MIN, None),
    ("CHP-0033", "LINE-B", LINE_B_CONDIMENT_LEAD, LINE_B_CONDIMENT_MIN, None),
    ("CHP-0034", "LINE-B", LINE_B_CONDIMENT_LEAD, LINE_B_CONDIMENT_MIN, None),
    ("CHP-0035", "LINE-B", LINE_B_CONDIMENT_LEAD, LINE_B_CONDIMENT_MIN, None),
    ("CHP-0036", "LINE-B", LINE_B_CONDIMENT_LEAD, LINE_B_CONDIMENT_MIN, None),
    ("CHP-0037", "LINE-B", LINE_B_CONDIMENT_LEAD, LINE_B_CONDIMENT_MIN, None),
    ("CHP-0038", "LINE-B", LINE_B_CONDIMENT_LEAD, LINE_B_CONDIMENT_MIN, None),

    # --- Pantry Staples (CHP-0039 to CHP-0050) → Line B ---
    ("CHP-0039", "LINE-B", LINE_B_PANTRY_LEAD, LINE_B_PANTRY_MIN, None),
    ("CHP-0040", "LINE-B", LINE_B_PANTRY_LEAD, LINE_B_PANTRY_MIN, None),
    ("CHP-0041", "LINE-B", LINE_B_PANTRY_LEAD, LINE_B_PANTRY_MIN, None),
    ("CHP-0042", "LINE-B", LINE_B_PANTRY_LEAD, LINE_B_PANTRY_MIN, None),
    ("CHP-0043", "LINE-B", LINE_B_PANTRY_LEAD, LINE_B_PANTRY_MIN, None),
    ("CHP-0044", "LINE-B", LINE_B_PANTRY_LEAD, LINE_B_PANTRY_MIN, None),
    ("CHP-0045", "LINE-B", LINE_B_PANTRY_LEAD, LINE_B_PANTRY_MIN, None),
    ("CHP-0046", "LINE-B", LINE_B_PANTRY_LEAD, LINE_B_PANTRY_MIN, None),
    ("CHP-0047", "LINE-B", LINE_B_PANTRY_LEAD, LINE_B_PANTRY_MIN, None),
    ("CHP-0048", "LINE-B", LINE_B_PANTRY_LEAD, LINE_B_PANTRY_MIN, None),
    ("CHP-0049", "LINE-B", LINE_B_PANTRY_LEAD, LINE_B_PANTRY_MIN, None),
    ("CHP-0050", "LINE-B", LINE_B_PANTRY_LEAD, LINE_B_PANTRY_MIN, None),
]

# Production schedule — ~30 booked runs.
# Reference date: 2025-11-01.  Week N starts on Monday 2025-11-03 + (N-1)*7 days.
# KEY STORY:
#   CHP-0001: run in week 4 (2025-11-24), NO run in weeks 8-14.
#             → stockout approximately week 9 with true demand (see HANDOFF calibration note).
#   CHP-0023: NO scheduled run → stockout approximately week 10.
#             → decision deadline ~week 2 (CRITICAL), within 4-week window of CHP-0001
#                (PAST DUE) → shared_line_conflict = True for both.
# Line A booked at ~40% capacity through week 6.
# (run_id, sku, line_id, scheduled_week, quantity_cases, status)
PRODUCTION_SCHEDULE = [
    # --- Line A: weeks 1-6 (40% capacity booked) ---
    ("RUN-A001", "CHP-0002", "LINE-A", "2025-11-03", 500, "booked"),
    ("RUN-A002", "CHP-0003", "LINE-A", "2025-11-10", 500, "booked"),
    ("RUN-A003", "CHP-0026", "LINE-A", "2025-11-10", 300, "booked"),
    ("RUN-A004", "CHP-0004", "LINE-A", "2025-11-17", 500, "booked"),
    ("RUN-A005", "CHP-0025", "LINE-A", "2025-11-17", 300, "booked"),
    # KEY: CHP-0001 run in week 4
    ("RUN-A006", "CHP-0001", "LINE-A", "2025-11-24", 500, "booked"),
    ("RUN-A007", "CHP-0005", "LINE-A", "2025-11-24", 500, "booked"),
    ("RUN-A008", "CHP-0027", "LINE-A", "2025-12-01", 300, "booked"),
    ("RUN-A009", "CHP-0007", "LINE-A", "2025-12-01", 500, "booked"),
    ("RUN-A010", "CHP-0008", "LINE-A", "2025-12-08", 500, "booked"),
    ("RUN-A011", "CHP-0024", "LINE-A", "2025-12-08", 300, "booked"),
    ("RUN-A012", "CHP-0009", "LINE-A", "2025-12-08", 500, "booked"),

    # --- Line A: weeks 8-14 (future booked runs — NOT CHP-0001) ---
    ("RUN-A013", "CHP-0010", "LINE-A", "2025-12-22", 500, "booked"),
    ("RUN-A014", "CHP-0011", "LINE-A", "2026-01-05", 500, "booked"),
    ("RUN-A015", "CHP-0012", "LINE-A", "2026-01-19", 500, "booked"),
    ("RUN-A016", "CHP-0013", "LINE-A", "2026-02-02", 500, "booked"),

    # --- Line B: weeks 1-6 ---
    ("RUN-B001", "CHP-0028", "LINE-B", "2025-11-03", 300, "booked"),
    ("RUN-B002", "CHP-0039", "LINE-B", "2025-11-03", 400, "booked"),
    ("RUN-B003", "CHP-0030", "LINE-B", "2025-11-10", 300, "booked"),
    ("RUN-B004", "CHP-0040", "LINE-B", "2025-11-10", 400, "booked"),
    ("RUN-B005", "CHP-0032", "LINE-B", "2025-11-17", 300, "booked"),
    ("RUN-B006", "CHP-0041", "LINE-B", "2025-11-24", 400, "booked"),
    ("RUN-B007", "CHP-0035", "LINE-B", "2025-12-01", 300, "booked"),
    ("RUN-B008", "CHP-0042", "LINE-B", "2025-12-01", 400, "booked"),
    ("RUN-B009", "CHP-0033", "LINE-B", "2025-12-08", 300, "booked"),
    ("RUN-B010", "CHP-0044", "LINE-B", "2025-12-08", 400, "booked"),

    # --- Line B: weeks 8-14 ---
    ("RUN-B011", "CHP-0036", "LINE-B", "2025-12-22", 300, "booked"),
    ("RUN-B012", "CHP-0043", "LINE-B", "2025-12-22", 400, "booked"),
    ("RUN-B013", "CHP-0037", "LINE-B", "2026-01-05", 300, "booked"),
    ("RUN-B014", "CHP-0046", "LINE-B", "2026-01-05", 400, "booked"),
]

# Current on-hand inventory as of 2025-11-01.
# CHP-0001 and CHP-0023 are intentionally low to produce the conflict story.
# CALIBRATION NOTE (HANDOFF.md): exact stockout timing depends on scan_data
# velocities.  Adjust on_hand_cases for CHP-0001 and CHP-0023 once the OOS
# correction module produces actual true_demand figures.
SKU_INVENTORY = [
    # Demo conflict SKUs — designed to stock out within the 12-week horizon
    ("CHP-0001", "2025-11-01", 50,  "Low inventory for demo story. Calibrate against scan_data."),
    ("CHP-0023", "2025-11-01", 160, "No scheduled run. Calibrate against scan_data."),

    # Artisan Sauces with recent production runs — higher inventory
    ("CHP-0002", "2025-11-01", 420, None),
    ("CHP-0003", "2025-11-01", 380, None),
    ("CHP-0004", "2025-11-01", 350, None),
    ("CHP-0005", "2025-11-01", 310, None),
    ("CHP-0006", "2025-11-01", 290, None),
    ("CHP-0007", "2025-11-01", 260, None),
    ("CHP-0008", "2025-11-01", 240, None),
    ("CHP-0009", "2025-11-01", 220, None),
    ("CHP-0010", "2025-11-01", 200, None),
    ("CHP-0011", "2025-11-01", 185, None),
    ("CHP-0012", "2025-11-01", 170, None),
    ("CHP-0013", "2025-11-01", 155, None),
    ("CHP-0014", "2025-11-01", 140, None),
    ("CHP-0015", "2025-11-01", 130, None),
    ("CHP-0016", "2025-11-01", 120, None),
    ("CHP-0017", "2025-11-01", 110, None),
    ("CHP-0018", "2025-11-01", 100, None),
    ("CHP-0019", "2025-11-01", 95,  None),
    ("CHP-0020", "2025-11-01", 90,  None),
    ("CHP-0021", "2025-11-01", 85,  None),
    ("CHP-0022", "2025-11-01", 80,  None),

    # Specialty Condiments top 5 (Line A)
    ("CHP-0024", "2025-11-01", 280, None),
    ("CHP-0025", "2025-11-01", 260, None),
    ("CHP-0026", "2025-11-01", 240, None),
    ("CHP-0027", "2025-11-01", 220, None),

    # Specialty Condiments remaining (Line B)
    ("CHP-0028", "2025-11-01", 320, None),
    ("CHP-0029", "2025-11-01", 300, None),
    ("CHP-0030", "2025-11-01", 280, None),
    ("CHP-0031", "2025-11-01", 260, None),
    ("CHP-0032", "2025-11-01", 240, None),
    ("CHP-0033", "2025-11-01", 220, None),
    ("CHP-0034", "2025-11-01", 200, None),
    ("CHP-0035", "2025-11-01", 180, None),
    ("CHP-0036", "2025-11-01", 160, None),
    ("CHP-0037", "2025-11-01", 140, None),
    ("CHP-0038", "2025-11-01", 120, None),

    # Pantry Staples (Line B)
    ("CHP-0039", "2025-11-01", 380, None),
    ("CHP-0040", "2025-11-01", 360, None),
    ("CHP-0041", "2025-11-01", 340, None),
    ("CHP-0042", "2025-11-01", 180, None),  # oil — smaller case size
    ("CHP-0043", "2025-11-01", 170, None),
    ("CHP-0044", "2025-11-01", 160, None),
    ("CHP-0045", "2025-11-01", 150, None),
    ("CHP-0046", "2025-11-01", 280, None),
    ("CHP-0047", "2025-11-01", 260, None),
    ("CHP-0048", "2025-11-01", 240, None),
    ("CHP-0049", "2025-11-01", 150, None),
    ("CHP-0050", "2025-11-01", 140, None),
]


def _run_ddl(cur, schema_path: pathlib.Path) -> None:
    ddl = schema_path.read_text(encoding="utf-8")
    # Execute each statement separately (psycopg2 doesn't support multi-statement execute)
    for statement in ddl.split(";"):
        stmt = statement.strip()
        if stmt:
            cur.execute(stmt)


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

    # CHP-0001 should have exactly one production_schedule row (week 4 run)
    cur.execute("SELECT COUNT(*) FROM production_schedule WHERE sku = 'CHP-0001'")
    runs = cur.fetchone()[0]
    assert runs == 1, f"Expected 1 production run for CHP-0001, got {runs}"

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
    conn = psycopg2.connect(DATABASE_URL)
    conn.autocommit = False
    try:
        seed(conn)
        verify(conn)
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()
