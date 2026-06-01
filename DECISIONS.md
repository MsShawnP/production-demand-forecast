# production-demand-forecast — Decisions Log

Permanent record of choices that should survive session turnover.
If a decision is reversed, strike it through and add the replacement
below — don't delete.

---

## Format

Each entry:
- **Date** — when decided
- **Decision** — one sentence, imperative voice
- **Why** — the reasoning, including what was tried and rejected
- **Scope** — what this applies to (file, chunk, deliverable, or "global")
- **Do not** — explicit anti-instructions, if any

---

## Architecture & Pipeline

### 2026-05-31 — Separate analytics logic from the Dash data layer
- **Why:** Pure analytics functions (OOS correction, forecasting, capacity math) belong in `app/analytics/` with no Dash or cache dependency, callable and testable in isolation. `app/data.py` is the caching/query layer that wraps analytics output for Dash callbacks.
- **Scope:** This project and all future Dash analytics projects in the portfolio.
- **Do not:** Put analytical computation inside `app/data.py` functions — mixing query I/O with analytics logic makes the analytics untestable without mocking Postgres.

### 2026-05-31 — Keep forecasting method pragmatic (seasonal time-series only)
- **Why:** The analytical differentiator is the OOS correction and the demand-vs-capacity gap logic, not forecast-algorithm sophistication. A complex model trained on zero-sale stockout windows just learns to predict zero. The OOS correction must happen before any model training.
- **Scope:** Global — all forecasting logic in this project
- **Do not:** Reach for ML models, neural nets, or exotic forecasting methods. A defensible seasonal time-series with OOS correction is the goal.

### 2026-05-31 — OOS correction method: rolling-median baseline
- **Why:** Use a rolling median of the 3 weeks pre- and post-stockout, adjusted for seasonal index. Simple, defensible, transparent — shows competence in recognizing the doom loop mechanically. See brief section §3 Move 1 for rationale.
- **Scope:** OOS correction module
- **Do not:** Interpolate linearly across the zero-sale window; this misses the seasonal baseline.

### 2026-05-31 — Forecast horizon: 12-week rolling window
- **Why:** Safely covers the maximum 8–12 week co-packer lead time needed to trigger a production run. Rolling (not static annual budget) so it stays live as data updates.
- **Scope:** Global — all forward-looking calculations

### 2026-05-31 — MVP: single co-packer
- **Why:** Multi-co-packer routing adds complexity without changing the analytical core. v2 extension is documented as a known open question in the brief.
- **Scope:** Global for v1

---

## Data & Schema

### 2026-06-01 — OOS rolling-median neighbor selection excludes promo weeks
- **Why:** Including promo-inflated weeks in the rolling median overstates the correction estimate for OOS periods adjacent to promotions. The seasonal index is already computed on non-promo weeks; the rolling-median baseline should match so the two components are consistent.
- **Scope:** `app/analytics/oos_correction.py` — `_correct_group()` neighbor pool selection.
- **Do not:** Re-include promo weeks in `neighbor_pool` even if it simplifies the code. Fall back to all non-OOS weeks only when every non-OOS week is a promo week (no other non-promo reference exists for that SKU/store pair).

---

### 2026-05-31 — Exclude aggregate channels from OOS correction
- **Why:** UNFI-AGG, KEHE-AGG, and DTC-AGG have intentional 4–6 week bulk-order cycles in the Cinderhaven synthetic data. Rolling-median OOS correction misclassifies these gaps as stockouts, corrupting `true_demand` for distributor channels. Their velocity is reported but not corrected.
- **Scope:** `app/analytics/oos_correction.py` — `detect_oos_periods()` sets `is_oos = False` for all rows where `store_id` ends in `-AGG`.
- **Do not:** Apply OOS correction to aggregate channels, even if they show zero-sale weeks.

---

### 2026-05-31 — Analytics functions that compare against "today" accept an as_of_date parameter
- **Why:** Tests that hardcode fixture dates break silently when the real date advances past them. Discovered when `compute_decision_deadline()` used `pd.Timestamp.today()` directly — all deadline-flag tests failed because fixture dates (2025-11-01) were in the past by the test run date (2026-05-31).
- **Scope:** All functions in `app/analytics/` that compute "days until X" or compare a calculated date to the present.
- **Do not:** Use `pd.Timestamp.today()` or `datetime.now()` directly inside analytics functions. Accept `as_of_date: pd.Timestamp | None = None` as a parameter and resolve to `today()` inside the function body.

### 2026-05-31 — get_scan_data() always filters to <= _DEMO_AS_OF_DATE
- **Why:** Unfiltered scan_data has 1.4M rows (3 years). Full query with correlated EXISTS on promotions takes 40+ seconds, silently times out, returns an empty DataFrame, and Flask-Caching stores that empty result for 1 hour — making the bug invisible.
- **Scope:** `app/data.py` — `get_scan_data()` only. Other functions are unaffected.
- **Do not:** Remove the `week_ending <= _DEMO_AS_OF_DATE` filter to "get all history." If more lookback is needed, change `_DEMO_AS_OF_DATE` or replace the EXISTS subquery with a CTE join first.

### 2026-05-31 — Cinderhaven tables accessed via search_path, not schema prefix
- **Why:** Cinderhaven data lives in the `raw` schema; co-packer tables land in `public`. Setting `search_path=raw,public` on the psycopg2 pool lets all SQL run without schema prefixes and keeps queries portable between dev (local proxy) and prod (Fly.io internal).
- **Scope:** `app/db.py` pool options. All application SQL in this project.
- **Do not:** Prefix table names with `raw.` in application SQL — let the search path resolve it. If a new table is added to `raw`, it is automatically visible without touching any queries.

---

## Visualization

[Chart conventions, palette decisions, interactivity choices]

---

## Output Formats

### 2026-05-31 — Use WeasyPrint for PDF export
- **Why:** WeasyPrint converts HTML/CSS to PDF, so the Lailara Design System CSS reuses directly — no rebuilding the layout from scratch. ReportLab requires programmatic layout construction. Headless Chromium adds excessive Docker image weight.
- **Scope:** PDF export in this project (`app/templates/export_pdf.html` + WeasyPrint render path).
- **Do not:** Use ReportLab or headless Chromium for this export. WeasyPrint requires system packages (pango, cairo, gdk-pixbuf) in the Dockerfile — install them, don't skip.

---

## Writing & Voice

### 2026-05-31 — Lead with the decision deadline, not the forecast number
- **Why:** "Projected demand for SKU X is 5,000 units" is a forecast. "You'll run out in week 9 and the deadline to prevent it is week 3" is a decision. The decision deadline is what makes an ops lead act.
- **Scope:** All copy, headlines, and chart annotations in the deliverable.

---

### 2026-05-31 — Connecting a new Fly.io app to an existing Fly.io Postgres database
- **Why:** `fly secrets import < .env` imports the local proxy URL (127.0.0.1:15433) — it works for local dev through `fly proxy` but resolves to localhost inside Fly.io containers. `fly postgres attach` creates a new empty database instead of pointing to the existing one. The correct pattern: attach to get a valid internal URL format, then `fly secrets set DATABASE_URL=...` with the existing database name substituted.
- **Scope:** Any future Fly.io deployment that reuses the Cinderhaven Postgres cluster (`cinderhaven-db`).
- **Do not:** Import `DATABASE_URL` from `.env` directly into Fly.io secrets — it will always be a proxy URL and will crash the container on startup.

---

### 2026-06-01 — Use cursor.execute() directly for psycopg2 queries, not pd.read_sql()
- **Why:** `pd.read_sql()` with a raw psycopg2 connection falls through to an undocumented DBAPI2 fallback in pandas 2.x that emits `UserWarning: "Other DBAPI2 objects are not tested."` It works today but is explicitly on a deprecation path. The correct psycopg2 idiom is `cursor.execute(sql, params)` + `pd.DataFrame(cursor.fetchall(), columns=[...])`.
- **Scope:** Any new database query in `app/data.py` or elsewhere that uses `get_conn()`. Existing `get_scan_data()` still uses `pd.read_sql()` — fix it when next touched.
- **Do not:** Pass a raw psycopg2 connection to `pd.read_sql()` in new code. Either use the cursor path directly, or wrap the connection in a SQLAlchemy engine if `pd.read_sql()` is preferred.

---

## Reversed / Superseded

When a decision is overturned:
1. Strike through the original entry above (don't delete)
2. Add a new entry below with the replacement decision
3. Note the link in both directions
