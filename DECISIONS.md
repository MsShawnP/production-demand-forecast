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

### 2026-05-31 — Exclude aggregate channels from OOS correction
- **Why:** UNFI-AGG, KEHE-AGG, and DTC-AGG have intentional 4–6 week bulk-order cycles in the Cinderhaven synthetic data. Rolling-median OOS correction misclassifies these gaps as stockouts, corrupting `true_demand` for distributor channels. Their velocity is reported but not corrected.
- **Scope:** `app/analytics/oos_correction.py` — `detect_oos_periods()` sets `is_oos = False` for all rows where `store_id` ends in `-AGG`.
- **Do not:** Apply OOS correction to aggregate channels, even if they show zero-sale weeks.

---

### 2026-05-31 — Analytics functions that compare against "today" accept an as_of_date parameter
- **Why:** Tests that hardcode fixture dates break silently when the real date advances past them. Discovered when `compute_decision_deadline()` used `pd.Timestamp.today()` directly — all deadline-flag tests failed because fixture dates (2025-11-01) were in the past by the test run date (2026-05-31).
- **Scope:** All functions in `app/analytics/` that compute "days until X" or compare a calculated date to the present.
- **Do not:** Use `pd.Timestamp.today()` or `datetime.now()` directly inside analytics functions. Accept `as_of_date: pd.Timestamp | None = None` as a parameter and resolve to `today()` inside the function body.

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

## Reversed / Superseded

When a decision is overturned:
1. Strike through the original entry above (don't delete)
2. Add a new entry below with the replacement decision
3. Note the link in both directions
