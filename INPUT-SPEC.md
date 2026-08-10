# INPUT-SPEC — production-demand-forecast (client mode)

What to hand the tool in a client engagement. One sell-through history file (one
row per store × SKU × week), CSV or XLSX. Derived from the forecast engine
(`app/analytics/forecast.py::build_rolling_forecast`), not the README.

## Required columns

| Canonical | Type | Used for |
|---|---|---|
| `store_id` | identifier (text) | Store id — the forecast is built from per-store velocity across physical stores. §1 |
| `sku` | identifier (text) | SKU code. §1 |
| `week_ending` | date | Week-ending date of the sell-through (mixed formats disclosed, then normalized). §1 |
| `true_demand` | number ≥ 0 | Units sold/demanded that store-week. §1 |

## Window (engagement.yml)

```yaml
as_of_date: "2025-11-01"          # forecast-from anchor; NEVER today's date
basis:
  horizon_weeks: 12               # forecast horizon
  window_label: "12-week horizon"
```

The forecast projects `horizon_weeks` forward from `as_of_date` (the analysis
anchor is always explicit — the engine never falls back to the wall clock). Each
SKU's method is chosen automatically (STL when there's enough history, rolling
mean otherwise).

## Run

```bash
pip install -e ../engagement-template/lib
python client_mode.py --config engagement.yml --input client-data/demand.csv \
    --out client-output [--final]
```

Output to `client-output/` (gitignored): a branded, provenance-footed,
DRAFT-watermarked `demand-forecast-summary.html` (projected units by SKU over the
horizon, with the forecast method) + `json/summary.json`; or a Data Readiness
Report if a required column is missing. The demo Dash app is never edited.
