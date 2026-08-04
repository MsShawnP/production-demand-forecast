# Production Demand Forecast

S&OP for specialty food brands using co-packers: corrects POS velocity for out-of-stock periods, forecasts 12 weeks of demand per SKU, and turns co-packer lead times into a production decision deadline.

**Narrative:** "You'll run out in week 9. The deadline was week 3."

**Live:** https://forecast.lailarallc.com

## What it does

- **Corrects observed velocity for out-of-stock periods** using a seasonal index, so the forecast reflects true demand rather than suppressed sales
- **Builds a 12-week rolling demand forecast by SKU** (STL decomposition)
- **Overlays co-packer capacity and lead-time constraints** on the forecast
- **Outputs a stockout date plus a production decision deadline per SKU** — the date by which a production order must be placed, not just the date the shelf goes empty
- **Exports** to Excel (openpyxl) and PDF (WeasyPrint + Jinja2)

## Why it matters

Most demand forecasts for co-packer-dependent brands are wrong for a structural reason: stockouts suppress observed velocity, and a forecast built on that suppressed data under-predicts demand, which guarantees the next stockout. This tool breaks that doom loop by correcting observed velocity before forecasting.

The second failure mode is timing. A forecast that says "you'll run out in week 9" is useless if the co-packer needs six weeks of lead time — the real deadline was week 3. Connecting the forecast to production constraints converts a projection into a decision with a date on it, which is what a founder can actually act on.

**Demonstration case:** the app's hero case is CHP-PS-008 (Italian Seasoning Blend), a Pantry Staples SKU that sits out of stock across the retail network for most of the observed window — the persistent, low-grade OOS that silently understates true demand. The per-week velocity correction is real but modest, and it compounds: a stocked-out Artisan Sauce store-week (CHP-AS-001), for example, corrects from an observed ~4.2 to a true ~5.0 units/store/week (+19.0%), and those hidden units accumulate across every dark store-week. Demo is anchored to a reference date of 2025-11-01. Data is synthetic (Cinderhaven, a fictional specialty food brand).

## Quick start

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

Run the tests — 60 unit and integration tests covering the analytics pipeline (OOS correction, rolling forecast, capacity overlay) and the data query layer:

```bash
pytest tests/
```

### Seeding the co-packer schema

The Cinderhaven Postgres SSOT is read-only from this app except for the co-packer tables (`co_packers`, `production_lines`, `production_schedule`, `sku_production_config`, `sku_inventory`). Run `python db/seed_copack.py` once against any Cinderhaven database, and re-run it if the database is recreated.

### Deploying

```bash
fly launch --no-deploy
fly secrets set DATABASE_URL="postgres://..." FLASK_SECRET_KEY="$(openssl rand -hex 32)"
fly volumes create cache_vol --size 1 --region iad
fly deploy
fly open /health
```

After deploy, `fly ssh console` and verify WeasyPrint works in the container: `python -c "import weasyprint; print('WeasyPrint OK')"`.

## Tech stack

- **UI:** Python + Dash 3.x + Plotly + dash-ag-grid
- **Analytics:** `app/analytics/` — OOS correction (seasonal index), rolling forecast (STL), capacity overlay
- **Database:** Cinderhaven Data Platform (synthetic Postgres SSOT)
- **Export:** Excel via openpyxl, PDF via WeasyPrint + Jinja2
- **Deployment:** Fly.io (python:3.13-slim, gunicorn, 2 GB)

## Data contract

Canonical Cinderhaven conformance — 50 SKUs across 5 product lines and 6 contracted retailers. This tool uses an S&OP subset of the full Cinderhaven dataset; the narrower SKU/retailer scope is intentional, not data drift.

## Client engagement use

The demo renders the live Cinderhaven dataset. To forecast a **client's own
demand** from their sell-through history — validated, never committed, never
deployed — use client mode (see [INPUT-SPEC.md](INPUT-SPEC.md)):

```bash
pip install -e ../engagement-template/lib      # the shared lailara_engagement scaffold
python client_mode.py --config engagement.yml --input client-data/demand.csv \
    --out client-output [--final]
```

It forecasts each SKU forward `horizon_weeks` from the config `as_of_date` (never
the wall clock) using the **same engine** the demo uses (`build_rolling_forecast`,
STL or rolling-mean per SKU). Output to `client-output/` (gitignored): a branded,
provenance-footed, DRAFT-watermarked `demand-forecast-summary.html` + `summary.json`,
or a Data Readiness Report if a required column is missing. The demo app is never
edited (golden-locked).

## License

MIT — see [LICENSE](LICENSE).

---

Built by [Lailara LLC](https://lailarallc.com) — data hygiene and analytics consulting for specialty food brands scaling into national retail.
