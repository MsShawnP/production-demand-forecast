-- Co-packer schema for the Production Demand Forecast demo.
-- All tables use CREATE TABLE IF NOT EXISTS — safe to re-run.
-- TEXT primary keys match the Cinderhaven SKU/ID convention.
-- Date columns use ISO 8601 text strings (YYYY-MM-DD).
--
-- Demo reference date: 2025-11-01 ("today" in the Cinderhaven scenario)
-- Line A (shared): Artisan Sauces + top 5 Specialty Condiments
-- Line B (dedicated): remaining Condiments + all Pantry Staples

-- ---------------------------------------------------------------
-- co_packers
-- One Cinderhaven co-packer for v1.
-- ---------------------------------------------------------------
CREATE TABLE IF NOT EXISTS co_packers (
    co_packer_id   TEXT PRIMARY KEY,
    name           TEXT NOT NULL,
    location       TEXT,
    notes          TEXT
);

-- ---------------------------------------------------------------
-- production_lines
-- Two lines at the co-packer facility.
-- ---------------------------------------------------------------
CREATE TABLE IF NOT EXISTS production_lines (
    line_id                TEXT PRIMARY KEY,
    co_packer_id           TEXT NOT NULL,
    line_name              TEXT NOT NULL,
    product_line_affinity  TEXT,
    notes                  TEXT
);

-- ---------------------------------------------------------------
-- sku_production_config
-- One row per SKU: which line, lead time, minimum run.
-- ---------------------------------------------------------------
CREATE TABLE IF NOT EXISTS sku_production_config (
    sku              TEXT PRIMARY KEY,
    line_id          TEXT NOT NULL,
    lead_time_weeks  INTEGER NOT NULL,
    min_run_cases    INTEGER NOT NULL,
    notes            TEXT
);

-- ---------------------------------------------------------------
-- production_schedule
-- Booked production runs.  ~30 synthetic rows seeded by seed_copack.py.
-- scheduled_week = ISO date of the Monday that starts the production week.
-- ---------------------------------------------------------------
CREATE TABLE IF NOT EXISTS production_schedule (
    run_id           TEXT PRIMARY KEY,
    sku              TEXT NOT NULL,
    line_id          TEXT NOT NULL,
    scheduled_week   TEXT NOT NULL,
    quantity_cases   INTEGER NOT NULL,
    status           TEXT NOT NULL DEFAULT 'booked'
);

-- ---------------------------------------------------------------
-- sku_inventory
-- Current on-hand inventory as of the demo reference date (2025-11-01).
-- The capacity overlay uses this as the starting inventory for each SKU.
-- NOTE: These values are synthetic and calibrated to produce a week-9
-- stockout story for CHP-0001.  Actual timing will vary with scan_data
-- velocities; see HANDOFF.md calibration note.
-- ---------------------------------------------------------------
CREATE TABLE IF NOT EXISTS sku_inventory (
    sku           TEXT PRIMARY KEY,
    as_of_date    TEXT NOT NULL,
    on_hand_cases INTEGER NOT NULL DEFAULT 0,
    notes         TEXT
);
