# Test conventions for production-demand-forecast `tests/`

This file applies when Claude is working in `tests/`.

## What gets tested

- The OOS correction logic — this is the analytical core; it must be correct.
- The decision deadline calculation — getting this wrong misleads the ops lead.
- Edge cases: zero-sale windows longer than 3 weeks, SKUs with no historical velocity,
  lead times longer than the forecast horizon.
- Anything in FAILURES.md that has a corresponding fix in code.

## What doesn't need a test

- Glue code (one-line wrappers, trivial mappings).
- Configuration constants.
- Pure type definitions.

## Structure

- Mirror the source tree: `src/foo/bar.py` → `tests/foo/test_bar.py`.
- One file per source module unless tests are huge.
- Group related tests by behavior, not by function name.

## Test names

- Pattern: `test_<behavior>_when_<condition>`
- Good: `test_oos_correction_uses_pre_post_median`, `test_decision_deadline_subtracts_lead_time`
- Bad: `test_function_1`, `test_correction`

## Key test cases to cover (fill in as built)

- OOS correction produces `true_demand > observed_velocity` when stockout is present
- OOS correction does NOT modify weeks with no stockout
- Decision deadline = stockout_date - lead_time (in weeks)
- Shared-line conflict is detected when two deadlines overlap on the same line
- 12-week forecast window covers full lead-time range

## Mocks and fakes

- Mock at the boundary (network, filesystem, time), not internal pure functions.
- Synthetic Cinderhaven data is the test fixture — do not use real brand data in tests.

## Running

- Tests must be runnable with a single command. Document it in README.md once stack is decided.

## When a test fails

- Read the actual output, not what you expected to see.
- Bisect: which change broke it?
- Don't suppress with `skip` or `xfail` without an issue or PLAN item to come back.
