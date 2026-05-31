# production-demand-forecast — Project Context for Claude

## What this project is

A Lailara LLC portfolio piece demonstrating S&OP (Sales & Operations Planning) for specialty food brands
using co-packers. The tool corrects observed POS velocity for out-of-stock periods — breaking the
"doom loop" where stockouts corrupt the forecast that was supposed to prevent them — then builds a
12-week rolling demand forecast by SKU, overlays co-packer capacity and lead-time constraints, and
outputs a stockout date plus production decision deadline per SKU. Narrative: "You'll run out in week 9.
The deadline was week 3."

Uses Cinderhaven (synthetic brand) as the case study. Targets COOs and VP Ops at $5M–$30M specialty
food brands dependent on co-packers.

**Business question this project answers:** Given current inventory, scheduled production, and true
(OOS-corrected) projected demand, which SKUs will stock out, when, and what is the last date a
production run can be ordered to prevent it?

## Tier

**Medium** — standard workflow, full state files, no gstack gates.

## Stack and tools

- Primary language: TBD
- Key packages/libraries: TBD
- Database: Cinderhaven Data Platform (synthetic data)
- Entry point: TBD

## Project files

- CLAUDE.md (this file) — permanent rules and facts
- DECISIONS.md — durable choices and reasoning
- HANDOFF.md — current session state
- PLAN.md — current work arc
- FAILURES.md — things tried that didn't work

Read PLAN.md and HANDOFF.md at session start. DECISIONS.md and
FAILURES.md as relevant.

## Voice and standards

- Economist style for all written output: sober, declarative, data-forward
- Plain English that tells the truth as the data presents it
- No marketing voice ("leverage," "synergy," "best-in-class," "unlock," "drive value")
- No hedging that softens a real finding
- Charts must be readable by non-data-scientist audiences
- Lead with the decision (stockout date + deadline), not the forecast number

## Design system

Lailara Design System v2. Full reference:
`~/projects/published/lailara-design-system/LAILARA_DESIGN_SYSTEM.md`

Key tokens: Canvas background `#f5f3ee`, Chicago navy `#1f2e7a`, HK teal `#158f75`,
Singapore orange `#ee8a2a`, Tokyo berry `#b82d4a`. Playfair Display (serif) + Source Sans 3 (sans).
Self-host fonts. SVG charts only.

## Rules

### Honesty and judgment

- Say "I don't know" or "I can't verify this" instead of guessing.
- Tell me what I need to hear, not what I want to hear. If a decision looks wrong, say so.
- If a rule in this file is too vague to verify whether you're following it, flag it for revision.

### Building and proposing

- No speculative abstractions. If something isn't needed right now, don't build it.
- When proposing a tool, library, or approach, present at least two alternatives with tradeoffs.
- Tie proposals back to the business question this project is answering.
- Keep the forecasting method pragmatic — the value is the OOS correction and capacity overlay,
  not forecast-algorithm sophistication. Resist the temptation to reach for complex models.

### How to work the project

- Work in vertical slices, not horizontal phases.
- When a feature is working, suggest a simple test to verify it stays working.
- Do not start tasks outside the current PLAN.md arc without flagging it first.
- Do not refactor unrelated code unprompted.
- Do not rename things unless asked.

### Git branching

- Before risky or experimental changes, suggest creating a branch.
- Keep it simple: `git checkout -b experiment/short-description`.

### Scope creep detection

- Periodically check whether the current work matches PLAN.md.
- Flag if we've been working on something not in the plan for more than ~15 minutes.

## Working with PLAN.md

PLAN.md defines the current arc of work. Read it at session start.

- Mark tasks complete as they're finished, in the same commit as the work
- Flag wrong-sized or out-of-order tasks rather than silently restructuring
- "Out of scope" items are decisions, not suggestions

## Session reminders

### Reminding the user to /log

Prompt when: meaningful change just landed, natural pause point reached, or ~30–45 minutes since last /log.

### Reminding the user to /wrap

Prompt when: context crosses 65%, user signals stopping, natural milestone reached, or 90+ minutes and winding down.

### Session start protocol

1. Read CLAUDE.md, PLAN.md, and HANDOFF.md
2. If HANDOFF.md's most recent entry is more than 24 hours old AND there are uncommitted changes, flag it
3. Briefly state the starting point from HANDOFF.md so the user confirms you're caught up
4. Confirm the current PLAN.md arc is still active
5. Check the Improvement History section of PLAN.md
6. Remind: "type / to see commands. Main ones: /log, /wrap, /improve. Run /commands for full list."

## Defaults

- Default to flagging gaps rather than filling with plausible-sounding but unverified content
- Default to short responses unless the task is substantive
- Default to asking before promoting a log entry to a DECISIONS.md entry
- Default to answering, not offering to answer
