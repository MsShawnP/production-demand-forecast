# production-demand-forecast — Current Work Plan

The current arc of work. Updated when the arc changes, not every
session. For session-by-session state, see HANDOFF.md.

---

## Goal

Build and deploy a Fly.io web app that corrects Cinderhaven's POS velocity for OOS periods, forecasts 12-week rolling demand by SKU, overlays co-packer capacity constraints, and surfaces per-SKU stockout dates + production decision deadlines with interactive scenario controls and a downloadable decision brief.

## Why this arc, why now

This is the full v1 build — the analytical core (OOS correction → forecast → capacity overlay → decision deadline) plus the interactive web interface. Everything else depends on this foundation being right.

## Business question this arc answers

Given current inventory, scheduled production, and true (OOS-corrected) projected demand, which SKUs will stock out, when, and what is the last date a production run can be ordered to prevent it?

## Stack

- **UI:** Python + Dash 3.x + Plotly + dash-ag-grid + dash-bootstrap-components (Lailara Design System via constants.py + charts.py)
- **Analytics:** `app/analytics/` package — OOS correction, rolling forecast (STL via statsmodels), capacity overlay
- **Database:** Cinderhaven Data Platform — existing synthetic Postgres SSOT + new co-packer schema (4 tables)
- **Deployment:** Fly.io (python:3.13-slim, gunicorn 3 workers, 2GB memory)
- **Export:** Excel via openpyxl, PDF via WeasyPrint + Jinja2

## Tasks

Work in vertical slices — one piece end-to-end before moving to the next.
Full plan: `docs/plans/2026-05-31-001-feat-production-demand-forecast-plan.md`

**Phase 1 — Foundation**
- [x] /clarify, /ce:brainstorm, /ce:plan — scope confirmed, requirements and plan written
- [x] Cinderhaven Postgres schema confirmed (scan_data, distribution_log, product_master, promotions)
- [x] U1: App scaffold — copy db.py, data.py, constants.py, charts.py, run.py from competitive-shelf-intelligence
- [x] U2: Co-packer schema — design + seed 4 tables in Cinderhaven Postgres SSOT

**Phase 2 — Analytics Core**
- [x] U3: OOS correction module (`app/analytics/oos_correction.py`)
- [x] U4: Rolling forecast module (`app/analytics/forecast.py`)
- [x] U5: Capacity overlay + decision deadline (`app/analytics/capacity.py`)

**Phase 3 — App Views**
- [x] U6: Data query layer (`app/data.py` — wraps analytics, caches via Flask-Caching)
- [ ] U7: S&OP view tab — per-SKU table, red flags, conflict indicators
- [ ] U8: Scenario controls tab — promo lift, retailer doors, lead-time slip
- [ ] U9: Doom loop narrative tab — hero case chart (Artisan Sauce Feb OOS)

**Phase 4 — Export + Deployment**
- [ ] U10: Excel export (.xlsx via openpyxl)
- [ ] U11: PDF export (WeasyPrint, Jinja2 template)
- [ ] U12: Fly.io deployment (Dockerfile, fly.toml)

## Out of scope for this arc

- Deep co-packer capacity optimization (that's #22, Co-Packer/Production Capacity Model)
- Automated production ordering
- Ingredient/raw material planning (MRP)
- Exotic forecasting methods (ML, neural nets)
- Multi-co-packer routing (v2)

## Definition of done for this arc

- [ ] App deployed and live on Fly.io
- [ ] Cinderhaven Artisan Sauce SKU shows the February OOS event — true demand corrects above observed velocity
- [ ] Per-SKU S&OP view renders with stockout date and decision deadline
- [ ] At least one SKU flags red (decision deadline < 14 days)
- [ ] Scenario controls update deadlines in real time without page reload
- [ ] Export downloads a usable decision brief
- [ ] Doom loop narrative is present and legible to a non-data-science reader

---

## Arc history

### 2026-05-31 — Project initialized
- Outcome: Repo scaffolded, brief reviewed, state files created
- Tag: v0.1-foundation

---

## Improvement history

<!-- Entries are added by /improve — don't delete this section -->
