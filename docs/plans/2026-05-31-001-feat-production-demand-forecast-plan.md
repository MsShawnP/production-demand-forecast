---
title: "feat: Build Production Demand Forecast App"
type: feat
status: active
date: 2026-05-31
origin: docs/brainstorms/2026-05-31-production-demand-forecast-requirements.md
---

# feat: Build Production Demand Forecast App

## Summary

Greenfield Dash + Plotly app scaffolded from the `competitive-shelf-intelligence` pattern, extended with a new `app/analytics/` package implementing OOS correction, rolling forecast, and capacity overlay. A new co-packer schema is designed and seeded into the Cinderhaven Postgres SSOT. The S&OP view, scenario controls, doom loop narrative, and dual Excel/PDF export complete the portfolio piece and deploy to Fly.io.

---

## Problem Frame

Specialty food brands using co-packers plan production reactively and run out of product because their reorder signals don't account for co-packer lead times — and their forecasts are corrupted by the very stockouts they're trying to prevent. Full problem narrative in the origin document.

See origin: `docs/brainstorms/2026-05-31-production-demand-forecast-requirements.md`

---

## Requirements

R1–R3: OOS correction produces `true_demand` per SKU per week, correcting zero-sale authorized periods using rolling-median baseline.
R4–R5: 12-week rolling forecast per SKU built from `true_demand`.
R6: Co-packer schema seeded in Cinderhaven Postgres — co_packers, production_lines, production_schedule, sku_production_config.
R7–R9: Stockout date, decision deadline, and shared-line conflict detection per SKU.
R10–R12: S&OP view — per-SKU forward view with red flags (< 14 days) and critical conflict indicators.
R13–R15: Scenario controls — promo lift, retailer doors, lead-time slip — server-side recompute via Dash callbacks.
R16–R17: Doom loop narrative + Artisan Sauce hero case (naive ~4.2 vs corrected ~5.0 units/store/week).
R18–R19: Excel (.xlsx) and PDF (WeasyPrint) export of current scenario state.
R20: Deployed to Fly.io at a public URL.

**Origin actors:** A1 (Ops Lead / VP Ops), A2 (CEO / COO), A3 (Portfolio Viewer)
**Origin flows:** F1 (S&OP Weekly Review), F2 (Scenario Modeling), F3 (Export), F4 (Doom Loop Demo)
**Origin acceptance examples:** AE1 (deadline < 14 days → red), AE2 (shared-line conflict → critical), AE3 (scenario update → no page reload), AE4 (Artisan Sauce hero case chart)

---

## Scope Boundaries

- Multi-co-packer routing — single co-packer in v1
- Automated production ordering
- MRP / ingredient-level planning
- ML or exotic forecasting methods
- Admin UI for co-packer constraints (seeded via scripts only)
- Real brand data
- User authentication

### Deferred to Follow-Up Work

- Multi-co-packer routing (v2): separate arc once v1 ships
- Co-Packer / Production Capacity Model (#22): deeper throughput optimization in its own project

---

## Context & Research

### Relevant Code and Patterns

- `competitive-shelf-intelligence/app/db.py` — ThreadedConnectionPool keyed by PID, DEC2FLOAT adapter, 30s statement timeout, `get_conn()` context manager. Copy verbatim; no changes needed unless decimal columns are absent.
- `competitive-shelf-intelligence/app/data.py` — `Cache` instantiated at module level, `init_cache(server)` called from `run.py`. `@cache.memoize(3600)`. All query functions import `get_conn` inside the function body (prevents import-time DB connections). Every `except Exception` logs via `logger.exception()` before returning empty DataFrame — never silent swallow.
- `competitive-shelf-intelligence/app/charts.py` — `base_chart_layout()` and `add_vline_at_date()`. The `add_vline_at_date()` helper is **critical**: it works around a Plotly 6.x / pandas 3.x TypeError on `add_vline()` with Timestamps. Use it for every stockout date and decision deadline vertical line.
- `competitive-shelf-intelligence/app/constants.py` — All 26 Lailara Design System color tokens. SG-55 (`#ee8a2a`) and Tokyo-40 (`#b82d4a`) are not yet named constants; add them if needed for warning/risk colors.
- `competitive-shelf-intelligence/app/run.py` — Init order is load-order-sensitive: `load_dotenv → Dash → init_cache(server) → app.layout → register_callbacks(app) → Flask route decorators`. Out-of-order init causes `@cache.memoize` failures at import time.
- `competitive-shelf-intelligence/app/tabs/oos_tracker.py` — Tab layout pattern: `TAB_ID`, `layout()`, `register_callbacks(app)`. `dcc.Store` as initial trigger. Input allowlist validation.
- `competitive-shelf-intelligence/Dockerfile` and `fly.toml` — Use `python:3.13-slim` base (not Playwright). Increase gunicorn workers to 2–4 (no Playwright constraint). `/health` route tests live DB connectivity.

### Institutional Learnings

- **OOS guard clause bug** (`competitive-shelf-intelligence/docs/solutions/logic-errors/price-convention-mismatch-oos-guard-clause-2026-05-28.md`): Build OOS detection so the "authorization signal absent" case fires as potential OOS, not as in-stock. Test the branch where `units_sold = 0` AND the `distribution_log` row is NULL — that case must be handled explicitly.
- **INNER JOIN silent drop** (`sku-rationalization-framework/docs/solutions/logic-errors/inner-join-silent-sku-exclusion-2026-05-28.md`): Anchor all demand queries on the SKU spine with LEFT JOINs. Assert that output SKU count equals input SKU count after every data pull. Include a fixture SKU with a gap week in every test suite touching demand data.
- **Silent exception swallow**: Every `except Exception` in `app/data.py` and `app/analytics/` must call `logger.exception()` before returning empty/fallback. Silent fallback makes OOS misclassification invisible in production.

### External References

- `statsmodels.tsa.seasonal.STL` — LOESS-based seasonal decomposition used for the 12-week rolling forecast. Parameters: `period=52`, `robust=True` (handles residual outliers from remaining stockout noise).
- WeasyPrint — HTML/CSS → PDF. Reuses Lailara Design System CSS for the PDF layout. Adds ~50 MB to Docker image but avoids rebuilding the layout from scratch.
- openpyxl — already in `competitive-shelf-intelligence/requirements.txt`. Excel export carries over directly.

---

## Key Technical Decisions

- **Separate `app/analytics/` package**: OOS correction, forecast, and capacity logic are pure Python functions with no Dash dependency. Tested in isolation via `tests/analytics/`. `app/data.py` calls into `app/analytics/` and wraps results in cached DataFrames. This is the testability decision: if the analytics logic lived inside `data.py`, unit tests would require mocking the cache and Postgres pool.
- **Seasonal index for OOS correction (simple multiplicative, not STL)**: For the OOS correction step, a store-level multiplicative seasonal index is used (each week-of-year's mean velocity / overall mean, computed over non-OOS, non-promo weeks). STL is more powerful but adds statsmodels as a correction-step dependency — the index approach is sufficient for a 6-week correction window and is more transparent to explain.
- **STL for forward forecast**: The 12-week rolling forecast uses `statsmodels.tsa.seasonal.STL` on the trailing 52 weeks of `true_demand`. Trend projected forward + seasonal component for the forecast window. Clipped to ≥ 0.
- **WeasyPrint for PDF**: HTML → PDF reuses Lailara Design System CSS. Avoids rebuilding layout. Accepted trade-off: ~50 MB Docker image addition.
- **Aggregate channels excluded from OOS correction**: UNFI-AGG, KEHE-AGG, DTC-AGG have synthetic lumpy 4–6 week bulk cycles — rolling-median correction misclassifies these as OOS. These channels are shown in velocity reporting but excluded from `true_demand` computation and the forecast.
- **Co-packer schema in Postgres**: Four tables (`co_packers`, `production_lines`, `production_schedule`, `sku_production_config`). Designed to be reusable across future Cinderhaven projects. Seeded via `db/seed_copack.py`.
- **Scenario recompute is server-side**: Scenario controls (promo lift, retailer doors, lead-time slip) trigger a Dash callback that calls `app/data.py` functions with scenario parameters. No client-side forecast logic. Cached at 60s TTL per scenario parameter combination.

---

## Open Questions

### Resolved During Planning

- **Seasonal decomposition method**: Simple multiplicative seasonal index for OOS correction; STL for forward forecast. See Key Technical Decisions.
- **PDF library**: WeasyPrint. See Key Technical Decisions.
- **Aggregate channel OOS handling**: Excluded from `true_demand`. See Key Technical Decisions.
- **Co-packer constraints to seed**: Cinderhaven uses one co-packer. Artisan Sauces line lead time: 10 weeks, min run: 500 cases. Condiments line: 8 weeks, min run: 300 cases. Pantry line: 12 weeks, min run: 400 cases. Shared line: Artisan Sauces top 5 SKUs and Specialty Condiments top 5 SKUs share one line. Current production schedule: ~40% of capacity booked through week 6 from today. These constraints are designed to produce non-trivial decision deadlines and at least one shared-line conflict in the demo.

### Deferred to Implementation

- **CHP-0001 as hero case**: Verify that the Artisan Sauce February OOS event in `scan_data` falls on CHP-0001 (Roasted Tomato Basil Marinara) at Walmart stores. If not, identify the correct SKU/store combination that shows the February event before building U9.
- **STL parameter tuning**: `period=52` and `robust=True` are the starting point. If the decomposition produces poor trend fits on short-history SKUs (< 52 weeks), fall back to a 12-week rolling mean as the trend component.
- **WeasyPrint CSS isolation**: The PDF export renders a standalone HTML template (not the live Dash app). The template must include inline CSS; the full Dash stylesheet may not be available in the WeasyPrint context. Verify during U11 implementation.
- **Fly.io Postgres connection string**: Requires the `DATABASE_URL` secret from the Cinderhaven platform Fly.io app. Confirm the secret name and value at deployment time.

---

## Output Structure

```
production-demand-forecast/
├── app/
│   ├── __init__.py
│   ├── run.py                   # Dash entry point, Flask server, /health route
│   ├── db.py                    # Postgres connection pool (copied from scaffold)
│   ├── data.py                  # Query + caching layer; calls app/analytics/
│   ├── layout.py                # Top-level dcc.Tabs layout
│   ├── constants.py             # Lailara Design System color tokens
│   ├── charts.py                # Plotly helpers: base_chart_layout, add_vline_at_date
│   ├── callbacks.py             # Thin dispatcher: register_callbacks per tab
│   ├── components.py            # Shared UI: DarkCard, empty_state, red_flag_badge
│   ├── analytics/
│   │   ├── __init__.py
│   │   ├── oos_correction.py    # detect_oos_periods(), correct_velocity()
│   │   ├── forecast.py          # build_rolling_forecast() — STL + 12-week projection
│   │   └── capacity.py          # compute_stockout_date(), compute_decision_deadline(),
│   │                            #   detect_shared_line_conflicts()
│   └── tabs/
│       ├── sop_view.py          # S&OP per-SKU view, red flags, conflict indicators
│       ├── scenario_controls.py # Promo lift / doors / lead-time-slip inputs
│       └── doom_loop.py         # Hero case chart + doom loop narrative
├── db/
│   ├── schema_copack.sql        # Co-packer schema DDL (CREATE TABLE IF NOT EXISTS)
│   └── seed_copack.py           # Synthetic seeding script
├── tests/
│   ├── analytics/
│   │   ├── test_oos_correction.py
│   │   ├── test_forecast.py
│   │   └── test_capacity.py
│   └── test_data.py
├── Dockerfile
├── fly.toml
├── requirements.txt
├── pyproject.toml               # ruff config, pytest config
└── .env.example
```

---

## High-Level Technical Design

> *This illustrates the intended approach and is directional guidance for review, not implementation specification. The implementing agent should treat it as context, not code to reproduce.*

```mermaid
flowchart TD
    PG[(Cinderhaven\nPostgres)]

    subgraph analytics["app/analytics/"]
        OOS["oos_correction.py\ndetect_oos_periods()\ncorrect_velocity()\n→ true_demand df"]
        FC["forecast.py\nbuild_rolling_forecast()\nSTL on trailing 52wks\n→ forecast_12wk df"]
        CAP["capacity.py\ncompute_stockout_date()\ncompute_decision_deadline()\ndetect_conflicts()\n→ sop_summary df"]
    end

    subgraph data["app/data.py (cached)"]
        D1["get_true_demand()\n@memoize 1h"]
        D2["get_forecast(scenario)\n@memoize 60s"]
        D3["get_sop_summary(scenario)\n@memoize 60s"]
    end

    subgraph tabs["app/tabs/"]
        T1["sop_view.py\nper-SKU table\nred flags + conflicts"]
        T2["scenario_controls.py\ninputs → dcc.Store\n→ callbacks update T1"]
        T3["doom_loop.py\nhero case chart\nnaive vs corrected"]
    end

    EX["Export\n.xlsx openpyxl\n.pdf WeasyPrint"]

    PG -- scan_data\ndistribution_log --> OOS
    PG -- product_master\npromotions --> OOS
    OOS --> D1
    D1 --> FC
    FC --> D2
    PG -- sku_production_config\nproduction_schedule --> CAP
    D2 --> CAP
    CAP --> D3
    D3 --> T1
    D3 --> T2
    D1 --> T3
    D3 --> EX
```

The critical path is left-to-right: Postgres → OOS correction → `true_demand` → forecast → capacity overlay → `sop_summary` → views + export. Scenario parameters enter at the `get_forecast()` call and flow through to `get_sop_summary()`. The S&OP view and scenario controls share the same `sop_summary` DataFrame; scenario control changes invalidate the 60s cache and trigger a server-side recompute.

---

## Implementation Units

### Phase 1 — Foundation

---

### U1. App scaffold and environment setup

**Goal:** Initialize the Dash app skeleton by copying proven patterns from `competitive-shelf-intelligence`, set up Postgres connection, caching, and dev environment.

**Requirements:** R20 (deploy foundation), all R1–R19 depend on this scaffold.

**Dependencies:** None

**Files:**
- Create: `app/__init__.py`, `app/run.py`, `app/db.py`, `app/data.py` (stub), `app/layout.py` (stub), `app/constants.py`, `app/charts.py`, `app/callbacks.py` (stub), `app/components.py` (stub)
- Create: `requirements.txt`, `pyproject.toml`, `.env.example`
- Modify: `PLAN.md` (update stack from FastAPI/HTML to Dash/Plotly)

**Approach:**
- Copy `db.py` verbatim from `competitive-shelf-intelligence/app/db.py`. No functional changes — pool, DEC2FLOAT, statement timeout, get_conn() context manager.
- Copy `constants.py`, `charts.py` from `competitive-shelf-intelligence`. Add Singapore orange (`SG_ORANGE = "#ee8a2a"`) and Tokyo rose (`TOKYO_ROSE = "#b82d4a"`) constants to `constants.py`.
- `app/run.py` follows the exact init order: `load_dotenv → Dash → init_cache(server) → layout → callbacks → Flask routes`. Include the `/health` route (SELECT 1 via get_conn).
- `app/data.py` stub: import cache, define `init_cache()`, one placeholder query function.
- `requirements.txt`: pin Dash >=3.0,<4.0, Plotly >=5.18,<7.0, pandas >=2.0,<3.0, psycopg2-binary >=2.9,<3.0, flask-caching >=2.1,<3.0, gunicorn >=21.0,<23.0, openpyxl >=3.1,<4.0, statsmodels >=0.14,<1.0, WeasyPrint >=61.0,<62.0, python-dotenv >=1.0,<2.0.
- `pyproject.toml`: ruff target py313, line-length 100, pytest config pointing to `tests/`.
- `.env.example`: DATABASE_URL, FLASK_SECRET_KEY, FLASK_DEBUG, CACHE_DIR.

**Patterns to follow:**
- `competitive-shelf-intelligence/app/db.py`
- `competitive-shelf-intelligence/app/run.py`
- `competitive-shelf-intelligence/app/constants.py`
- `competitive-shelf-intelligence/app/charts.py`

**Test scenarios:**
- Happy path: `python -c "from app.db import get_conn"` succeeds when DATABASE_URL is set.
- Happy path: `/health` route returns 200 and `{"status": "ok"}` when Postgres is reachable.
- Error path: `/health` returns 503 when DATABASE_URL points to an unreachable host.
- Test expectation: remaining stub files have no behavioral tests yet — coverage added as each module is built.

**Verification:**
- `flask run` (or `gunicorn app.run:server`) starts without import errors.
- `/health` returns 200 against the Cinderhaven dev Postgres.
- `ruff check app/` passes with zero violations.

---

### U2. Co-packer schema design and seeding

**Goal:** Extend the Cinderhaven Postgres SSOT with a realistic, reusable co-packer capacity schema and seed it with synthetic data that produces non-trivial decision deadlines and at least one shared-line conflict in the demo.

**Requirements:** R6

**Dependencies:** U1 (Postgres connection available)

**Files:**
- Create: `db/schema_copack.sql`
- Create: `db/seed_copack.py`

**Approach:**

Four tables (all `CREATE TABLE IF NOT EXISTS`, safe to re-run):

- `co_packers(co_packer_id, name, location, notes)` — one row: "Midwest Production Partners, LLC"
- `production_lines(line_id, co_packer_id, line_name, product_line_affinity)` — two rows: Line A (Artisan Sauces + top Condiments, shared), Line B (remaining Condiments + Pantry, dedicated)
- `sku_production_config(sku, line_id, lead_time_weeks, min_run_cases, notes)` — one row per SKU. Artisan Sauces: 10-week lead, 500-case min. Condiments: 8-week lead, 300-case min. Pantry: 12-week lead, 400-case min.
- `production_schedule(run_id, sku, line_id, scheduled_week, quantity_cases, status)` — ~30 rows of synthetic booked runs. ~40% of Line A capacity booked through week 6 from a reference date of 2025-11-01 (the "today" for the demo). Runs are distributed so that CHP-0001 (Artisan Sauce top SKU) has a run booked for week 4 but none between weeks 8–14, creating the story: demo shows that at true demand (~5.0 units/store/week), the next unbooked window produces a stockout in week 9.

Seeding script (`db/seed_copack.py`): runs DDL then inserts data via psycopg2. Idempotent — uses `ON CONFLICT DO NOTHING` or truncate-and-reinsert. Reads `DATABASE_URL` from environment.

**Patterns to follow:**
- Cinderhaven schema conventions from `archived/cinderhaven-data/scripts/` — TEXT PKs matching existing SKU IDs, ISO date strings for date columns.

**Test scenarios:**
- Happy path: running `seed_copack.py` twice produces the same row count both times (idempotent).
- Happy path: every SKU in `product_master` has exactly one row in `sku_production_config` after seeding.
- Edge case: seeding against an already-seeded DB produces no duplicates and no errors.
- Integration: `SELECT s.sku, c.lead_time_weeks FROM sku_production_config c JOIN product_master p ON c.sku = p.sku` returns 50 rows (all SKUs have co-packer config).

**Verification:**
- `psql $DATABASE_URL -c "SELECT COUNT(*) FROM sku_production_config"` returns 50.
- `psql $DATABASE_URL -c "SELECT COUNT(*) FROM production_schedule"` returns ~30.
- At least two SKUs share the same `line_id` on Line A with overlapping `scheduled_week` ranges.

---

### Phase 2 — Analytics Core

---

### U3. OOS correction module

**Goal:** Implement `app/analytics/oos_correction.py` — detect true OOS periods using `scan_data` + `distribution_log`, then replace zero-sale authorized windows with a rolling-median baseline adjusted for a simple multiplicative seasonal index. Output: `true_demand` column per (SKU, store, week).

**Requirements:** R1, R2, R3

**Dependencies:** U1, U2

**Files:**
- Create: `app/analytics/__init__.py`
- Create: `app/analytics/oos_correction.py`
- Create: `tests/analytics/test_oos_correction.py`

**Approach:**

Two public functions:

`detect_oos_periods(df: DataFrame) -> DataFrame` — adds a boolean `is_oos` column. An OOS period is a row where `units_sold == 0` AND the SKU was authorized at that store (i.e., a matching `distribution_log` record exists with `authorized_date <= week_ending AND (deauthorized_date IS NULL OR deauthorized_date > week_ending)`). Rows with `units_sold == 0` but no authorization record are NOT flagged as OOS — they are un-authorized periods. Aggregate channels (`store_id` ending in `-AGG`) are excluded: `is_oos = False` for all aggregate channel rows.

`correct_velocity(df: DataFrame) -> DataFrame` — adds `true_demand` column. For non-OOS rows: `true_demand = units_sold`. For OOS rows: `true_demand = rolling_median * seasonal_index`.

Rolling median: median of `units_sold` from the 3 non-OOS weeks immediately before and 3 non-OOS weeks immediately after the OOS block, for the same (SKU, store) combination.

Seasonal index: for each SKU, compute the mean `units_sold` for each ISO week-of-year across all non-OOS, non-promotional weeks, divided by the SKU's overall non-OOS mean. Applied as a multiplier to the rolling median for the OOS correction weeks.

Edge cases:
- Fewer than 3 pre- or post-stockout weeks available → use what is available (minimum 1 week on each side).
- Back-to-back OOS blocks → use the non-OOS weeks adjacent to the combined block.
- All historical weeks are OOS for a (SKU, store) → `true_demand = 0` with a flag `insufficient_data = True`.

**Execution note:** Implement `detect_oos_periods()` test-first — the detection logic has a subtle guard condition (authorized-but-zero vs. unauthorized-and-zero) that regression tests must lock in before the correction step is built.

**Patterns to follow:**
- Seasonal index pattern: pandas `groupby(["sku", week_of_year]).mean()` / `groupby("sku").mean()`.
- Institutional learning: every `except Exception` logs before returning empty DataFrame (see Context & Research).

**Test scenarios:**
- Happy path: SKU with a known 2-week OOS block → `true_demand` > 0 for those 2 weeks, `units_sold` unchanged.
- Happy path: SKU with no OOS periods → `true_demand == units_sold` for all rows.
- Edge case: `units_sold == 0` with no `distribution_log` row (unauthorized) → `is_oos = False`, `true_demand = 0`.
- Edge case: OOS at the very start of the data window (0 pre-stockout weeks) → uses post-stockout weeks only, no crash.
- Edge case: consecutive OOS blocks with no non-OOS weeks between them → each block uses the nearest available non-OOS boundary on each side.
- Edge case: aggregate channel (UNFI-AGG) with zero units_sold → `is_oos = False` regardless of distribution_log.
- Covers AE4: CHP-0001 Artisan Sauce at Walmart stores — February 2025 OOS window → corrected `true_demand` is ~18% higher than `units_sold` mean for those weeks.
- Integration: `detect_oos_periods()` output has same row count as input (no rows dropped).

**Verification:**
- `pytest tests/analytics/test_oos_correction.py -v` passes.
- For the CHP-0001 February OOS window at Walmart: mean `true_demand` during OOS weeks is within 15–25% above the pre-OOS mean `units_sold` (the ~18% correction from the brainstorm doc).

---

### U4. Rolling forecast module

**Goal:** Implement `app/analytics/forecast.py` — build a 12-week rolling forward demand forecast per SKU from `true_demand`, using STL decomposition on the trailing 52 weeks.

**Requirements:** R4, R5

**Dependencies:** U3

**Files:**
- Create: `app/analytics/forecast.py`
- Create: `tests/analytics/test_forecast.py`

**Approach:**

One public function: `build_rolling_forecast(true_demand_df: DataFrame, forecast_from_week: str, n_weeks: int = 12) -> DataFrame`

Returns a DataFrame with columns: `(sku, week_ending, forecast_units, is_projected)`. `is_projected = True` for the 12 forward weeks; historical fitted values may also be included for chart display.

Per SKU:
1. Aggregate `true_demand` to weekly SKU-level totals (sum across stores — weighted by store count and distribution flag).
2. Extract trailing 52 weeks ending at `forecast_from_week`.
3. Apply `statsmodels.tsa.seasonal.STL(series, period=52, robust=True).fit()`.
4. Project trend forward using the last trend value + mean trend delta over trailing 4 weeks. Add the seasonal component for the corresponding week-of-year from the decomposed seasonal series.
5. Clip to ≥ 0.
6. If fewer than 52 weeks of `true_demand` are available for a SKU → fall back to 12-week rolling mean with no seasonal adjustment. Flag these SKUs with `forecast_method = "rolling_mean_fallback"`.
7. SKUs with all `true_demand = 0` across their history → `forecast_units = 0`, `forecast_method = "insufficient_data"`.

Scenario inputs (passed as parameters): `promo_lift_pct` (default 0.0), `new_retailer_doors` (default 0), `new_doors_velocity_factor` (per-store velocity assumption for new doors, defaults to median store velocity for that SKU).

**Patterns to follow:**
- statsmodels STL: `from statsmodels.tsa.seasonal import STL`

**Test scenarios:**
- Happy path: 52 weeks of true_demand → forecast returns 12 rows of positive values per SKU.
- Happy path: seasonal pattern visible — a SKU with known Q4 uplift has higher forecast for weeks falling in Q4 than weeks falling in Q1.
- Edge case: SKU with 30 weeks of history (< 52) → falls back to rolling mean, `forecast_method = "rolling_mean_fallback"`, no crash.
- Edge case: `new_retailer_doors = 200` → forecast increases (more doors = more demand).
- Edge case: `promo_lift_pct = 0.3` → affected weeks show 30% lift in forecast.
- Edge case: all-zero `true_demand` → returns `insufficient_data` flag, `forecast_units = 0`.
- Integration: forecast built from `true_demand` output of `correct_velocity()` on real Cinderhaven scan_data returns plausible velocity ranges (1–50 units/store/week for Artisan Sauces top SKUs).

**Verification:**
- `pytest tests/analytics/test_forecast.py -v` passes.
- CHP-0001 forecast at baseline scenario (no promo, no new doors) shows ~5.0 units/store/week × store count for the trailing trend — consistent with the OOS-corrected baseline from U3.

---

### U5. Capacity overlay and decision deadline module

**Goal:** Implement `app/analytics/capacity.py` — join the rolling forecast against co-packer constraints and current production schedule to produce per-SKU stockout date, decision deadline, and shared-line conflict flags.

**Requirements:** R7, R8, R9

**Dependencies:** U2, U4

**Files:**
- Create: `app/analytics/capacity.py`
- Create: `tests/analytics/test_capacity.py`

**Approach:**

Three public functions:

`compute_stockout_date(forecast_df, inventory_df, schedule_df) -> DataFrame` — For each SKU: starting from current inventory, subtract weekly forecast demand, add scheduled production for each week. The week where running inventory first crosses zero is `stockout_date`. If inventory never reaches zero in the 12-week window → `stockout_date = None` (no stockout projected).

`compute_decision_deadline(sop_df, sku_config_df) -> DataFrame` — For each SKU with a `stockout_date`: `decision_deadline = stockout_date - lead_time_weeks`. If `decision_deadline` is in the past → `decision_deadline = "PAST DUE"` flag. If `stockout_date = None` → `decision_deadline = None`.

`detect_shared_line_conflicts(sop_df, sku_config_df) -> DataFrame` — For each production line, collect all SKUs on that line that have a non-None `decision_deadline` within the 12-week horizon. If two or more SKUs on the same line have `decision_deadline` within the same 4-week window → both are flagged `shared_line_conflict = True`.

Returns a combined S&OP summary DataFrame: `(sku, product_name, product_line, current_inventory, weekly_forecast_mean, stockout_date, decision_deadline, days_until_deadline, deadline_flag, shared_line_conflict, conflict_line_id, conflict_skus)`.

`deadline_flag` values: `"PAST_DUE"`, `"CRITICAL"` (< 14 days), `"WARNING"` (14–28 days), `"OK"` (> 28 days or no stockout).

**Test scenarios:**
- Covers AE1: SKU with `days_until_deadline = 10` → `deadline_flag = "CRITICAL"`.
- Covers AE2: SKU A and SKU B on Line A with `decision_deadline` in week 3 → both `shared_line_conflict = True`.
- Happy path: SKU with sufficient inventory + scheduled production → `stockout_date = None`, `deadline_flag = "OK"`.
- Happy path: SKU with PAST_DUE deadline → `deadline_flag = "PAST_DUE"`, `days_until_deadline` is negative.
- Edge case: `stockout_date` falls exactly on the last week of the 12-week horizon → treated as a projected stockout.
- Edge case: shared-line conflict where one SKU has no deadline → no false conflict flagged.
- Integration: `compute_stockout_date()` output row count equals input SKU count (LEFT JOIN spine, no silent drops).

**Verification:**
- `pytest tests/analytics/test_capacity.py -v` passes.
- Cinderhaven Artisan Sauce top SKU (CHP-0001) at demo scenario shows `stockout_date` in week 9 and `decision_deadline` in week 3 (per the brief's headline).
- At least one `shared_line_conflict = True` pair appears in the Cinderhaven demo data.

---

### Phase 3 — App Views

---

### U6. Data query layer

**Goal:** Implement `app/data.py` fully — expose OOS-corrected demand, forecast, and S&OP summary as cached DataFrames. Wire scenario parameters as cache keys.

**Requirements:** R1–R15 (data layer underpins all view requirements)

**Dependencies:** U1, U3, U4, U5

**Files:**
- Modify: `app/data.py` (replace stub with full implementation)
- Create: `tests/test_data.py`

**Approach:**

Key public functions (all `@cache.memoize`):

- `get_scan_data(sku=None) -> DataFrame` — raw scan_data from Postgres, LEFT JOIN distribution_log authorization flag. 1h cache. LEFT JOIN from product_master spine (assert SKU count = 50 after pull).
- `get_true_demand(sku=None) -> DataFrame` — calls `app.analytics.oos_correction.correct_velocity(get_scan_data())`. 1h cache.
- `get_forecast(promo_lift_pct=0.0, new_doors=0, lead_time_slip_weeks=0) -> DataFrame` — calls `app.analytics.forecast.build_rolling_forecast(get_true_demand(), ...)`. 60s cache (scenario-keyed).
- `get_sop_summary(promo_lift_pct=0.0, new_doors=0, lead_time_slip_weeks=0) -> DataFrame` — calls capacity module on `get_forecast(...)`. 60s cache.

Scenario parameter validation: clamp promo_lift_pct to [0, 1.0], new_doors to [0, 5000], lead_time_slip_weeks to [0, 12] before calling analytics functions. Log a warning for out-of-range inputs.

Every query function wraps Postgres access in `try/except Exception: logger.exception(...); return pd.DataFrame()`.

**Patterns to follow:**
- `competitive-shelf-intelligence/app/data.py` — cache init, memoize pattern, `from app.db import get_conn` inside function body, LEFT JOIN from spine.
- Institutional learning: assert row count == spine count after every pull.

**Test scenarios:**
- Happy path: `get_sop_summary()` returns 50 rows (one per SKU), no nulls in `deadline_flag`.
- Edge case: `get_scan_data()` with Postgres unavailable → returns empty DataFrame, logs exception.
- Edge case: scenario parameters out of range → clamped values used, no crash.
- Integration: `get_sop_summary(promo_lift_pct=0.3)` returns higher mean forecast than `get_sop_summary()` baseline for at least one SKU.

**Verification:**
- `pytest tests/test_data.py -v` passes (using a test Postgres connection or a fixture DataFrame for analytics calls).
- `get_sop_summary()` returns 50 rows on the Cinderhaven dev database.

---

### U7. S&OP view tab

**Goal:** Build `app/tabs/sop_view.py` — the primary per-SKU forward view. Red flags for deadline < 14 days, critical conflict indicator, scrollable SKU table, and a detail chart for any selected SKU.

**Requirements:** R10, R11, R12 (F1 flow, AE1, AE2)

**Dependencies:** U6

**Files:**
- Create: `app/tabs/sop_view.py`
- Modify: `app/layout.py` (add S&OP tab)
- Modify: `app/callbacks.py` (register sop_view callbacks)

**Approach:**

Tab structure follows `oos_tracker.py` pattern: `TAB_ID = "sop-view"`, `layout()` returns `html.Div`, `register_callbacks(app)` wires all callbacks.

Layout sections:
1. Summary row — 3 KPI chips: total SKUs, SKUs needing action (deadline < 28 days), SKUs with critical conflicts.
2. SKU table — `dash_ag_grid` component (already in requirements). Columns: SKU, Product Name, Product Line, Forecast (mean weekly), Stockout Week, Decision Deadline, Days Until Deadline, Conflict. `deadline_flag` drives row conditional formatting (red background for CRITICAL/PAST_DUE, orange for WARNING). Conflict column shows a "⚠ Shared Line" badge in red for conflicted SKUs.
3. SKU detail panel — appears on row click. Shows inventory runway chart (stacked bar: current inventory + scheduled production by week, line overlay for weekly forecast demand). Uses `add_vline_at_date()` for stockout date (red) and decision deadline (orange dashed). Doom loop framing text appears below: "This SKU's February stockout suppressed the baseline velocity that was feeding its forecast. The corrected forecast raises the demand estimate by X%."

Callback wiring:
- Table row click → update detail panel chart (no page reload).
- Scenario `dcc.Store` change (from scenario_controls tab) → refresh table data (calls `get_sop_summary(scenario_params)`).

**Patterns to follow:**
- `competitive-shelf-intelligence/app/tabs/oos_tracker.py` — tab structure, ag-grid pattern, callback wiring.
- `competitive-shelf-intelligence/app/charts.py` — `add_vline_at_date()` for deadline/stockout lines.

**Test scenarios:**
- Covers AE1: Given `get_sop_summary()` returns a SKU with `days_until_deadline = 10`, the ag-grid row for that SKU has red conditional formatting.
- Covers AE2: Given a SKU with `shared_line_conflict = True`, the Conflict column displays the conflict badge.
- Covers AE3: Given scenario controls update `dcc.Store`, the table refreshes without a full Dash page reload (callback fires, table rows update).
- Happy path: clicking a table row populates the detail panel with the inventory runway chart.
- Edge case: all 50 SKUs have `deadline_flag = "OK"` → summary KPI chips show 0 SKUs needing action.

**Verification:**
- S&OP view renders with all 50 Cinderhaven SKUs.
- At least one SKU row shows red formatting.
- Row click loads the detail chart with stockout and deadline vertical lines.

---

### U8. Scenario controls tab

**Goal:** Build `app/tabs/scenario_controls.py` — promo lift %, new retailer door count, lead-time slip inputs that write to a shared `dcc.Store` and trigger S&OP view recompute.

**Requirements:** R13, R14, R15 (F2 flow, AE3)

**Dependencies:** U7

**Files:**
- Create: `app/tabs/scenario_controls.py`
- Modify: `app/layout.py` (add scenario tab, add `dcc.Store(id="scenario-params")`)
- Modify: `app/callbacks.py`

**Approach:**

Tab layout: three control groups.
1. Promo Lift — slider (0–50%) + numeric input. Label: "Promo demand lift for [SKU selector] during [week range]." Defaults to all SKUs.
2. New Retailer Doors — numeric input (0–5000). Label: "Additional retail doors launching in week 1." Adds demand at median per-door velocity.
3. Lead-Time Slip — slider (0–12 weeks). Label: "Co-packer lead time increases by N weeks."

"Apply Scenario" button writes `{promo_lift_pct, new_doors, lead_time_slip_weeks}` to `dcc.Store(id="scenario-params")`. Store update triggers S&OP view callback to call `get_sop_summary(scenario_params)`.

"Reset to Baseline" button sets all inputs to 0 and clears the store.

Scenario state is displayed as a summary chip above the S&OP table: "Scenario: +30% promo lift, 200 new doors, +0 lead-time weeks."

Input validation at callback level: reject promo_lift > 1.0 (100%), negative values for doors or lead-time. Display an inline validation message, do not write to store.

**Test scenarios:**
- Covers AE3: slider set to +30% promo lift → store update → S&OP view callback fires → table data refreshes without full page reload.
- Happy path: "Reset to Baseline" sets all inputs to 0 and the scenario chip reads "Baseline."
- Error path: promo_lift set to 150% → inline validation message shown, store not updated.
- Edge case: all three inputs at maximum (50% + 5000 doors + 12 weeks) → `get_sop_summary()` called with clamped values, no server error.

**Verification:**
- Adjusting any control and clicking "Apply" updates the S&OP table within one server round-trip.
- Scenario summary chip reflects active scenario parameters.

---

### U9. Doom loop narrative and hero case

**Goal:** Build `app/tabs/doom_loop.py` — the portfolio teaching tool. Shows the doom loop mechanism as narrative text and renders the Artisan Sauce hero case chart (naive vs OOS-corrected forecast with February OOS window marked).

**Requirements:** R16, R17 (F4 flow, AE4)

**Dependencies:** U3, U6

**Files:**
- Create: `app/tabs/doom_loop.py`
- Modify: `app/layout.py`
- Modify: `app/callbacks.py`

**Approach:**

Layout: two sections.

Section 1 — "The Doom Loop" narrative. Styled prose using the Economist voice from CLAUDE.md. Four short paragraphs matching the brief's before/after structure: reactive planning → lead time gap → stockout → corrupted forecast → repeat. Ends with: "The fix is not a better forecast. It's correcting the data before forecasting."

Section 2 — Hero case chart. For CHP-0001 (Artisan Sauce top SKU) at Walmart:
- Two line traces: "Observed velocity" (raw `units_sold` per week) and "True demand" (`true_demand` after OOS correction).
- February 2025 OOS window highlighted as a shaded region (or via `add_vline_at_date()` markers at start and end).
- Annotation: "Feb stockout: 11 days. Observed velocity: 4.2 units/store/week. True demand: 5.0 units/store/week (+18%)."
- Verify the correct SKU/store for the February OOS event before building — see Deferred to Implementation.
- Below the chart: the "Before / After" decision story from the brief. Formatted as two callout boxes (dark card component from `app/components.py`).

**Patterns to follow:**
- `add_vline_at_date()` from `app/charts.py` for OOS window markers.
- Dark callout card tokens from `app/constants.py` (CARD_BG = `#1a1a1a`, etc.).

**Test scenarios:**
- Covers AE4: hero case chart renders with two line traces; the February OOS window is visually marked; the "True demand" trace is higher than "Observed velocity" during the OOS weeks.
- Happy path: narrative prose renders without truncation on mobile (640px breakpoint).
- Edge case: if the February OOS event for CHP-0001 is not found in `scan_data` → chart renders a fallback message ("Demo case not found — run the data seeding script") rather than crashing.

**Verification:**
- Doom loop tab loads and shows both narrative and hero case chart.
- "True demand" line is visibly above "Observed velocity" line during the February window.
- Chart annotations match the ~4.2 vs ~5.0 units/store/week values from the brainstorm doc.

---

### Phase 4 — Export and Deployment

---

### U10. Excel export

**Goal:** Wire a "Download MPS Workbook" button that exports the current S&OP summary (reflecting active scenario) as a formatted `.xlsx` file.

**Requirements:** R18 (F3 flow)

**Dependencies:** U7, U8

**Files:**
- Modify: `app/tabs/sop_view.py` (add export button and callback)
- Modify: `app/data.py` (add `export_sop_excel()` helper)

**Approach:**

Download button placed below the S&OP table. Wired via `dcc.Download` + `dcc.Store` pattern.

Workbook structure (openpyxl):
- Sheet 1: "Production Decision Brief" — per-SKU rows with columns: SKU, Product Name, Product Line, Mean Weekly Forecast (units), Current Inventory (cases), Stockout Week, Decision Deadline, Days Until Deadline, Action Flag, Shared Line Conflict. Header row styled with Chicago navy fill, white text. CRITICAL rows highlighted red, WARNING rows highlighted orange.
- Sheet 2: "Scenario Parameters" — records the scenario inputs used to generate this export (promo_lift_pct, new_doors, lead_time_slip_weeks, generated_at timestamp).
- Footer note on Sheet 1: "Generated by Lailara LLC Production Demand Forecast. Data: Cinderhaven Provisions LLC (synthetic). Date: [generated_at]."

**Patterns to follow:**
- openpyxl already in requirements. Pattern: `workbook = openpyxl.Workbook()`, `ws = wb.active`, cell styling via `PatternFill` and `Font`.

**Test scenarios:**
- Happy path: clicking "Download" triggers file download with `.xlsx` extension.
- Happy path: downloaded workbook contains two sheets with expected column headers.
- Happy path: CRITICAL rows have red fill in the exported workbook.
- Edge case: scenario parameters at non-default values → Sheet 2 records the correct parameter values.

**Verification:**
- Download button triggers `dcc.Download` with a valid `.xlsx` file.
- Workbook opens in Excel/LibreOffice without errors.
- Sheet 1 has 50 rows (one per SKU) plus header.

---

### U11. PDF export

**Goal:** Wire a "Download Decision Brief (PDF)" button that exports the current S&OP view and doom loop narrative as a formatted print-ready PDF using WeasyPrint.

**Requirements:** R19 (F3 flow)

**Dependencies:** U9, U10

**Files:**
- Create: `app/templates/export_pdf.html` (Jinja2 template)
- Modify: `app/tabs/sop_view.py` (add PDF download button and callback)
- Modify: `app/data.py` (add `export_sop_pdf()` helper)

**Approach:**

WeasyPrint renders a standalone Jinja2 HTML template (`app/templates/export_pdf.html`) — not the live Dash app. The template includes:
- Inline CSS using Lailara Design System tokens (Canvas background, Chicago navy, HK teal, Source Sans 3 fallbacks).
- Title section: "Production Decision Brief — [date]" in Playfair Display (or serif fallback).
- Per-SKU decision table: same columns as Excel export, with color-coded action flags.
- "Doom Loop" section: condensed narrative (2 paragraphs) + the hero case chart embedded as an SVG string (exported from Plotly via `fig.to_image(format="svg")`).
- Footer: brand, date, "Data is synthetic — Cinderhaven Provisions LLC."

`export_sop_pdf(sop_df, scenario_params) -> bytes` — renders the template with Jinja2, passes result to `weasyprint.HTML(string=html_str).write_pdf()`, returns bytes.

Note (see Deferred to Implementation): Verify that WeasyPrint can render the Jinja2 template in the Fly.io container. WeasyPrint requires system fonts and may need font installation in the Dockerfile.

**Patterns to follow:**
- Lailara Design System tokens (same hex values as `app/constants.py`).

**Test scenarios:**
- Happy path: `export_sop_pdf()` returns non-empty bytes with `%PDF` header.
- Happy path: rendered PDF contains the SKU count headline and at least one CRITICAL row.
- Edge case: `fig.to_image(format="svg")` fails in the Fly.io container (kaleido not installed) → chart section falls back to a placeholder text box rather than crashing.
- Integration: PDF renders in the Fly.io environment (system fonts, WeasyPrint CSS support).

**Verification:**
- PDF opens in a browser or PDF reader without errors.
- Decision table matches the active scenario state at download time.
- No WeasyPrint CSS warnings in server logs for the core layout.

---

### U12. Fly.io deployment

**Goal:** Deploy the app to Fly.io as a publicly accessible portfolio URL. Configure Postgres connection, cache volume, health check, and gunicorn workers.

**Requirements:** R20

**Dependencies:** U1–U11 (all app code complete)

**Files:**
- Create: `Dockerfile`
- Create: `fly.toml`
- Modify: `README.md` (add "How to run" section with local dev and deploy commands)

**Approach:**

`Dockerfile`: `FROM python:3.13-slim`. Install system packages needed by WeasyPrint: `libpango-1.0-0 libcairo2 libgdk-pixbuf2.0-0 libffi-dev`. `pip install -r requirements.txt`. `gunicorn --bind 0.0.0.0:8050 --workers 3 --timeout 120 app.run:server`. Non-root `appuser` (uid 1001). `/cache` volume pre-created.

`fly.toml`: `primary_region = "iad"`, `auto_stop_machines = "off"`, `min_machines_running = 1`, `/health` health check, `/cache` mount, `[[vm]] memory = "2gb" cpu_kind = "shared" cpus = 1`.

Fly.io secrets to set: `DATABASE_URL` (Cinderhaven platform Postgres connection string), `FLASK_SECRET_KEY` (random hex), `CACHE_DIR = "/cache"`.

**Test scenarios:**
- Test expectation: none — deployment is infrastructure; behavior tested by U1's /health check and the app test suite.

**Verification:**
- `fly deploy` succeeds with exit code 0.
- Public URL serves the app with a 200 response.
- `/health` returns `{"status": "ok"}` from the public URL.
- WeasyPrint PDF export works in the deployed container (system fonts present).

---

## System-Wide Impact

- **Callback graph**: Scenario `dcc.Store` is a shared signal source — both `sop_view` and `scenario_controls` tabs read from it. Adding a new tab that also depends on scenario params must register a callback on the same store, not create a parallel store.
- **Cache invalidation**: `get_true_demand()` and `get_scan_data()` are 1h TTL. Analytics functions called with scenario params are 60s TTL. If Cinderhaven `scan_data` is updated (e.g., new weeks seeded), the 1h cache must be manually cleared (restart the app or `fly machine restart`).
- **Error propagation**: Every `app/analytics/` function that encounters a computation error should return an empty DataFrame with a `computation_error` flag column rather than raising — this lets `app/data.py` detect and log the error without crashing the Dash callback.
- **LEFT JOIN invariant**: All queries from `app/data.py` anchor on the `product_master` spine (50 SKUs) via LEFT JOIN. If any query returns fewer than 50 rows, it means data is missing — log a warning and fill with `null`/zero rather than silently dropping SKUs from the S&OP view.
- **Aggregate channel exclusion**: UNFI-AGG, KEHE-AGG, DTC-AGG are excluded from OOS correction and the S&OP view. They remain in velocity reporting (e.g., if a "total velocity" chart is added). This exclusion is enforced in `detect_oos_periods()` and documented in `src/CLAUDE.md`.
- **WeasyPrint system dependencies**: The Dockerfile must install WeasyPrint's system dependencies (pango, cairo, gdk-pixbuf). Missing system packages cause WeasyPrint to fail silently on some CSS features. Test PDF export in the container early, not just locally.
- **Unchanged invariants**: The Cinderhaven Postgres SSOT tables (`scan_data`, `distribution_log`, `product_master`, `promotions`, `stores`, `orders`, `order_lines`) are read-only from this app. The only writes are the new co-packer tables created in U2.

---

## Risks & Dependencies

| Risk | Mitigation |
|------|------------|
| February OOS event may not be on CHP-0001 at Walmart | Verify in the Cinderhaven DB before building U9. If the event is on a different SKU/store, update U9's hero case. The brainstorm doc numbers (~4.2 → ~5.0 units/store/week) are directional — verify actual values from the data. |
| WeasyPrint system packages in Fly.io container | Install pango, cairo, gdk-pixbuf in Dockerfile. Test `fly ssh console` + `python -c "import weasyprint; print('ok')"` immediately after first deploy. |
| STL seasonal decomposition on short-history SKUs (< 52 weeks) | Fallback to 12-week rolling mean already specified in U4. Verify the fallback fires correctly for new/recently-launched SKUs in Cinderhaven. |
| Scan data aggregate channel lumpy cycles misidentified as OOS | Aggregate channels excluded from OOS correction in U3. Confirm exclusion is applied before the first analytics integration test. |
| Cinderhaven Postgres connection string format on Fly.io | Confirm `DATABASE_URL` secret name and format with the Cinderhaven platform app at deployment time. The standard Fly.io Postgres format is `postgres://user:pass@host:5432/db`. |
| PLAN.md stack field is stale (says FastAPI/HTML) | Update in U1 as part of scaffold setup — explicit task. |

---

## Documentation / Operational Notes

- Update `README.md` in U12 with: one-sentence project description, how to run locally (`python -m dotenv run gunicorn`), how to run tests (`pytest tests/`), how to deploy (`fly deploy`).
- Log the co-packer schema design decision to `DECISIONS.md` (U2) — the table structure is a portfolio-reusable SSOT pattern.
- The `db/seed_copack.py` seeding script must be re-run if the Cinderhaven Postgres is recreated. Document this in `README.md`.
- After the app ships, run `/ce-compound` to capture the OOS correction pattern, STL forecast pattern, WeasyPrint integration, and Dash scenario controls pattern as `docs/solutions/` entries — these are all portfolio firsts.

---

## Sources & References

- **Origin document:** [docs/brainstorms/2026-05-31-production-demand-forecast-requirements.md](docs/brainstorms/2026-05-31-production-demand-forecast-requirements.md)
- Scaffold reference: `competitive-shelf-intelligence/app/` (all modules)
- Lailara Design System: `~/projects/published/lailara-design-system/LAILARA_DESIGN_SYSTEM.md`
- Institutional learnings: `competitive-shelf-intelligence/docs/solutions/logic-errors/price-convention-mismatch-oos-guard-clause-2026-05-28.md`
- Institutional learnings: `sku-rationalization-framework/docs/solutions/logic-errors/inner-join-silent-sku-exclusion-2026-05-28.md`
- Cinderhaven schema reference: `archived/cinderhaven-data/` (SQLite export + seed scripts)
- statsmodels STL: https://www.statsmodels.org/stable/generated/statsmodels.tsa.seasonal.STL.html
- WeasyPrint: https://doc.courtbouillon.org/weasyprint/stable/

---

## Phased Delivery

### Phase 1 — Foundation (U1–U2)
App skeleton, Postgres connection, co-packer schema. Everything else depends on this.

### Phase 2 — Analytics Core (U3–U5)
OOS correction → rolling forecast → capacity overlay. The analytical differentiators. Test independently of Dash.

### Phase 3 — App Views (U6–U9)
Data query layer, S&OP view, scenario controls, doom loop narrative. Makes the analytics visible.

### Phase 4 — Export and Deployment (U10–U12)
Excel/PDF exports, Fly.io deployment. Polish and portfolio-ready delivery.
