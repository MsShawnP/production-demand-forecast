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

- **Backend:** Python (FastAPI) — queries Cinderhaven Postgres, runs OOS correction + forecast + capacity logic
- **Frontend:** HTML/JS + Lailara Design System (SVG charts, Economist style)
- **Database:** Cinderhaven Data Platform — existing synthetic Postgres SSOT
- **Deployment:** Fly.io

## Tasks

Work in vertical slices — one piece end-to-end before moving to the next.

- [x] /clarify — scope confirmed
- [ ] Explore Cinderhaven Postgres schema — confirm available tables (velocity/POS, inventory, production bookings)
- [ ] OOS correction module — rolling-median baseline (pre/post-stockout), outputs `true_demand` per SKU per week
- [ ] Rolling forecast module — 12-week forward demand by SKU, built on `true_demand`
- [ ] Capacity overlay — join forecast to co-packer lead times, min run sizes; compute `stockout_date` and `decision_deadline`
- [ ] Shared-line conflict detection — flag SKUs with overlapping deadlines on the same line
- [ ] FastAPI backend — expose forecast + capacity data as JSON endpoints
- [ ] S&OP view (frontend) — per-SKU forward view: true demand, inventory, scheduled production, stockout date, decision deadline; red flag when deadline < 14 days
- [ ] Scenario controls (frontend) — promo lift %, retailer door count, lead-time slip; update deadlines in real time
- [ ] Export — downloadable production decision brief (format: TBD during build, likely Excel or PDF)
- [ ] Fly.io deployment — Dockerfile, fly.toml, Postgres connection via env var
- [ ] Doom loop narrative — copy and annotations that explain the OOS correction as the circuit breaker

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
