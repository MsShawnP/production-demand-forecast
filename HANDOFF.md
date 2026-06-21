# production-demand-forecast — Handoff Log

Session-by-session state. Updated by /log mid-session and /wrap at
session end.

For durable choices, see DECISIONS.md.
For the current work arc, see PLAN.md.
For things that didn't work, see FAILURES.md.

---

## 2026-05-31 — Project initialized

**Started from:** New project setup. Brief: `portfolio_project_brief_production_demand_forecast.md`.

**Did:** Created repo scaffold — CLAUDE.md, PLAN.md, HANDOFF.md, DECISIONS.md, FAILURES.md,
README.md, .gitignore, src/CLAUDE.md, tests/CLAUDE.md. Git init, initial commit, GitHub private
remote created.

**State:** Foundation in place. Brief reviewed and absorbed into CLAUDE.md. PLAN.md arc placeholder
ready. Stack TBD — to be decided during /clarify.

**Next:** Run `/clarify` to scope the first build arc and pin the stack.

---

## 2026-05-31 13:30

**What changed:** Full session-zero workflow complete — /clarify, /ce:brainstorm, /ce:plan all done.

**Why:** Project needed scoping, requirements doc, and implementation plan before any code is written. All three produced and committed.

**State:** Plan written at `docs/plans/2026-05-31-001-feat-production-demand-forecast-plan.md` (12 units, 4 phases). Requirements doc at `docs/brainstorms/2026-05-31-production-demand-forecast-requirements.md`. PLAN.md updated with full task list and stack. DECISIONS.md pre-populated. No code written yet.

**Next:** New session → run `/ce:work` with the plan path to begin Phase 1 (U1 app scaffold + U2 co-packer schema).

---

## 2026-05-31 14:00 — Session wrap

**Started from:** New project folder, brainstorm brief only, no scaffold.

**Did:** Full session-zero: /new-project scaffold → /clarify (stack, deploy, export confirmed) → /ce:brainstorm (requirements doc, 20 R-IDs) → /ce:plan (12-unit implementation plan, 4 phases). Researched competitive-shelf-intelligence scaffold and Cinderhaven schema as plan inputs. All planning artifacts committed and pushed.

**State:** No code written. Plan at `docs/plans/2026-05-31-001-feat-production-demand-forecast-plan.md`. Requirements at `docs/brainstorms/2026-05-31-production-demand-forecast-requirements.md`. PLAN.md stack field is stale (says FastAPI/HTML — fix in U1).

**Next:** New session → `/ce:work docs/plans/2026-05-31-001-feat-production-demand-forecast-plan.md`. Start U1 (app scaffold from competitive-shelf-intelligence) + U2 (co-packer schema). Fix PLAN.md stack field in U1.

---

## 2026-05-31 — U1–U10 complete, U11 partial, U12 pending

**Started from:** Full planning artifacts in place, zero code written. Plan at `docs/plans/2026-05-31-001-feat-production-demand-forecast-plan.md`.

**Did:** Ran `/ce:work` — executed U1 through U10 in sequence. Built the full analytics pipeline (OOS correction → STL forecast → capacity overlay), data query layer with Flask-Caching, three Dash tabs (S&OP view, scenario controls, doom loop narrative), and Excel export. 54 tests written and passing. U11 (PDF export) code written but not committed — interrupted at max context.

**State:** U1–U10 committed. U11 has uncommitted changes in `app/data.py`, `app/tabs/sop_view.py`, and `app/templates/export_pdf.html`. U12 (Dockerfile, fly.toml) not started. PDF export only works on Linux (WeasyPrint requires GTK system libs — non-functional on Windows). Inventory seed numbers for CHP-0001/CHP-0023 need calibration once actual scan_data velocities are known.

**Next:** `python -m pytest tests/ -q` → commit U11 (`git add app/data.py app/tabs/sop_view.py app/templates/ PLAN.md`). Then U12: `Dockerfile` (python:3.13-slim, `libpango-1.0-0 libcairo2 libgdk-pixbuf2.0-0 libffi-dev`, gunicorn 3 workers, non-root appuser uid 1001) + `fly.toml` (iad, 2GB, min_machines=1, /health, /cache mount) + README update. Then `fly deploy`.

---

## 2026-05-31 15:10 — First run session: app live with real Cinderhaven data

**Started from:** U1–U10 committed, U11 uncommitted, U12 not started. No `.env`, app never run.

**Did:** Got the app running end-to-end against live Cinderhaven Postgres. Fixed `db.py` search_path (`raw,public`), rewrote `seed_copack.py` with correct SKU format (`CHP-AS-001` etc.), fixed DDL runner semicolon-in-comment bug, filtered `get_scan_data()` to `<= 2025-11-01` to avoid 40s+ timeout, bumped statement_timeout to 90s, cleared stale Flask cache (C:/tmp not Git Bash /tmp).

**State:** App renders live at http://127.0.0.1:8050. 50 SKUs loading, stockout grid populated. KPI shows 50/50/50 — inventory calibration needed. Scenario chip defaults to wrong value. `app/db.py`, `app/data.py`, `db/seed_copack.py`, `.claude/` uncommitted. U11 PDF export still uncommitted. U12 not started.

**Next:** 1) Commit all changes. 2) Investigate 50/50/50 KPI — check `days_until_deadline` distribution, calibrate `sku_inventory` quantities against actual scan_data velocities. 3) Fix scenario chip default to "Base case". 4) U12: Dockerfile + fly.toml + `fly deploy`.

---

## 2026-05-31 19:30 — U12 complete, app deployed

**Started from:** U1–U11 committed, U12 not started. KPI showing 50/50/50 (as_of_date bug). App live locally only.

**Did:** Fixed KPI bug (compute_decision_deadline not receiving as_of_date — defaulted to today, all deadlines PAST_DUE). Created Dockerfile, fly.toml, .dockerignore, updated README. Deployed to Fly.io — two Dockerfile fixes needed (libgdk-pixbuf renamed in Debian Trixie; missing libpangocairo). Fixed DATABASE_URL: fly secrets import brought in a local proxy URL; fly postgres attach created an empty DB; manually redirected to existing cinderhaven DB. WeasyPrint confirmed working in container. All 12 units complete, arc marked completed.

**State:** App live at https://cinderhaven-demand-forecast.fly.dev/ — health check passing, 50 SKUs loading, 54 tests passing. All definition-of-done items checked. Plan status: completed. GitHub up to date.

**Next:** Run `/ce:compound` to capture OOS correction, STL forecast, WeasyPrint Fly.io Dockerfile, and Dash scenario controls patterns as `docs/solutions/` entries. That closes the arc.

---

## 2026-05-31 20:30 — /ce:compound complete, arc closed

**Started from:** Arc complete, app live on Fly.io. `/ce:compound` was the one remaining step.

**Did:** Full compound run (session history enabled). Documented two deployment-arc bugs:
`docs/solutions/build-errors/weasyprint-dockerfile-debian-trixie-deps-2026-05-31.md` (gdk-pixbuf renamed in Debian Trixie, missing libpangocairo) and `docs/solutions/logic-errors/kpi-as-of-date-demo-data-past-due-2026-05-31.md` (as_of_date defaulting to today against 2025 data). Updated CLAUDE.md to surface `docs/solutions/` to future agents. Committed `93cf68a`.

**State:** Arc fully closed. App live, all 12 units shipped, 54 tests passing, two solution docs committed. No open tasks.

**Next:** New arc. Options: (a) portfolio landing page for this tool, (b) `/improve` pass on the app code, (c) start next project in the backlog.

---

## 2026-06-01 — /improve post-launch audit complete, all findings fixed and deployed

**Started from:** Arc closed, v1.0 tagged, /ce:compound done. /improve was the final step.

**Did:** Full audit with security + correctness reviewers. Fixed 16 findings (3 critical, 8 important, 5 nice-to-have). Key fixes: logger NameError in sop_view.py, new-doors scenario guard, promo weeks excluded from OOS rolling median, detail panel now uses active scenario, inventory clamping bug, CSP header, f-string WHERE clause, WeasyPrint CVE-2025-68616 (upgraded to 68.1). Deployed to Fly.io.

**State:** App live at https://cinderhaven-demand-forecast.fly.dev/ with all fixes deployed. 54 tests passing. No known CVEs. Next /improve review due 2026-07-01.

**Next:** New arc — portfolio landing page, next project in backlog, or additional features (multi-SKU conflict resolution, demand sensing).

---

## 2026-06-01 — /ce:compound ×2: all /improve findings documented

**Started from:** Arc complete, /improve done, one /ce:compound run still needed to close the arc.

**Did:** Two /ce:compound Full runs documenting 4 /improve findings. First run: OOS rolling median promo neighbor contamination (critical logic bug — promo weeks inflated OOS demand corrections; test fixture fixed — sparse-neighbor version actually separates buggy from fixed). Second run: strftime %-d Windows portability (runtime_error), f-string SQL WHERE clause (security_issue, includes pd.read_sql DBAPI2 deprecation note), WeasyPrint CVE-2025-68616 (factual error caught — CVE spans 61.0–67.0 inclusive, 68.0 is first fix). Committed and pushed: 0c160ab + cfdc45f.

**State:** docs/solutions/ has 6 entries. App live, 54 tests passing, all pushed. No open tasks.

**Next:** New arc — (a) portfolio landing page, (b) next project in backlog, (c) additional features (multi-SKU conflict resolution, demand sensing). Next /improve due 2026-07-01.

---

## 2026-06-20 — UX fixes, doom loop narrative, schema isolation

**Started from:** App live, arc closed. Three UX issues + narrative polish + database wipe investigation.

**Did (across two sessions, second resumed from context compaction):**

1. **Three UX fixes** (each committed separately):
   - `69c3f19` — Kill horizontal scroll on S&OP table (flex + minWidth columns)
   - `8fec656` — Match text width to chart/table width across all tabs (removed maxWidth: 660px)
   - `1d727a5` — Scenario Controls: baseline vs scenario deltas (KPI chips with colored deltas, narrative line, baseline flag column in urgent SKUs table)

2. **Doom loop narrative** — User provided final copy for all three sections:
   - `e5736ec` — Replace all three narrative sections with final signed-off copy
   - `4cc6dde` — Tighten hero-case text and align PDF export template to match

3. **Schema isolation** (Phase C investigation + fix):
   - Root cause: cinderhaven-data-platform's `seed_all.py` runs `DROP SCHEMA IF EXISTS raw CASCADE`, destroying co-packer tables
   - Fix: Created dedicated `copack` schema, moved 5 co-packer tables there
   - `5d973d6` — `db.py` search_path → `copack,raw,public`, `seed_copack.py` creates `copack` schema
   - Smoke test: dropped `raw`, co-packer tables survived intact
   - cinderhaven-data-platform README updated (`8c98ebf` in that repo)
   - `raw` schema restored via scan_data seeder (1.3M rows, all 50 SKUs)

4. **App verified:** S&OP shows 50 SKUs, 4-tier differentiation (15 OK / 9 WARNING / 12 CRITICAL / 14 PAST_DUE). Doom loop hero CHP-PS-008 has 1,210 dark store-weeks.

**State:** Working tree clean. Branch 6 commits ahead of origin (not pushed). `.env` currently configured with flypgadmin user pointing to Fly proxy on port 15433 — may need reverting for local dev if proxy is down. `raw` schema has shared tables populated but retailer/distributor/DTC pipeline tables are still empty (only scan_data was reseeded, not the full pipeline). This doesn't affect this app — it only needs scan_data + product_master + stores + distribution_log + copack tables.

**Next:** Push to origin. Deploy to Fly.io to get the schema fix and narrative updates live. Next /improve due 2026-07-01.

---
