"""SQL query layer — full implementation (replaces U1 stub).

All public functions return DataFrames cached with @cache.memoize.
Cache is initialized in run.py via init_cache(server).

Patterns followed from competitive-shelf-intelligence/app/data.py:
- get_conn() imported inside function body (no import-time DB connections)
- @cache.memoize with per-function TTL
- every except Exception logs before returning empty DataFrame
- LEFT JOIN from product_master spine (50 SKUs) with row-count assert

Unit note:
- scan_data: units/store/week
- sku_inventory / production_schedule: cases
- capacity functions need consistent units — get_sop_summary converts cases
  to units using case_pack_qty before calling compute_stockout_date
"""

from __future__ import annotations

import logging
import os
from datetime import date, timedelta

import pandas as pd
from flask_caching import Cache

from app.analytics.capacity import (
    compute_decision_deadline,
    compute_stockout_date,
    detect_shared_line_conflicts,
)
from app.analytics.forecast import build_rolling_forecast
from app.analytics.oos_correction import correct_velocity, detect_oos_periods

cache = Cache()
logger = logging.getLogger(__name__)

_DEMO_AS_OF_DATE = "2025-11-01"   # reference date for demo stockout story
_SPINE_SKU_COUNT = 50
_SCENARIO_CACHE_TTL = 60          # seconds — scenario-keyed cache
_DEMAND_CACHE_TTL   = 3600        # 1 hour — stable demand data


def init_cache(server) -> None:
    cache_dir = os.environ.get("CACHE_DIR", "/cache")
    try:
        cache.init_app(server, config={
            "CACHE_TYPE": "FileSystemCache",
            "CACHE_DIR": cache_dir,
            "CACHE_DEFAULT_TIMEOUT": _DEMAND_CACHE_TTL,
        })
    except Exception:
        cache.init_app(server, config={
            "CACHE_TYPE": "SimpleCache",
            "CACHE_DEFAULT_TIMEOUT": _DEMAND_CACHE_TTL,
        })


# ---------------------------------------------------------------------------
# Scenario parameter validation
# ---------------------------------------------------------------------------

def _clamp_scenario(
    promo_lift_pct: float,
    new_doors: int,
    lead_time_slip_weeks: int,
) -> tuple[float, int, int]:
    """Clamp scenario params to valid ranges, log warnings for out-of-range inputs."""
    original = (promo_lift_pct, new_doors, lead_time_slip_weeks)
    promo_lift_pct    = max(0.0, min(1.0, promo_lift_pct))
    new_doors         = max(0, min(5000, new_doors))
    lead_time_slip_weeks = max(0, min(12, lead_time_slip_weeks))
    clamped = (promo_lift_pct, new_doors, lead_time_slip_weeks)
    if clamped != original:
        logger.warning("Scenario params clamped: original=%s → clamped=%s", original, clamped)
    return clamped


# ---------------------------------------------------------------------------
# Raw data queries
# ---------------------------------------------------------------------------

@cache.memoize(timeout=_DEMAND_CACHE_TTL)
def get_product_master() -> pd.DataFrame:
    """All 50 Cinderhaven SKUs from product_master."""
    from app.db import get_conn
    try:
        with get_conn() as conn:
            df = pd.read_sql(
                """
                SELECT sku, product_name, product_line, case_pack_qty
                FROM product_master
                ORDER BY sku
                """,
                conn,
            )
            if len(df) != _SPINE_SKU_COUNT:
                logger.warning("get_product_master: expected %d rows, got %d",
                               _SPINE_SKU_COUNT, len(df))
            return df
    except Exception:
        logger.exception("get_product_master failed")
        return pd.DataFrame()


@cache.memoize(timeout=_DEMAND_CACHE_TTL)
def get_scan_data(sku: str | None = None) -> pd.DataFrame:
    """Scan data with is_authorized (from distribution_log) and is_promo flags.

    LEFT JOIN from scan_data spine. Aggregate channels are included but
    flagged (store_id ends with -AGG). OOS correction excludes them.

    Row count should match product_master × authorized stores × weeks of history.
    """
    from app.db import get_conn
    try:
        where_clause = "WHERE s.sku = %(sku)s" if sku else ""
        params = {"sku": sku} if sku else {}
        with get_conn() as conn:
            return pd.read_sql(
                f"""
                SELECT
                    s.sku,
                    s.store_id,
                    s.week_ending,
                    s.units_sold,
                    s.dollars_sold,
                    CASE
                        WHEN d.sku IS NOT NULL
                             AND d.authorized_date  <= s.week_ending
                             AND (d.deauthorized_date IS NULL
                                  OR d.deauthorized_date > s.week_ending)
                        THEN TRUE
                        ELSE FALSE
                    END                                             AS is_authorized,
                    CASE
                        WHEN EXISTS (
                            SELECT 1
                            FROM promotions p
                            WHERE p.sku = s.sku
                              AND s.week_ending BETWEEN p.start_week AND p.end_week
                        ) THEN TRUE
                        ELSE FALSE
                    END                                             AS is_promo
                FROM scan_data s
                LEFT JOIN distribution_log d
                    ON d.sku = s.sku AND d.store_id = s.store_id
                {where_clause}
                ORDER BY s.sku, s.store_id, s.week_ending
                """,
                conn,
                params=params if params else None,
            )
    except Exception:
        logger.exception("get_scan_data failed")
        return pd.DataFrame()


@cache.memoize(timeout=_DEMAND_CACHE_TTL)
def get_true_demand(sku: str | None = None) -> pd.DataFrame:
    """OOS-corrected true_demand per (sku, store_id, week_ending).

    Calls detect_oos_periods() → correct_velocity() on the scan DataFrame.
    """
    scan = get_scan_data(sku=sku)
    if scan.empty:
        return pd.DataFrame()
    try:
        with_oos = detect_oos_periods(scan)
        corrected = correct_velocity(with_oos)
        return corrected
    except Exception:
        logger.exception("get_true_demand failed")
        return pd.DataFrame()


@cache.memoize(timeout=_DEMAND_CACHE_TTL)
def get_sku_inventory() -> pd.DataFrame:
    """Current on-hand inventory in cases and units (using case_pack_qty)."""
    from app.db import get_conn
    try:
        with get_conn() as conn:
            df = pd.read_sql(
                """
                SELECT
                    i.sku,
                    i.as_of_date,
                    i.on_hand_cases,
                    pm.case_pack_qty,
                    i.on_hand_cases * pm.case_pack_qty  AS on_hand_units
                FROM sku_inventory i
                JOIN product_master pm ON pm.sku = i.sku
                ORDER BY i.sku
                """,
                conn,
            )
            if len(df) != _SPINE_SKU_COUNT:
                logger.warning("get_sku_inventory: expected %d rows, got %d",
                               _SPINE_SKU_COUNT, len(df))
            return df
    except Exception:
        logger.exception("get_sku_inventory failed")
        return pd.DataFrame()


@cache.memoize(timeout=_DEMAND_CACHE_TTL)
def get_production_schedule() -> pd.DataFrame:
    """Booked production runs converted to units."""
    from app.db import get_conn
    try:
        with get_conn() as conn:
            return pd.read_sql(
                """
                SELECT
                    ps.run_id,
                    ps.sku,
                    ps.line_id,
                    ps.scheduled_week,
                    ps.quantity_cases,
                    pm.case_pack_qty,
                    ps.quantity_cases * pm.case_pack_qty  AS quantity_units,
                    ps.status
                FROM production_schedule ps
                JOIN product_master pm ON pm.sku = ps.sku
                WHERE ps.status = 'booked'
                ORDER BY ps.scheduled_week, ps.sku
                """,
                conn,
            )
    except Exception:
        logger.exception("get_production_schedule failed")
        return pd.DataFrame()


@cache.memoize(timeout=_DEMAND_CACHE_TTL)
def get_sku_config() -> pd.DataFrame:
    """Per-SKU production config with product metadata."""
    from app.db import get_conn
    try:
        with get_conn() as conn:
            df = pd.read_sql(
                """
                SELECT
                    c.sku,
                    c.line_id,
                    c.lead_time_weeks,
                    c.min_run_cases,
                    pm.product_name,
                    pm.product_line,
                    pm.case_pack_qty
                FROM sku_production_config c
                JOIN product_master pm ON pm.sku = c.sku
                ORDER BY c.sku
                """,
                conn,
            )
            if len(df) != _SPINE_SKU_COUNT:
                logger.warning("get_sku_config: expected %d rows, got %d",
                               _SPINE_SKU_COUNT, len(df))
            return df
    except Exception:
        logger.exception("get_sku_config failed")
        return pd.DataFrame()


# ---------------------------------------------------------------------------
# Scenario-keyed analytics queries
# ---------------------------------------------------------------------------

@cache.memoize(timeout=_SCENARIO_CACHE_TTL)
def get_forecast(
    promo_lift_pct: float = 0.0,
    new_doors: int = 0,
    lead_time_slip_weeks: int = 0,
) -> pd.DataFrame:
    """12-week rolling demand forecast per SKU, with scenario parameters applied."""
    promo_lift_pct, new_doors, lead_time_slip_weeks = _clamp_scenario(
        promo_lift_pct, new_doors, lead_time_slip_weeks
    )
    true_demand = get_true_demand()
    if true_demand.empty:
        return pd.DataFrame()
    try:
        forecast_from = _get_forecast_from_week(true_demand)
        return build_rolling_forecast(
            true_demand,
            forecast_from_week=forecast_from,
            promo_lift_pct=promo_lift_pct,
            new_retailer_doors=new_doors,
        )
    except Exception:
        logger.exception("get_forecast failed")
        return pd.DataFrame()


@cache.memoize(timeout=_SCENARIO_CACHE_TTL)
def get_sop_summary(
    promo_lift_pct: float = 0.0,
    new_doors: int = 0,
    lead_time_slip_weeks: int = 0,
) -> pd.DataFrame:
    """Full S&OP summary: stockout date, decision deadline, conflict flags per SKU.

    Joins forecast → inventory → production schedule through the analytics
    pipeline. lead_time_slip_weeks adds N weeks to each SKU's lead_time_weeks
    for scenario modeling.
    """
    promo_lift_pct, new_doors, lead_time_slip_weeks = _clamp_scenario(
        promo_lift_pct, new_doors, lead_time_slip_weeks
    )
    try:
        forecast = get_forecast(promo_lift_pct=promo_lift_pct, new_doors=new_doors)
        inventory = get_sku_inventory()
        schedule = get_production_schedule()
        sku_config = get_sku_config()

        if forecast.empty or inventory.empty or sku_config.empty:
            logger.warning("get_sop_summary: missing inputs — returning empty")
            return pd.DataFrame()

        # Convert inventory and schedule to units (already done by get_sku_inventory /
        # get_production_schedule using case_pack_qty in the query)
        inventory_for_cap = inventory[["sku", "on_hand_units"]].rename(
            columns={"on_hand_units": "on_hand_units"}
        )
        schedule_for_cap = (
            schedule[["sku", "line_id", "scheduled_week", "quantity_units", "status"]]
            if not schedule.empty else schedule
        )

        # Apply lead_time_slip to sku_config
        sku_config_adj = sku_config.copy()
        if lead_time_slip_weeks > 0:
            sku_config_adj["lead_time_weeks"] = (
                sku_config_adj["lead_time_weeks"] + lead_time_slip_weeks
            )

        # Step 1: stockout dates
        sop = compute_stockout_date(forecast, inventory_for_cap, schedule_for_cap)

        # Step 2: decision deadlines + flags
        sop = compute_decision_deadline(sop, sku_config_adj)

        # Step 3: shared-line conflict detection
        sop = detect_shared_line_conflicts(sop, sku_config_adj)

        # Step 4: join product metadata
        meta = sku_config_adj[["sku", "product_name", "product_line"]].copy()
        sop = sop.merge(meta, on="sku", how="left")

        if len(sop) != _SPINE_SKU_COUNT:
            logger.warning("get_sop_summary: expected %d SKUs, got %d",
                           _SPINE_SKU_COUNT, len(sop))

        return sop
    except Exception:
        logger.exception("get_sop_summary failed")
        return pd.DataFrame()


# ---------------------------------------------------------------------------
# Export helpers
# ---------------------------------------------------------------------------

def export_sop_excel(
    sop_df: pd.DataFrame,
    scenario_params: dict | None = None,
) -> bytes:
    """Render the S&OP summary as a formatted .xlsx workbook.

    Returns raw bytes suitable for dcc.Download.

    Sheet 1 "Production Decision Brief": per-SKU rows, header navy fill,
        CRITICAL/PAST_DUE rows red, WARNING rows orange.
    Sheet 2 "Scenario Parameters": records the scenario inputs + generated_at.
    """
    import io
    from datetime import datetime

    import openpyxl
    from openpyxl.styles import Font, PatternFill
    from openpyxl.utils import get_column_letter

    from app.constants import CHICAGO, SURFACE_FAIL, SURFACE_WARN, TEAL

    def _hex(color: str) -> str:
        return color.lstrip("#")

    NAVY_FILL   = PatternFill("solid", fgColor=_hex(CHICAGO))
    RED_FILL    = PatternFill("solid", fgColor=_hex(SURFACE_FAIL))
    ORANGE_FILL = PatternFill("solid", fgColor=_hex(SURFACE_WARN))
    GREEN_FILL  = PatternFill("solid", fgColor=_hex("#e4f5f0"))
    WHITE_FONT  = Font(name="Calibri", bold=True, color="FFFFFF")
    BOLD_FONT   = Font(name="Calibri", bold=True)

    SHEET1_COLS = [
        ("SKU",               "sku"),
        ("Product Name",      "product_name"),
        ("Product Line",      "product_line"),
        ("Forecast/wk (units)", "weekly_forecast_mean"),
        ("Current Inv (units)", "current_inventory"),
        ("Stockout Week",     "stockout_date"),
        ("Decision Deadline", "decision_deadline"),
        ("Days Until Deadline", "days_until_deadline"),
        ("Action Flag",       "deadline_flag"),
        ("Shared Line Conflict", "shared_line_conflict"),
    ]

    wb = openpyxl.Workbook()
    ws1 = wb.active
    ws1.title = "Production Decision Brief"

    # Header row
    for col_idx, (header, _) in enumerate(SHEET1_COLS, start=1):
        cell = ws1.cell(row=1, column=col_idx, value=header)
        cell.fill = NAVY_FILL
        cell.font = WHITE_FONT
        ws1.column_dimensions[get_column_letter(col_idx)].width = max(len(header) + 4, 16)

    # Data rows
    for row_idx, (_, row) in enumerate(sop_df.iterrows(), start=2):
        flag = str(row.get("deadline_flag", "OK"))
        if flag in ("PAST_DUE", "CRITICAL"):
            row_fill = RED_FILL
        elif flag == "WARNING":
            row_fill = ORANGE_FILL
        else:
            row_fill = GREEN_FILL

        for col_idx, (_, field) in enumerate(SHEET1_COLS, start=1):
            val = row.get(field)
            if isinstance(val, (pd.Timestamp,)):
                val = str(val.date()) if pd.notna(val) else None
            elif val is None or (isinstance(val, float) and pd.isna(val)):
                val = None
            elif isinstance(val, bool):
                val = "Yes" if val else ""
            cell = ws1.cell(row=row_idx, column=col_idx, value=val)
            cell.fill = row_fill

    # Footer note
    note_row = len(sop_df) + 3
    ws1.cell(row=note_row, column=1,
             value="Generated by Lailara LLC Production Demand Forecast. "
                   "Data: Cinderhaven Provisions LLC (synthetic). "
                   f"Date: {datetime.now().strftime('%Y-%m-%d %H:%M')}")

    # Sheet 2: Scenario Parameters
    ws2 = wb.create_sheet("Scenario Parameters")
    params = scenario_params or {}
    ws2.cell(row=1, column=1, value="Parameter").font = BOLD_FONT
    ws2.cell(row=1, column=2, value="Value").font = BOLD_FONT
    rows = [
        ("Promo Lift %", f"{params.get('promo_lift_pct', 0.0)*100:.0f}%"),
        ("New Retailer Doors", str(params.get("new_doors", 0))),
        ("Lead-Time Slip (weeks)", str(params.get("lead_time_slip_weeks", 0))),
        ("Generated At", datetime.now().strftime("%Y-%m-%d %H:%M")),
    ]
    for i, (k, v) in enumerate(rows, start=2):
        ws2.cell(row=i, column=1, value=k)
        ws2.cell(row=i, column=2, value=v)

    buf = io.BytesIO()
    wb.save(buf)
    buf.seek(0)
    return buf.getvalue()


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _get_forecast_from_week(true_demand_df: pd.DataFrame) -> str:
    """Return the last week_ending in the dataset, or the demo reference date."""
    if true_demand_df.empty:
        return _DEMO_AS_OF_DATE
    try:
        last_week = pd.to_datetime(true_demand_df["week_ending"]).max()
        return str(last_week.date())
    except Exception:
        return _DEMO_AS_OF_DATE
