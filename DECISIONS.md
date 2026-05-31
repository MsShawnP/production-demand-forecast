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

[Decisions about data sources, schemas, transformations]

---

## Visualization

[Chart conventions, palette decisions, interactivity choices]

---

## Output Formats

[Decisions about deliverable formats, structure, organization]

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
