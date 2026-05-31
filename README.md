# Production Demand Forecast

A Lailara LLC portfolio piece demonstrating S&OP (Sales & Operations Planning) for specialty food
brands using co-packers. The tool corrects POS velocity for out-of-stock periods, builds a 12-week
rolling demand forecast by SKU, overlays co-packer capacity and lead-time constraints, and outputs
a stockout date plus production decision deadline per SKU.

**Narrative:** "You'll run out in week 9. The deadline was week 3."

## What it does

Most demand forecasts for co-packer-dependent brands are wrong for a structural reason: stockouts
suppress observed velocity, and a forecast built on that suppressed data under-predicts demand,
which guarantees the next stockout. This tool breaks that doom loop by correcting observed velocity
for out-of-stock periods before forecasting, then connecting the forecast to co-packer lead times
to produce actionable decision deadlines — not just projected demand.

## How to run

[Fill in after stack is decided and project is built.]

## Stack

TBD — to be decided during initial scoping.

## Case study

Uses Cinderhaven (a synthetic specialty food brand) as the demonstration case. Data is synthetic.
