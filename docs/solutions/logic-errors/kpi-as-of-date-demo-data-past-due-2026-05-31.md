---
title: KPI deadlines all show PAST_DUE when analytics function defaults as_of_date to today
date: 2026-05-31
category: docs/solutions/logic-errors/
module: analytics
problem_type: logic_error
component: service_object
severity: high
symptoms:
  - KPI row shows N/N/N — every SKU flagged as needing action regardless of inventory
  - Every row in the AG Grid table shows PAST_DUE in the deadline status column
  - No errors in Dash callback logs — computation runs cleanly but produces wrong output
root_cause: logic_error
resolution_type: code_fix
tags:
  - deadline
  - as-of-date
  - demo-data
  - synthetic-data
  - kpi
  - time-anchor
  - dash
---

# KPI deadlines all show PAST_DUE when analytics function defaults as_of_date to today

## Problem

The S&OP dashboard KPI row showed 50/50/50 — all SKUs flagged PAST_DUE — when the underlying data
indicated a healthy spread of OK, WARNING, and CRITICAL items. The root cause was a time-anchor
mismatch: `compute_decision_deadline()` defaulted to `pd.Timestamp.today()` (2026), but all
Cinderhaven synthetic scan data was cut off at 2025-11-01. Every stockout date was months in the
past relative to today, so every deadline classified as PAST_DUE.

## Symptoms

- KPI row shows `50 | 50 | 50` regardless of inventory levels or forecast values
- Every AG Grid row has `PAST_DUE` in the deadline flag column
- `days_until_deadline` is negative for all SKUs
- No errors logged — the analytics functions execute correctly, they just compute against the wrong date

## What Didn't Work

- Inspected the Dash callback that feeds the KPI row and the AG Grid conditional formatting rules —
  both were correct. The bug was upstream in the data layer, not in the display layer.
- Suspected synthetic seed inventory quantities were set too low, causing genuinely early stockout
  dates. Checked the seed values; inventory levels were reasonable.
- The `as_of_date` parameter was added to `compute_decision_deadline` to fix test failures (tests
  used a `TODAY = 2025-11-01` fixture against the 2026 wall clock). The analytics layer was
  correct, but `get_sop_summary` — the production call site — was never updated to pass the anchor.
  The fix existed in the analytics layer but was unused in the running app. (session history)

## Solution

Define a demo anchor date constant and pass it explicitly at the call site:

```python
# app/data.py

_DEMO_AS_OF_DATE = "2025-11-01"   # anchors the demo to the data cutoff date

def get_sop_summary(...):
    ...
    # BEFORE (bug): as_of_date defaults to pd.Timestamp.today() (2026)
    # sop = compute_decision_deadline(sop, sku_config_adj)

    # AFTER (fix): explicitly anchor to the data cutoff date
    sop = compute_decision_deadline(
        sop, sku_config_adj, as_of_date=pd.Timestamp(_DEMO_AS_OF_DATE)
    )
```

The `compute_decision_deadline` signature already accepted the parameter:

```python
# app/analytics/capacity.py

def compute_decision_deadline(
    sop_df: pd.DataFrame,
    sku_config_df: pd.DataFrame,
    as_of_date: pd.Timestamp | None = None,
) -> pd.DataFrame:
    today = (as_of_date or pd.Timestamp.today()).normalize()
    ...
```

## Why This Works

With `as_of_date = 2025-11-01`, `days_until_deadline` is computed relative to the last real data
point, not the wall clock date of whoever runs the app. Stockout dates in December 2025 and
January 2026 correctly show as 4–8 weeks out from the anchor, and the CRITICAL / WARNING / OK /
PAST_DUE classification produces a realistic distribution instead of collapsing everything into
PAST_DUE.

## Prevention

- Any analytics function that computes time-relative values — deadlines, days-until, expiry windows,
  age — should accept an explicit `as_of_date: pd.Timestamp | None = None` parameter. Defaulting
  to `pd.Timestamp.today()` is correct for live production data but breaks any app using synthetic
  or historical data.
- For demo and portfolio apps built on synthetic historical data, define a named anchor constant
  (e.g., `_DEMO_AS_OF_DATE = "2025-11-01"`) and thread it through every time-relative calculation.
  Do not rely on wall-clock time.
- Add a debug log in any `as_of_date`-accepting function that emits the anchor value at call time,
  making time-anchor bugs immediately diagnosable:
  ```python
  logger.debug("compute_decision_deadline: as_of_date=%s", today.date())
  ```
- When a KPI count shows an implausible distribution (e.g., all SKUs flagging when total == count),
  suspect a time-anchor mismatch before inspecting display or formatting logic.

## Related Issues

- Fix commit: `860cb7b` (KPI as_of_date bug)
- DECISIONS.md entry: "analytics functions must accept injectable `as_of_date`, never call
  `pd.Timestamp.today()` directly inside the function body"
- Affects any dashboard built on the Cinderhaven synthetic dataset run after its 2025 data cutoff
