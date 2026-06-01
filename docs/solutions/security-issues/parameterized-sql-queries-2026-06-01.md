---
title: "f-string SQL WHERE Clause: Parameterized Query Refactor"
date: 2026-06-01
category: docs/solutions/security-issues/
module: app/data.py
problem_type: security_issue
component: database
severity: high
symptoms:
  - "SQL WHERE clause built with f-string interpolation instead of parameterized binding"
  - "Function structurally unsafe to extend — future caller-controlled input would be injectable"
  - "Violates psycopg2 parameterized-query conventions used elsewhere in the codebase"
root_cause: wrong_api
resolution_type: code_fix
tags:
  - sql-injection
  - parameterized-queries
  - psycopg2
  - f-string
  - security
  - data-layer
  - get-scan-data
---

# f-string SQL WHERE Clause: Parameterized Query Refactor

## Problem

`get_scan_data(sku)` in `app/data.py` built its SQL WHERE clause using f-string interpolation,
embedding `sku` and `_DEMO_AS_OF_DATE` directly into the query string. Both values came from
internal sources — a dropdown selection and a module-level constant — so no injection was
possible at the time. The structural risk remained: if the function signature changed or data
provenance shifted, the protection assumption would break silently with no compiler warning, no
test failure, and no visible signal.

The `/improve` security reviewer flagged this as an IMPORTANT finding. Even for internal APIs,
f-string SQL is an unsafe pattern by construction.

## Symptoms

No runtime failure. The function worked correctly. The risk was latent — a refactor that passed
`sku` from a URL parameter or user-supplied input would have introduced a real injection vector
without touching the SQL logic itself. The only symptom was the pattern: f-string interpolation
in a WHERE clause.

## What Didn't Work

No alternatives were attempted. This is a single-path fix: f-string interpolation must be
replaced with parameterized queries. String escaping is not an equivalent remedy — it can be
bypassed. Structural separation of SQL and values cannot.

The bug was caught by an automated security reviewer during a `/improve` audit, not from a
runtime failure. The `get_scan_data()` function had been under active testing in an earlier
session during a timeout investigation (the correlated EXISTS subquery on promotions took 40+
seconds without the date filter), but the f-string pattern was not flagged at that time.
(session history)

## Solution

Replace the dynamically constructed SQL string with two static SQL constants — one for the
all-SKUs query, one for the single-SKU query — and pass values through psycopg2's named
parameter binding.

**Before (buggy):**

```python
# f-string interpolation — unsafe even with "trusted" values
where = f"WHERE s.week_ending <= '{_DEMO_AS_OF_DATE}'"
if sku:
    where += f" AND s.sku = '{sku}'"
sql = f"SELECT ... FROM scan_data s ... {where} ORDER BY ..."
with get_conn() as conn:
    return pd.read_sql(sql, conn)
```

**After (fixed — from `app/data.py`):**

```python
# Two static SQL strings — no f-string interpolation — so structural parts
# are never user-influenced even if the call signature changes in the future.
_SQL_ALL = """
    SELECT
        s.sku, s.store_id, s.week_ending, s.units_sold,
        CASE WHEN d.sku IS NOT NULL THEN TRUE ELSE FALSE END AS is_authorized,
        CASE
            WHEN EXISTS (
                SELECT 1 FROM promotions p
                WHERE p.sku = s.sku
                  AND s.week_ending BETWEEN p.start_week AND p.end_week
            ) THEN TRUE ELSE FALSE
        END AS is_promo
    FROM scan_data s
    LEFT JOIN distribution_log d ON d.sku = s.sku AND d.store_id = s.store_id
    WHERE s.week_ending <= %(as_of)s
    ORDER BY s.sku, s.store_id, s.week_ending
"""
_SQL_SKU = """
    ... same structure ...
    WHERE s.sku = %(sku)s AND s.week_ending <= %(as_of)s
    ORDER BY s.sku, s.store_id, s.week_ending
"""

if sku:
    sql, params = _SQL_SKU, {"sku": sku, "as_of": _DEMO_AS_OF_DATE}
else:
    sql, params = _SQL_ALL, {"as_of": _DEMO_AS_OF_DATE}
with get_conn() as conn:
    return pd.read_sql(sql, conn, params=params)
```

## Why This Works

When passed through `cursor.execute(sql, params)`, psycopg2 sends values as separate wire
protocol parameters — the SQL structure is fixed at parse time and cannot be altered by the
values regardless of their content.

Note: `pd.read_sql(sql, conn, params=params)` with a raw psycopg2 connection falls through to
an undocumented DBAPI2 fallback path in pandas 2.x and emits a `UserWarning: "Other DBAPI2
objects are not tested."` It works today because the fallback calls `cur.execute(sql, params)`
internally, but this path is not officially supported. The production fix should eventually
switch to `cursor.execute()` directly (see Prevention) or wrap the connection in a SQLAlchemy
engine.

Static SQL strings also make the queries easier to read, audit, and test in isolation — the
full query is visible without tracing string concatenation.

The original code was safe in the narrow sense that `sku` came from an internal dropdown and
`_DEMO_AS_OF_DATE` was a module constant. "Safe today" is not the same as "safe by
construction." Parameterized queries with static SQL are safe regardless of how data provenance
changes in future refactors.

The two-constant approach (`_SQL_ALL`, `_SQL_SKU`) is intentionally duplicated. A single
parameterized template with a conditional WHERE fragment would require rebuilding dynamic SQL
construction — which is exactly the pattern this fix eliminates. Accept the duplication; do not
try to DRY it into a single string.

## Prevention

Never use f-strings or `.format()` to construct SQL, even with values you control today.

**psycopg2 — prefer `cursor.execute()` directly:**
```python
with get_conn() as conn:
    with conn.cursor() as cur:
        cur.execute(sql, {"sku": sku, "as_of": as_of_date})
        rows = cur.fetchall()
        cols = [d[0] for d in cur.description]
return pd.DataFrame(rows, columns=cols)
```

**SQLAlchemy (not used in this project — shown for reference):**
```python
from sqlalchemy import text
stmt = text("SELECT ... WHERE id = :id").bindparams(id=value)
with engine.connect() as conn:
    df = pd.read_sql(stmt, conn)
```

**Audit pattern for existing code:**
```bash
# f-string SQL
grep -rn "f\".*WHERE\|f'.*WHERE\|WHERE.*\.format" app/

# %-style interpolation
grep -rn '"\s*%\s*(' app/ | grep -i "select\|where\|from"
```

The rule is structural, not contextual: if values are embedded in the SQL string at
construction time, the pattern is wrong. If values travel separately to the driver, the pattern
is correct.

**Load-bearing constraint:** the `_DEMO_AS_OF_DATE` filter on `week_ending` in this function
is not optional. Without it, the full scan_data query returns 1.4M rows, takes 40+ seconds,
and silently caches an empty DataFrame for one hour (per the Flask-Caching TTL). Any refactor
of `get_scan_data()` must preserve this date filter. (session history)

## Related Issues

- `app/db.py` — connection pool uses `search_path=raw,public`; all unqualified table names in
  `get_scan_data()` resolve through this search path. Any query rewrite should not add explicit
  `raw.` schema prefixes. (session history)
