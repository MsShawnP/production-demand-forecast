# Production Demand Forecast

A Lailara LLC portfolio piece demonstrating S&OP (Sales & Operations Planning) for specialty food
brands using co-packers. The tool corrects POS velocity for out-of-stock periods, builds a 12-week
rolling demand forecast by SKU, overlays co-packer capacity and lead-time constraints, and outputs
a stockout date plus production decision deadline per SKU.

**Narrative:** "You'll run out in week 9. The deadline was week 3."

**Live:** https://forecast.lailarallc.com

## What it does

Most demand forecasts for co-packer-dependent brands are wrong for a structural reason: stockouts
suppress observed velocity, and a forecast built on that suppressed data under-predicts demand,
which guarantees the next stockout. This tool breaks that doom loop by correcting observed velocity
for out-of-stock periods before forecasting, then connecting the forecast to co-packer lead times
to produce actionable decision deadlines — not just projected demand.

## Data Contract

**Cinderhaven canonical dataset:** 50 SKUs / 5 production lines / 6 retailers.
**Scope:** This tool addresses production planning and demand forecasting for co-packer operations. It uses an S&OP subset of the full Cinderhaven dataset. Audits should not flag the narrower SKU/retailer scope as data drift.

## Stack

- **UI:** Python + Dash 3.x + Plotly + dash-ag-grid
- **Analytics:** `app/analytics/` — OOS correction (seasonal index), rolling forecast (STL), capacity overlay
- **Database:** Cinderhaven Data Platform (synthetic Postgres SSOT)
- **Deployment:** Fly.io (python:3.13-slim, gunicorn 3 workers, 2 GB)
- **Export:** Excel via openpyxl, PDF via WeasyPrint + Jinja2

## How to run locally

```bash
# Install dependencies
pip install -r requirements.txt

# Set environment variables
cp .env.example .env
# Edit .env — set DATABASE_URL to the Cinderhaven Postgres connection string

# Seed co-packer schema (first time only)
python db/seed_copack.py

# Start the app
gunicorn --bind 0.0.0.0:8050 --workers 1 --timeout 120 app.run:server

# Or with the dev reload flag
python -m app.run
```

The app runs at http://localhost:8050.

## How to run tests

```bash
pytest tests/
```

54 unit and integration tests covering the analytics pipeline (OOS correction, rolling forecast,
capacity overlay) and the data query layer.

## How to deploy

```bash
# First-time setup
fly launch --no-deploy
fly secrets set DATABASE_URL="postgres://..." FLASK_SECRET_KEY="$(openssl rand -hex 32)"
fly volumes create cache_vol --size 1 --region iad

# Deploy
fly deploy

# Verify
fly open /health
```

After deploy, run `fly ssh console` and verify WeasyPrint works in the container:

```bash
python -c "import weasyprint; print('WeasyPrint OK')"
```

## Seeding the co-packer schema

The Cinderhaven Postgres SSOT is read-only from this app except for four co-packer tables
(`co_packers`, `production_lines`, `production_schedule`, `sku_production_config`, `sku_inventory`).
Run the seeding script once against any Cinderhaven database:

```bash
python db/seed_copack.py
```

If the Cinderhaven Postgres is recreated, re-run the seeding script before starting the app.

## Data contract

Canonical Cinderhaven conformance — 50 SKUs across 5 product lines and 6 contracted retailers.

## Case study

Uses Cinderhaven (a synthetic specialty food brand) as the demonstration case. Data is synthetic.
The demo is anchored to a reference date of 2025-11-01. The Artisan Sauce hero SKU (CHP-AS-001)
shows a February 2025 out-of-stock event where observed velocity was ~4.2 units/store/week
and true demand corrects to ~5.0 units/store/week (+18%).

---

Built by [Lailara LLC](https://lailarallc.com) — data hygiene and analytics consulting for specialty food brands scaling into national retail.
