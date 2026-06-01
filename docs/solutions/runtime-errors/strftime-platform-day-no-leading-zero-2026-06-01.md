---
title: "Python strftime %-d: Linux-Only No-Leading-Zero Day Format"
date: 2026-06-01
category: docs/solutions/runtime-errors/
module: app/data.py, app/tabs/sop_view.py
problem_type: runtime_error
component: tooling
severity: high
symptoms:
  - "ValueError: Invalid format string raised on Windows when formatting date strings"
  - "App runs correctly on Linux and WSL but crashes on Windows in date-display paths"
  - "%-d strftime specifier accepted silently on Linux but rejected by Windows CRT"
  - "Affected both PDF export (_fmt_date_pdf) and S&OP view week-label (_format_date)"
root_cause: wrong_api
resolution_type: code_fix
tags:
  - strftime
  - windows-portability
  - cross-platform
  - date-formatting
  - python
  - dash
  - runtime-crash
  - platform-difference
---

# Python strftime %-d: Linux-Only No-Leading-Zero Day Format

## Problem

Python's `strftime` format specifier `%-d` (day without leading zero) is a POSIX extension not
implemented by the Windows C runtime. On Linux and macOS, `strftime("%-d")` returns `"5"` for
the 5th day of the month. On Windows, the same call raises `ValueError: Invalid format string`
at runtime.

The production-demand-forecast app used `%-d` in two private date-formatting helpers:
`_fmt_date_pdf()` in `app/data.py` (PDF export path) and `_format_date()` in
`app/tabs/sop_view.py` (S&OP view week labels). Both functions were written on Linux and failed
silently on the developer's Windows machine until Windows testing was attempted.

## Symptoms

- `ValueError: Invalid format string` raised when any callback path invokes `_fmt_date_pdf()`
  or `_format_date()` on Windows.
- Error surfaces only when the affected callback is triggered (PDF export or S&OP grid
  rendering), not on app startup.
- No error on Linux or macOS — the same code path executes silently and produces the expected
  output.
- No static analysis or linter flags the issue; `%-d` is syntactically valid in Python string
  literals on all platforms.
- The `/improve` audit originally classified this as a "silent" Windows failure — the app did
  not crash on start, only on the specific callback path. (session history)

## What Didn't Work

**`%d`** — returns a zero-padded string (`"05"` instead of `"5"`). Different output from the
intended format; not a drop-in replacement.

**`strftime("%-d").lstrip("0")`** — verbose, and the `strftime("%-d")` call still raises
`ValueError` on Windows before `.lstrip()` is reached. This solves the wrong half of the
problem.

No failing test surfaced the bug — `_fmt_date_pdf()` and `_format_date()` are private helpers
called through the grid and export callbacks. No test exercised them directly.

## Solution

Replace `%-d` with `ts.day`, a plain integer attribute on `pd.Timestamp`. No leading zero,
no platform dependency, identical output to what `%-d` produced on Linux.

**`app/data.py` — `_fmt_date_pdf()`:**

```python
# Before (Linux-only):
return ts.strftime("%-d %b %Y")   # e.g. "5 Feb 2025"

# After (cross-platform):
return str(ts.day) + ts.strftime(" %b %Y")   # same output, works everywhere
```

**`app/tabs/sop_view.py` — `_format_date()`:**

```python
# Before (Linux-only):
return ts.strftime("Wk %-d %b")        # e.g. "Wk 5 Feb"

# After (cross-platform):
return "Wk " + str(ts.day) + ts.strftime(" %b")   # e.g. "Wk 5 Feb", works everywhere
```

The approach: pull the platform-dependent component (`%-d`) out of the format string entirely.
`strftime()` handles only the portable parts (month abbreviation, year). `str(ts.day)` produces
the no-leading-zero integer directly.

## Why This Works

`pd.Timestamp.day` (and equivalently `datetime.day`) is a Python integer attribute. It carries
no formatting behavior — it is the day-of-month as a plain `int`. `str(ts.day)` on day 5
produces `"5"`; on day 15 it produces `"15"`. No OS-level format string interpretation, no
platform flag, and no leading zero. The output is identical to what `%-d` produced on Linux.

## Prevention

Audit any Python codebase targeting both Windows and Linux for the minus-flag `strftime`
variants. None work on Windows:

```bash
grep -rn "strftime.*%-[dmHMS]" .
```

The full set of Linux-only minus-flag directives:

| Directive | Meaning |
|---|---|
| `%-d` | Day of month, no leading zero |
| `%-m` | Month number, no leading zero |
| `%-H` | Hour (24h), no leading zero |
| `%-M` | Minute, no leading zero |
| `%-S` | Second, no leading zero |

The portable replacement pattern for any of these: extract the corresponding `datetime` /
`Timestamp` attribute (`.day`, `.month`, `.hour`, `.minute`, `.second`) and compose the
surrounding format string in a separate `strftime()` call that contains only portable
directives.

`datetime.date` and `datetime.datetime` expose the same `.day`, `.month`, etc. attributes as
`pd.Timestamp` — the fix pattern applies equally to standard-library datetime objects.

## Related Issues

- `docs/solutions/logic-errors/kpi-as-of-date-demo-data-past-due-2026-05-31.md` — another
  date-handling bug in `app/data.py` where a date value produced silent wrong output with no
  exception in the expected environment. Both bugs illustrate how date/time code can silently
  misbehave across platform or time-context boundaries.
