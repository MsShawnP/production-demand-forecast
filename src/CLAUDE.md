# Code conventions for production-demand-forecast `src/`

This file applies when Claude is working in `src/`.

## Style

- Match the existing code style. If there's a linter config, follow it strictly.
- New files mirror the structure of nearby existing files.
- No mixing of paradigms inside a module without a reason worth stating in DECISIONS.md.

## Naming

- Functions: verbs (`correct_for_oos`, `compute_decision_deadline`, `build_rolling_forecast`)
- Variables: nouns (`true_demand`, `stockout_date`, `decision_deadline`)
- Booleans: predicates (`is_oos_period`, `has_scheduled_production`)
- Avoid abbreviations unless standard — "OOS" is fine, everything else spell out.

## Domain vocabulary (use exactly these terms)

- `true_demand` — OOS-corrected velocity (not "adjusted" or "cleaned")
- `observed_velocity` — raw POS velocity before correction
- `oos_period` — out-of-stock period
- `decision_deadline` — last date to book a production run to prevent stockout
- `stockout_date` — projected date inventory reaches zero under true demand
- `lead_time` — co-packer lead time in weeks
- `min_run_size` — minimum order quantity from co-packer

## Comments

- Comment why, not what. The code already says what.
- TODO comments include a date or issue reference.

## Error handling

- Don't swallow errors. If you catch one, log or rethrow with context.
- No bare `except:` blocks without a comment explaining why.

## Don't invent

- Before adding a new utility, check if a similar one already exists.
- Before adding a dependency, ask the user (and log to DECISIONS.md).
- Before refactoring an existing pattern, surface it as a question.

## Key analytical invariants

- OOS correction MUST happen before any forecasting step — never forecast off uncorrected velocity.
- The decision deadline is computed by subtracting `lead_time` from `stockout_date`.
- A shared-line conflict exists when two SKUs with overlapping decision deadlines share the same co-packer line.
