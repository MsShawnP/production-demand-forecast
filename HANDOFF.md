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

## 2026-06-24 — Exec-readiness UX pass (Phase 2)

**Started from:** Phase 1 performance/UX fixes deployed (loading spinners, SQL CTE optimization, cache pre-warm, page title). Column header truncation fix from Phase 1 didn't work — carried into this session.

**Did:** Six fixes, one commit each, all pushed and deployed:

1. `81d553d` — **Global time-period selector** (Full History / 12M / 6M / 3M) above tabs. Doom Loop hero chart filters by selected period via callback. S&OP and Scenario tabs see the selector but are forward-looking and unaffected. Period is relative to `_DEMO_AS_OF_DATE`.
2. `9d6a5b9` — **S&OP table column fix** — dropped Line column, all decision columns use fixed `width`, Product gets `flex: 1` to fill remaining space. Headers no longer truncate at 1200px.
3. `f534df7` — **KPI card height consistency** — Scenario Controls `_kpi_with_delta` always renders baseline annotation row (invisible spacer when delta is zero).
4. `d70f1ff` — **Doom Loop chart fixes** — height 360→520px, right margin 70→90px, shortened y2 axis label, hovertemplate rounds to whole numbers.
5. `b0f0776` — **PDF export cleanup** — SKU `white-space: nowrap`, `_fmt_date_pdf` handles NaT/None/NaN uniformly (→ "—"), `break-inside: avoid` on table rows.
6. `71f0d25` — **Excel export cleanup** — `weekly_forecast_mean` rounded to int, dates written as `datetime.date` objects with `YYYY-MM-DD` format, NaT handling broadened.

**Design note:** Time period selector is above the tab bar (not between tab bar and content) because Dash `dcc.Tabs` renders content inside the component — no slot between header and content. The selector is still global and persists across tab switches. The period only filters _display_ of historical data; the forecast always uses the full 78-week history window because STL(period=52) needs >= 52 weeks.

**State:** Working tree clean. All pushed and deployed to https://cinderhaven-demand-forecast.fly.dev/. Next /improve due 2026-07-01.

**Next:** Verify all six fixes on the live site. Potential follow-ups: (a) wire time-period selector to S&OP detail panel chart range, (b) remove Line column from PDF export table to match grid, (c) next /improve review on 2026-07-01.

---

## 2026-06-24 — Pre-compute forecast to snapshot tables (across 2 sessions)

**Started from:** Phase 2 UX fixes deployed. App pulled 840K rows and ran 50 STL forecasts on every cold load — minutes on the 2GB Fly machine.

**Did:** Two fixes, one commit each:

1. `b666e55` — **S&OP table restructure** — fixed column widths with pixel values, Product gets `flex: 1`, full SKU display without horizontal scroll. (Done in prior session.)

2. `2d84b57` — **Pre-compute forecast to snapshot tables** — the big one:
   - Created `db/precompute_forecast.py` — standalone script that runs the full pipeline (get_scan_data → OOS correction → STL forecast → capacity overlay) and writes results to `copack.forecast_snapshot` (50 rows) + `copack.doom_loop_snapshot` (3,900 rows) + `copack.snapshot_meta`.
   - Rewired `app/data.py` — snapshot mode is default. `_LIVE_COMPUTE=1` env var gates live computation. `_read_forecast_snapshot()` and `_read_doom_loop_snapshot(sku)` read from snapshot tables. `_apply_scenario_to_snapshot()` uses linear approximations (proportional stockout scaling, lead-time slip addition) for scenario controls. `median_store_velocity` stored per SKU for new-doors math.
   - Created `get_doom_loop_weekly(sku, period_weeks)` — unified interface for both snapshot and live modes. Period filtering recomputes cumulative hidden units from the filtered window start.
   - Updated `app/tabs/doom_loop.py` to use `get_doom_loop_weekly()` instead of raw `get_true_demand()` + manual aggregation.
   - Updated `app/run.py` pre-warm to log snapshot vs live mode.
   - Fixed 4 tests that needed `monkeypatch.setattr(data_module, "_LIVE_COMPUTE", True)` to stay on the live code path.

**Deploy sequence executed:**
1. `git push origin main`
2. `fly deploy` (health check passing)
3. `fly ssh console -C "python db/precompute_forecast.py"` — 702K scan rows → 50 SKU snapshots, 3,900 doom-loop rows
4. `fly machines restart` — cleared stale empty cache from pre-snapshot boot

**Verified on live site (https://forecast.lailarallc.com):**
- First load: 125ms server response (was minutes)
- S&OP View: 50 SKUs, all columns populated, KPI cards correct (50/35/26)
- Doom Loop: 1,553 hidden units, 1,210 dark store-weeks, 4.5% understatement, 76/78 weeks — all from snapshot
- Scenario Controls: same `get_sop_summary()` pipeline, confirmed working
- Zero errors in Fly logs

**State:** Working tree clean. All pushed. App live at https://forecast.lailarallc.com. 55 tests passing. Data is synthetic and only changes on reseed — run `python db/precompute_forecast.py` on Fly after any reseed.

**Next:** (a) Next /improve review due 2026-07-01. (b) Wire time-period selector to S&OP detail panel chart range. (c) Remove Line column from PDF export table to match grid.

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

## 2026-06-24 — Exec-readiness narrative polish and color audit

**Started from:** Pre-compute forecast deployed. Continuing exec-readiness UX pass.

**Did:** 8 commits — moved period selector into Doom Loop tab only, fixed S&OP third KPI card (two iterations), updated narrative copy for exec readiness, reordered tabs story-first (Doom Loop → S&OP → Scenario Controls), added co-packer production framing across all three tabs, full color audit (5 off-palette fixes), sharpened hero cards and closing paragraph. Pushed and deployed `669bc2d`; remaining 3 commits unpushed.

**State:** Working tree clean. 3 commits ahead of origin. 55 tests passing. All narrative and color corrections complete.

**Next:** Push 3 unpushed commits and deploy to Fly.io. Verify on live site. Next /improve due 2026-07-01.

---

## 2026-06-24 — Hero card single-row fix

**Started from:** Prior session's wrap landed. 3 unpushed commits needed push + deploy.

**Did:** Pushed and deployed prior commits. Fixed hero cards wrapping to two lines — `flexWrap: "nowrap"` on container, `flex: "1"` on each `dark_card`. Pushed, deployed, verified on live site.

**State:** Working tree clean. All pushed and deployed. 55 tests passing. Hero cards confirmed in single row.

**Next:** No immediate work queued. Next /improve due 2026-07-01.

---

## 2026-06-25 15:55 — Exec-readiness polish deployed and verified

**Started from:** Hero card single-row fix deployed. Continuing exec-readiness UX pass.

**Did:** Eight exec-readiness fixes in one commit (`d79fdd9`): hero card single-row, KPI label alignment, header tool name, tab title, Doom Loop visual separation, detail panel chart audit, PDF co-packer narrative, conflict column showing shared line. Follow-up fix (`2b23fcf`): abbreviated production line names to two-letter codes (AS/DG/PS/SB/SC) after full names truncated at 100px. Both deployed to Fly.io and verified on live site.

**State:** Working tree clean. All pushed and deployed to https://forecast.lailarallc.com. 55 tests passing. Conflict column shows "⚠ AS" cleanly.

**Next:** No immediate work queued. Next /improve due 2026-07-01.

---
