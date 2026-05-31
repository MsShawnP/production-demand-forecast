---
date: 2026-05-31
topic: production-demand-forecast
---

# Production Demand Forecast

## Summary

A Dash + Plotly web app that corrects Cinderhaven's POS velocity for out-of-stock periods, builds a 12-week rolling demand forecast by SKU, overlays a new co-packer capacity layer seeded into the Cinderhaven Postgres SSOT, and surfaces per-SKU stockout dates and production decision deadlines. Interactive scenario controls and dual Excel/PDF export make it both a teaching tool and a demonstration of decision infrastructure for specialty food brands.

---

## Problem Frame

Specialty food brands using co-packers plan production reactively: inventory gets low, someone notices, a run gets ordered. But co-packer lead times are 8–12 weeks. By the time inventory is visibly low, the production decision deadline already passed. The product short-ships. Empty shelves suppress velocity — and here the loop tightens: the brand forecasts off that suppressed velocity and under-produces, guaranteeing the next stockout. The forecast is wrong *because* the brand keeps running out. The stockouts are poisoning the very data the forecast is built on.

The status quo is a reorder-point spreadsheet that doesn't account for lead time, current bookings, or the fact that its own stockout history has corrupted the baseline it's forecasting from. There is no forward view that says "here's when you run out and here's the last date to prevent it."

---

## Actors

- A1. **Ops Lead / VP Ops**: The primary user. Opens the app weekly to review SKU status, run scenarios, and download the decision brief for co-packer conversations or internal monitoring.
- A2. **CEO / COO**: Views the scenario layer to understand how growth plans (new retail doors, promos) collide with production capacity — a strategic conversation the tool makes possible for the first time.
- A3. **Portfolio Viewer**: A prospective client or recruiter reviewing the Lailara portfolio piece. Needs to grasp the doom loop mechanism and the tool's value within ~2 minutes without a guided walkthrough.

---

## Key Flows

- F1. **S&OP Weekly Review**
  - **Trigger:** Ops lead opens the app at the start of the week
  - **Actors:** A1
  - **Steps:** App loads the current S&OP view → ops lead scans per-SKU status → red-flagged SKUs (decision deadline < 14 days) are immediately visible → ops lead drills into a flagged SKU to see stockout date, decision deadline, and whether a shared-line conflict exists → ops lead determines which runs to book
  - **Outcome:** Ops lead knows exactly which SKUs need a production decision this week and when the deadline is
  - **Covered by:** R7, R8, R9, R10, R11, R12

- F2. **Scenario Modeling**
  - **Trigger:** Ops lead (or CEO) adjusts a scenario control
  - **Actors:** A1, A2
  - **Steps:** User adjusts promo lift %, new retailer door count, or lead-time slip → server recomputes forecast, stockout dates, and decision deadlines → S&OP view updates without page reload → user sees how deadlines shift under the scenario
  - **Outcome:** User understands how a specific growth plan or supply disruption affects production urgency
  - **Covered by:** R13, R14, R15

- F3. **Export**
  - **Trigger:** User clicks the Excel or PDF export button
  - **Actors:** A1, A2, A3
  - **Steps:** User sets scenario controls to desired state → clicks export → file downloads to local machine
  - **Outcome:** Excel workbook usable as a co-packer meeting agenda or internal MPS brief; PDF usable as a portfolio leave-behind
  - **Covered by:** R18, R19

- F4. **Doom Loop Demo (Portfolio Viewer Path)**
  - **Trigger:** Portfolio viewer lands on the app
  - **Actors:** A3
  - **Steps:** Viewer sees the doom loop narrative in the app → finds the Artisan Sauce case study → chart shows naive forecast (4.2 units/store/week) vs. OOS-corrected forecast (5.0 units/store/week) for the February stockout → viewer understands how the stockout suppressed the data and how the correction breaks the cycle
  - **Outcome:** Viewer grasps the analytical insight — the correction is what breaks the loop — without needing a guided explanation
  - **Covered by:** R16, R17

---

## Requirements

**OOS Correction**

- R1. The app corrects observed POS velocity for OOS periods using a rolling-median baseline: the median of the 3 pre-stockout weeks and 3 post-stockout weeks, adjusted for the seasonal index of the stockout window. The result is stored as `true_demand`.
- R2. OOS periods are detected by identifying multi-day blocks of near-zero POS velocity for a SKU at stores where `distribution_log` confirms the SKU was authorized during that period.
- R3. `true_demand` is used as the sole input to all downstream forecasting. The app never forecasts off uncorrected observed velocity.

**Rolling Forecast**

- R4. The app builds a 12-week rolling forward forecast by SKU from `true_demand`, incorporating seasonality and trend. The horizon covers the full 8–12 week co-packer lead-time range.
- R5. The forecast window is rolling — it reflects current data and updates as new records are available, rather than being a static annual plan.

**Co-Packer Capacity Overlay**

- R6. The Cinderhaven Postgres is extended with a co-packer capacity schema: tables for co-packers, production lines, production schedules, and per-SKU production configuration (lead time, minimum run size, line assignment). The schema is seeded with realistic synthetic data and designed to be reusable across future Cinderhaven projects.
- R7. For each SKU, the app computes the projected stockout date: the week when current inventory plus all scheduled production runs is exhausted by the `true_demand` forecast.
- R8. For each SKU, the app computes the production decision deadline: the stockout date minus the SKU's co-packer lead time. This is the last date a production run can be ordered to prevent the stockout.
- R9. The app detects shared-line conflicts: when two or more SKUs assigned to the same production line have overlapping decision deadlines, all affected SKUs are flagged as a critical conflict — not as independent deadlines.

**S&OP View**

- R10. The app displays a per-SKU S&OP view with: true demand (weekly), current inventory, scheduled production (from the production schedule), projected stockout date, and production decision deadline.
- R11. SKUs with a decision deadline fewer than 14 days from today are highlighted red.
- R12. SKUs in a shared-line conflict are flagged with a distinct critical indicator, separate from the standard red deadline flag.

**Scenario Controls**

- R13. The app provides three scenario controls: promo demand lift (%), new retailer door count (integer), and co-packer lead-time slip (weeks).
- R14. Adjusting any scenario control triggers a server-side recompute of the affected forecasts, stockout dates, and decision deadlines. The S&OP view reflects the updated values without a full page reload.
- R15. Scenario controls default to the baseline state (0% lift, 0 new doors, 0 lead-time slip). The baseline represents the current Cinderhaven data as-is.

**Doom Loop Narrative**

- R16. The app includes explanatory text and chart annotations that make the doom loop mechanism visible: how OOS periods suppress observed velocity, how forecasting off that suppressed data perpetuates stockouts, and how the OOS correction breaks the cycle.
- R17. The Cinderhaven Artisan Sauce February OOS event serves as the hero demo case. A chart explicitly shows the naive forecast (~4.2 units/store/week) alongside the OOS-corrected forecast (~5.0 units/store/week), with the February stockout period marked.

**Export**

- R18. The app provides an Excel export (.xlsx) of the current S&OP state: per-SKU decision data including `true_demand`, stockout date, production decision deadline, and the active scenario parameters. This is the operational MPS handoff format.
- R19. The app provides a PDF export of the current S&OP view: a print-ready document including the narrative, charts, and per-SKU decision data reflecting the active scenario state.

**Deployment**

- R20. The app is deployed to Fly.io and accessible via a public URL.

---

## Acceptance Examples

- AE1. **Covers R11.** Given a SKU whose production decision deadline is 10 days from today, the app renders that row highlighted red in the S&OP view.
- AE2. **Covers R9, R12.** Given SKU A and SKU B both assigned to Line 1 with overlapping decision deadlines in week 3, both SKUs are flagged with a critical conflict indicator — not just individual red flags.
- AE3. **Covers R14.** Given the user sets promo lift to +30% for the Artisan Sauce, the stockout date moves earlier and the decision deadline tightens; the S&OP view reflects the updated values without a full page reload.
- AE4. **Covers R3, R17.** Given the Artisan Sauce February OOS event in `scan_data`, the chart shows observed velocity dropping to near-zero for the stockout weeks and `true_demand` holding at ~5.0 units/store/week across that window. The naive forecast line (built on uncorrected velocity) diverges below the corrected forecast line.

---

## Success Criteria

- A portfolio viewer understands the doom loop mechanism and the OOS correction's role in breaking it within ~2 minutes, without a guided walkthrough.
- An ops lead reviewing the S&OP view can identify which SKUs need a production decision this week and when the deadline is, without reading documentation.
- The Excel export is directly usable as a co-packer conversation agenda item — another practitioner could hand it to a co-packer as-is.
- The app is live on Fly.io with the Cinderhaven case study populated.

---

## Scope Boundaries

- Multi-co-packer routing — v1 supports a single co-packer. A brand with multiple co-packers is v2.
- Automated production ordering — the tool surfaces the decision and deadline; it does not place orders.
- Ingredient / raw material planning (MRP) — demand → finished goods is in scope; finished goods → ingredient requirements is not.
- ML or exotic forecasting methods — pragmatic seasonal time-series only. The value is the OOS correction and capacity overlay, not forecast sophistication.
- Admin UI for co-packer constraints — co-packer data is seeded via scripts, not editable in the running app.
- Real brand data — Cinderhaven synthetic data only.
- User authentication — read-only portfolio demo, no auth required.

---

## Key Decisions

- **Dash + Plotly**: Follows the existing competitive-shelf-intelligence portfolio pattern. Reuses `db.py`, `data.py`, `charts.py`, and the Fly.io deployment setup. Scenario controls are Dash callbacks — no client-side JS forecasting logic.
- **All data in Postgres SSOT**: Co-packer constraints go into the Cinderhaven Postgres as a proper schema, not a config file. Designed for reuse across future Cinderhaven projects.
- **OOS correction before forecasting**: `true_demand` is a prerequisite to any forecast step. The app never lets uncorrected velocity reach the forecasting layer.
- **Rolling-median OOS correction**: 3 pre + 3 post week median, seasonal-adjusted. Chosen for defensibility and transparency — a complex model on zero-sale windows just learns to predict zero.
- **Dual export**: Excel for operational handoff; PDF for portfolio/presentation. Both reflect the active scenario state at export time.
- **12-week rolling horizon**: Covers the full co-packer lead-time range (8–12 weeks). Rolling, not static annual budget.

---

## Dependencies / Assumptions

- Cinderhaven Postgres is accessible and contains `scan_data`, `distribution_log`, `product_master`, `promotions`, and `orders`/`order_lines`.
- The Artisan Sauce February OOS event is present in `scan_data` (referenced in both the project brief and the competitive-shelf-intelligence piece).
- The existing `competitive-shelf-intelligence` project's `db.py`, `data.py`, and `charts.py` are the scaffold. Patterns carry over directly.
- The co-packer capacity schema will be seeded with synthetic constraints realistic enough that the decision deadlines and shared-line conflicts are non-trivial in the demo.

---

## Outstanding Questions

### Deferred to Planning

- [Affects R4][Needs research] What seasonal decomposition approach works best with 157 weeks of Cinderhaven `scan_data`? (STL, multiplicative, or additive decomposition — depends on variance structure of the data.)
- [Affects R19][Technical] Which PDF generation library to use: WeasyPrint, ReportLab, or headless Chromium? Trade-off is render fidelity vs. Fly.io image size.
- [Affects R6][Technical] What specific co-packer constraints (lead times, min run sizes, line assignments) should be seeded for Cinderhaven's synthetic co-packer to produce realistic and non-trivial decision deadlines in the demo?
