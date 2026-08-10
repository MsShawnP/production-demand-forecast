"""Client-mode CLI for production-demand-forecast.

Forecast a client's demand from their own sell-through history using the same
engine the demo uses (build_rolling_forecast) — validated, never committed, never
deployed. The demo Dash app is untouched.

Usage:
    python client_mode.py --config engagement.yml --input client-data/demand.csv \
        --out client-output [--final]
"""

from __future__ import annotations

import argparse
import html
import json
import sys
from pathlib import Path

import pandas as pd

from lailara_engagement import (
    ColumnSpec,
    PreflightSpec,
    build_provenance,
    load_config,
    read_table,
    run_preflight,
    validation_status_label,
    write_report,
)
from lailara_engagement import palette as P
from lailara_engagement.provenance import Provenance

sys.path.insert(0, str(Path(__file__).resolve().parent))
from app.analytics.forecast import build_rolling_forecast  # noqa: E402

TOOL = "production-demand-forecast"
TOOL_VERSION = "1.0"


def _spec() -> PreflightSpec:
    return PreflightSpec(
        tool=TOOL, version=TOOL_VERSION,
        columns=[
            ColumnSpec(name="store_id", dtype="identifier", required=True,
                       description="store id (physical stores drive velocity)", spec_ref="INPUT-SPEC §1"),
            ColumnSpec(name="sku", dtype="identifier", required=True,
                       description="SKU code", spec_ref="INPUT-SPEC §1"),
            ColumnSpec(name="week_ending", dtype="date", required=True,
                       description="week-ending date of the sell-through", spec_ref="INPUT-SPEC §1"),
            ColumnSpec(name="true_demand", dtype="number", required=True, not_negative=True,
                       description="units sold/demanded that week", spec_ref="INPUT-SPEC §1"),
        ],
    )


def run(config_path: str, input_path: str, out_dir: str, *, final: bool = False) -> dict:
    config = load_config(config_path)
    read = read_table(input_path)
    report = run_preflight(read, _spec(), config)

    out = Path(out_dir)
    out.mkdir(parents=True, exist_ok=True)
    provenance = build_provenance(
        tool=TOOL, tool_version=TOOL_VERSION, inputs=[read], config=config,
        validation_status=validation_status_label(report.status, report.n_warnings))
    if not report.passed:
        paths = write_report(report, config, str(out), provenance=provenance,
                             draft=not final, basename="data-readiness-report",
                             title="Demand-History Data Readiness Report")
        return {"status": "blocked", "readiness_report": paths["html"]}

    m = report.column_mapping
    # Normalize week_ending to ISO (the preflight already discloses mixed formats;
    # the forecast engine expects parseable dates). Unparseable rows are dropped.
    weeks = pd.to_datetime(read.frame[m["week_ending"]], format="mixed", errors="coerce")
    df = pd.DataFrame({
        "store_id": read.frame[m["store_id"]].astype(str),
        "sku": read.frame[m["sku"]].astype(str),
        "week_ending": weeks.dt.strftime("%Y-%m-%d"),
        "true_demand": pd.to_numeric(read.frame[m["true_demand"]], errors="coerce").fillna(0.0),
    })
    df = df[df["week_ending"].notna()]

    n_weeks = int(config.basis.get("horizon_weeks") or 12)
    forecast_from = config.as_of_date.isoformat()
    fc = build_rolling_forecast(df, forecast_from_week=forecast_from, n_weeks=n_weeks)

    if fc is None or len(fc) == 0 or "sku" not in fc.columns:
        fc = pd.DataFrame(columns=["sku", "week_ending", "forecast_units", "is_projected", "forecast_method"])
    proj = fc[fc["is_projected"]] if "is_projected" in fc.columns and len(fc) else fc
    by_sku = (proj.groupby("sku")
              .agg(forecast_units=("forecast_units", "sum"),
                   method=("forecast_method", lambda s: s.iloc[0] if len(s) else ""))
              .reset_index()
              .sort_values("forecast_units", ascending=False))
    total = float(proj["forecast_units"].sum()) if len(proj) else 0.0

    summary = {
        "window": {"forecast_from": forecast_from, "horizon_weeks": n_weeks,
                   "label": config.basis.get("window_label", "")},
        "sku_count": int(by_sku["sku"].nunique()),
        "total_forecast_units": round(total, 1),
        "by_sku": [{"sku": r["sku"], "forecast_units": round(float(r["forecast_units"]), 1),
                    "method": str(r["method"])} for _, r in by_sku.iterrows()],
    }
    json_dir = out / "json"; json_dir.mkdir(parents=True, exist_ok=True)
    (json_dir / "summary.json").write_text(json.dumps(summary, indent=2), encoding="utf-8")
    report_path = out / "demand-forecast-summary.html"
    report_path.write_text(_summary_html(config, summary, provenance, draft=not final), encoding="utf-8")
    return {"status": "ok", "sku_count": summary["sku_count"],
            "total_forecast_units": summary["total_forecast_units"], "report": str(report_path),
            "summary_json": str(json_dir / "summary.json"), "n_warnings": report.n_warnings}


def _summary_html(config, s, provenance: Provenance, *, draft: bool) -> str:
    esc = html.escape
    w = s["window"]
    wl = w.get("label") or ""
    rows = "".join(
        f"<tr><td>{esc(r['sku'])}</td><td class=num>{r['forecast_units']:,.1f}</td>"
        f"<td>{esc(r['method'])}</td></tr>"
        for r in s["by_sku"])
    return f"""<!doctype html><html lang=en><head><meta charset=utf-8>
<meta name=viewport content="width=device-width, initial-scale=1">
<title>Demand Forecast — {esc(config.client_name)}</title><style>{_css(draft)}</style></head>
<body class="{' ll-draft' if draft else ''}"><main class=ll-page>
<header class=ll-header>
  <div class=ll-eyebrow>Lailara LLC · Demand Forecast</div>
  <h1 class=ll-title>{w['horizon_weeks']}-Week Demand Forecast</h1>
  <div class=ll-client>
    <div><span class=ll-k>Client</span> {esc(config.client_name)}</div>
    <div><span class=ll-k>Engagement</span> {esc(config.engagement_id)}</div>
    <div><span class=ll-k>Forecast from</span> {esc(w['forecast_from'])}</div>
    <div><span class=ll-k>Horizon</span> {w['horizon_weeks']} weeks{(' · ' + esc(wl)) if wl else ''}</div>
  </div>
</header>
<section class=ll-banner>
  <div class=ll-score>{s['total_forecast_units']:,.0f} units forecast</div>
  <div>across {s['sku_count']} SKUs over the next {w['horizon_weeks']} weeks
       from {esc(w['forecast_from'])}</div>
</section>
<section class=ll-section>
  <h2 class=ll-h2>Forecast by SKU</h2>
  <table class=ll-table><thead><tr><th>SKU</th><th>Forecast units</th><th>Method</th></tr></thead>
  <tbody>{rows}</tbody></table>
  <p class=ll-note>Projected units summed over the {w['horizon_weeks']}-week horizon from
  {esc(w['forecast_from'])} (config as_of_date, never the wall clock). Method is chosen
  per SKU (STL when enough history, rolling mean otherwise).</p>
</section>
{provenance.to_html()}
</main></body></html>"""


def _css(draft: bool) -> str:
    draft_css = (
        ".ll-draft::before{content:'DRAFT';position:fixed;top:50%;left:50%;"
        "transform:translate(-50%,-50%) rotate(-32deg);font-family:var(--s);"
        "font-size:22vw;font-weight:700;color:rgba(204,16,10,.06);z-index:0;"
        "pointer-events:none;white-space:nowrap}" if draft else ""
    )
    return f"""
:root{{--s:{P.LL_SERIF};--f:{P.LL_SANS}}}*{{box-sizing:border-box}}
body{{margin:0;background:{P.LL_CANVAS};color:{P.LL_TEXT};font-family:var(--f);line-height:1.6}}
.ll-page{{position:relative;z-index:1;max-width:{P.LL_MAX_WIDTH};margin:0 auto;padding:48px 24px}}
.ll-header{{border-bottom:1px solid {P.LL_GRIDLINE};padding-bottom:24px;margin-bottom:24px}}
.ll-eyebrow{{font-size:12px;letter-spacing:.04em;text-transform:uppercase;color:{P.LL_RED};font-weight:600}}
.ll-title{{font-family:var(--s);font-weight:700;color:{P.LL_INK};font-size:34px;margin:8px 0 16px}}
.ll-client{{display:grid;grid-template-columns:repeat(auto-fit,minmax(160px,1fr));gap:8px 24px;font-size:14px}}
.ll-k{{display:block;color:{P.LL_TEXT_SEC};font-size:11px;text-transform:uppercase;letter-spacing:.04em}}
.ll-banner{{border-radius:2px;padding:16px 20px;margin-bottom:32px;background:{P.LL_HK_SURFACE};color:{P.LL_HK_DARK}}}
.ll-score{{font-family:var(--s);font-weight:700;font-size:22px}}
.ll-section{{margin:0 0 32px}}
.ll-h2{{font-family:var(--s);font-weight:700;color:{P.LL_INK};font-size:22px;
margin:0 0 12px;padding-bottom:6px;border-bottom:1px solid {P.LL_GRIDLINE}}}
.ll-note{{font-size:13px;color:{P.LL_TEXT_SEC};margin-top:8px}}
.ll-table{{width:100%;border-collapse:collapse;font-size:14px}}
.ll-table th{{text-align:left;background:{P.LL_CHICAGO};color:#fff;padding:8px 12px}}
.ll-table td{{padding:8px 12px;border-bottom:1px solid {P.LL_GRIDLINE}}}
.num{{text-align:right;font-variant-numeric:tabular-nums}}
.ll-provenance{{margin-top:40px;background:{P.LL_CARD_BG};color:{P.LL_CARD_TEXT};
padding:20px 24px;border-radius:2px;font-size:13px}}
.ll-prov-title{{font-family:var(--s);font-weight:700;font-size:16px;margin-bottom:8px}}
.ll-provenance div{{margin-bottom:4px;color:{P.LL_CARD_SUBTITLE}}}
.ll-provenance strong{{color:{P.LL_CARD_TEXT}}}
.ll-prov-inputs{{width:100%;border-collapse:collapse;margin-top:8px}}
.ll-prov-inputs th{{text-align:left;border-bottom:1px solid rgba(255,255,255,.12);padding:4px 8px;color:{P.LL_CARD_MUTED}}}
.ll-prov-inputs td{{padding:4px 8px;border-bottom:1px solid rgba(255,255,255,.08);color:{P.LL_CARD_SUBTITLE}}}
.ll-prov-brand{{margin-top:12px;font-family:var(--s);color:{P.LL_CARD_MUTED}}}
{draft_css}
@media print{{body{{background:#fff}}}}
"""


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(prog="production-demand-forecast client mode")
    ap.add_argument("--config", required=True)
    ap.add_argument("--input", required=True)
    ap.add_argument("--out", default="client-output")
    ap.add_argument("--final", action="store_true")
    args = ap.parse_args(argv)
    result = run(args.config, args.input, args.out, final=args.final)
    if result["status"] == "blocked":
        print(f"BLOCKED — data not ready. See {result['readiness_report']}")
        return 3
    print(f"forecast {result['total_forecast_units']:,.0f} units across {result['sku_count']} SKUs")
    print(f"report -> {result['report']}")
    return 0


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
