---
title: "OOS Correction Rolling Median: Promo Week Contamination"
date: 2026-06-01
category: docs/solutions/logic-errors/
module: app/analytics/oos_correction.py
problem_type: logic_error
component: service_object
severity: critical
symptoms:
  - "OOS correction over-estimates true demand velocity near promotional periods"
  - "Rolling median neighbor pool includes elevated promo-week sales"
  - "Forecast inflation during OOS blocks adjacent to promotions"
root_cause: scope_issue
resolution_type: code_fix
tags:
  - oos-correction
  - demand-forecasting
  - promo-contamination
  - rolling-median
  - neighbor-selection
  - data-quality
  - sop
  - velocity-estimation
---

# OOS Correction Rolling Median: Promo Week Contamination

## Problem

The OOS correction function `_correct_group()` in `app/analytics/oos_correction.py` included
promotion weeks in the neighbor pool used to compute the rolling median for OOS-flagged weeks.
Promotion weeks carry sales 40–80% above baseline velocity. Any OOS event adjacent to a
promotion campaign received an inflated correction — one that reflected elevated promo demand
rather than the true underlying baseline.

The seasonal index computation (`_compute_seasonal_index()`) already excluded promotion weeks,
making the neighbor selection rule inconsistent. The asymmetry was only visible during a
correctness review — not from test failures or runtime errors.

## Symptoms

- OOS corrections for stockout events adjacent to promotion windows were systematically high —
  roughly 40–80% above corrected values for OOS events with no nearby promotions.
- In the Artisan Sauce February 2025 case, the rolling median included a Whole Foods feature
  week that immediately preceded the stockout. The OOS correction was inflated by ~55% above
  true baseline demand.
- The doom loop narrative chart showed a larger apparent demand signal than the historical
  record supported.
- Corrected values passed visual inspection — the inflation was only visible when
  cross-checked against the known promo calendar, not as a crash or callback error.

## What Didn't Work

The bug went undetected through the full 12-unit development arc and a 54-test suite. Synthetic
test data used non-overlapping OOS and promo periods — the contamination only triggers when an
OOS block and a promo week are adjacent or concurrent, which none of the fixtures exercised.

The `is_promo` flag existed in the scan data from project inception (195 promo events in the
Cinderhaven promotions table). The oversight was not filtering on it in neighbor selection, not
a missing-data problem. (session history)

No failed fix attempts were recorded. The problem was surfaced in a single correctness review
pass that flagged the asymmetry: the seasonal index excluded promos; the neighbor pool did not.

## Solution

Filter promotion weeks out of the neighbor pool before computing position lookups. Fall back to
all non-OOS weeks only when every non-OOS week is also a promo week — a rare edge case that
ensures the correction still runs rather than flagging insufficient data.

**Before (buggy):**

```python
non_oos_idx = group.index[~oos_mask].tolist()

if not non_oos_idx:
    group["true_demand"] = 0.0
    group["insufficient_data"] = True
    return group

positions = list(group.index)
pos_of = {idx: i for i, idx in enumerate(positions)}
neighbor_positions = [pos_of[i] for i in non_oos_idx]  # includes promo weeks — inflates median
```

**After (fixed):**

```python
non_oos_idx = group.index[~oos_mask].tolist()

if not non_oos_idx:
    group["true_demand"] = 0.0
    group["insufficient_data"] = True
    return group

# For neighbor selection, exclude promo weeks to avoid inflating the rolling
# median with promo-elevated sales. Fall back to all non-OOS weeks only when
# every non-OOS week is a promo week (rare; ensures we always have neighbors).
promo_mask = group.get("is_promo", pd.Series(False, index=group.index)).astype(bool)
non_oos_non_promo_idx = group.index[~oos_mask & ~promo_mask].tolist()
neighbor_pool = non_oos_non_promo_idx if non_oos_non_promo_idx else non_oos_idx

positions = list(group.index)
pos_of = {idx: i for i, idx in enumerate(positions)}
neighbor_positions = [pos_of[i] for i in neighbor_pool]
```

The `group.get("is_promo", ...)` pattern handles DataFrames where the `is_promo` column is
absent without raising a KeyError.

A performance fix was bundled: `pos_of` lookups moved outside the OOS loop (O(n) once vs O(n)
per OOS row). This is unrelated to the correctness fix but was applied in the same edit.

## Why This Works

The rolling median is meant to estimate baseline velocity — what the SKU would have sold in a
normal week had inventory been available. Promotion weeks are not normal weeks.

The analytical rule: **the neighbor pool and the seasonal index must exclude the same week
categories.** The seasonal index divides per-week mean by the overall mean — both computed over
non-OOS, non-promo weeks. If the neighbor pool draws from a wider population (all non-OOS weeks,
including promos), the rolling median and the seasonal index no longer represent the same
population, and the correction is biased upward for OOS periods near promotions. (session history)

This rule was recorded in DECISIONS.md after the fix: the rolling-median neighbor pool must be
restricted to non-promo weeks to match the seasonal index exclusion rules.

## Prevention

**1. Add an OOS-adjacent-to-promo test fixture.**

The bug only triggers when OOS and promo windows are adjacent or concurrent. Add a fixture that
exercises this combination and asserts `true_demand` approximates the non-promo baseline:

```python
def test_oos_correction_excludes_adjacent_promo_week():
    # Sparse neighbors: only 1 baseline week (100) and 1 promo week (180) before OOS.
    # Buggy path: neighbors = [100, 180] -> median = 140.0
    # Fixed path: neighbors = [100]      -> median = 100.0
    data = pd.DataFrame({
        "week_ending": pd.date_range("2025-01-01", periods=4, freq="W"),
        "units_sold":  [100, 180, 0, 0],
        "is_oos":      [False, False, True, True],
        "is_promo":    [False, True, False, False],
        "store_id":    ["STORE-01"] * 4,
        "sku":         ["CHP-AS-001"] * 4,
    })
    result = _correct_group(data, seasonal_index={})
    oos_corrections = result.loc[result["is_oos"], "true_demand"]
    assert oos_corrections.mean() < 120  # buggy path gives 140; fixed gives 100
```

**2. Audit neighbor-selection logic against seasonal-index exclusion rules.**

Whenever `_compute_seasonal_index()` excludes a week category (promos, distribution gaps,
holidays), verify that the same category is excluded from the neighbor pool. Treat the seasonal
index exclusion list as the authoritative filter for "what counts as a normal week."

**3. When adding a new boolean flag column to scan data, audit every aggregation site.**

Adding `is_promo` to `get_scan_data()` affects neighbor selection, seasonal index computation,
and the forecast pipeline. For each new flag, grep for every location that selects or aggregates
"non-OOS weeks" and decide explicitly whether the flag should be excluded there too.

## Related Issues

- `docs/solutions/logic-errors/kpi-as-of-date-demo-data-past-due-2026-05-31.md` — Another
  silent correctness error in the analytics layer that produced no callback exceptions. Both
  bugs produced plausible-looking numbers that only surfaced when cross-checked against external
  ground truth.
