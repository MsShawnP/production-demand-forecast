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
