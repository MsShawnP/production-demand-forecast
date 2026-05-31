# production-demand-forecast — Failure Log

What was attempted that didn't work, why it didn't work, and what was
tried next.

Lower bar than DECISIONS.md — capture failures even when they didn't
produce a durable rule. The whole point: future-you (or future-Claude)
shouldn't re-attempt dead ends because the lesson got lost.

---

## Format

### YYYY-MM-DD — [One-line failure description]

**Attempted:** [What was tried]

**Why it didn't work:** [Concrete reason]

**What we tried instead:** [The next attempt]

**Status:** Resolved / open / abandoned

**Tags:** [keywords]

---

## Entries

### 2026-05-31 — Deadline flag tests failed because analytics used real today(), not test date

**Attempted:** Wrote `compute_decision_deadline()` using `pd.Timestamp.today()` to compute `days_until_deadline`. Tests used a fixed `TODAY = pd.Timestamp("2025-11-01")` for all stockout/deadline fixtures.

**Why it didn't work:** Test dates were in the past relative to actual today (2026-05-31), so every deadline was flagged `PAST_DUE` regardless of the intended scenario.

**What we tried instead:** Added `as_of_date: pd.Timestamp | None = None` parameter to `compute_decision_deadline()`, defaulting to `pd.Timestamp.today()`. Tests pass the fixed `TODAY` as `as_of_date`. Production calls omit the parameter and get real today.

**Status:** Resolved

**Tags:** analytics, testing, date-sensitive, capacity

---

### 2026-05-31 — .env.example blocked by .gitignore

**Attempted:** Created `.env.example` as a template file for environment variables, then tried to `git add` it.

**Why it didn't work:** `.gitignore` had `.env.*` which matched `.env.example`. Git refused to stage it.

**What we tried instead:** Added `!.env.example` exception to `.gitignore` immediately above `.env.*`. Template files should always have an explicit negation in the gitignore.

**Status:** Resolved

**Tags:** git, gitignore, env

---

### 2026-05-31 — Git Bash /tmp ≠ Python /tmp on Windows; Flask cache not cleared

**Attempted:** Cleared the Flask FileSystemCache by running `rm -rf /tmp/demand-forecast-cache` in Git Bash, then restarted the server expecting a fresh cache.

**Why it didn't work:** On Windows, Git Bash maps `/tmp` to `C:\Users\mssha\AppData\Local\Temp`, but Python (running as a native Windows process) resolves `/tmp` to `C:\tmp`. The cache was stored at `C:\tmp\demand-forecast-cache`; Bash was clearing a different directory. Stale empty DataFrames persisted across restarts and caused the app to show "No data" for the full 1-hour cache TTL.

**What we tried instead:** Called `cache.clear()` from within a Python script using `from app.run import server; with server.app_context(): cache.clear()`. Also verified the actual path via `cache.cache._path`.

**Status:** Resolved

**Tags:** windows, flask-caching, cache, filesystem, /tmp, debug

---

### 2026-05-31 — seed_copack.py DDL runner broke on semicolons inside SQL comments

**Attempted:** `_run_ddl()` split the schema SQL on `;` and executed each chunk as a statement. One comment line read `-- velocities; see HANDOFF.md calibration note.` — the semicolon inside the comment caused the split to produce a chunk starting with `see HANDOFF.md...`, which psycopg2 rejected with `SyntaxError: syntax error at or near "see"`.

**Why it didn't work:** `str.split(";")` doesn't understand SQL syntax — it splits on every semicolon, including those inside `--` line comments.

**What we tried instead:** Strip all `--` line comments via `re.sub(r"--[^\n]*", "", ddl)` before splitting on `;`. The stripped copy is used only to decide whether a chunk has real SQL; the original chunk (with comments intact) is passed to `cur.execute()`.

**Status:** Resolved

**Tags:** sql, seed, ddl, comments, psycopg2, parsing

---

### 2026-05-31 — get_scan_data() full load timed out and cached an empty DataFrame

**Attempted:** `get_scan_data()` with no SKU filter loaded all 1.4M rows from `scan_data` (3 years of data) with a correlated EXISTS subquery on `promotions` for every row. The `statement_timeout=30000` in `db.py` killed the query at 30s; the `except Exception` block silently returned `pd.DataFrame()`, which Flask-Caching then stored for the 1-hour `_DEMAND_CACHE_TTL`.

**Why it didn't work:** 1.4M rows × EXISTS subquery = ~40s. Timeout hit, exception swallowed, empty result cached. Every subsequent call returned the cached empty immediately, making the bug invisible.

**What we tried instead:** Two fixes: (1) added `WHERE s.week_ending <= %(as_of)s` using `_DEMO_AS_OF_DATE = "2025-11-01"` to cut the dataset to 840K rows (~26s); (2) bumped `statement_timeout` from 30s to 90s in `db.py` to give headroom. First load after cache clear still takes ~60s total (SQL + OOS correction + forecast).

**Status:** Resolved — but 26s query is still slow. Consider pre-warming cache at startup or replacing EXISTS with a CTE join for a future pass.

**Tags:** performance, timeout, flask-caching, scan_data, silent-failure, psycopg2
