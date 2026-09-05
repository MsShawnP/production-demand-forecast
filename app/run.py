"""Dash app entry point.

Init order: load_dotenv → Dash → cache → layout → callbacks → health route.
Matches competitive-shelf-intelligence/app/run.py pattern exactly.
"""

from __future__ import annotations

import logging
import os
import pathlib
import secrets as _secrets
import threading

logger = logging.getLogger(__name__)

from dotenv import load_dotenv

load_dotenv(pathlib.Path(__file__).resolve().parent.parent / ".env")

import dash_bootstrap_components as dbc
from dash import Dash
from flask import jsonify

from app.callbacks import register_callbacks
from app.data import cache, init_cache
from app.layout import create_layout
from lailara_frame import wrap

app = Dash(
    __name__,
    external_stylesheets=[dbc.themes.BOOTSTRAP],
    suppress_callback_exceptions=True,
    title="Co-Packer Production Planner — Cinderhaven",
    meta_tags=[
        {"property": "og:title", "content": "Co-Packer Production Planner"},
        {
            "property": "og:description",
            "content": (
                "Demand signals, capacity constraints, and seasonality in one "
                "S&OP model: what the next launch does to existing commitments."
            ),
        },
        {"property": "og:type", "content": "website"},
        {"property": "og:url", "content": "https://forecast.lailarallc.com/"},
        {"property": "og:image", "content": "https://lailarallc.com/og/s/forecast.png"},
        {
            "property": "og:image:secure_url",
            "content": "https://lailarallc.com/og/s/forecast.png",
        },
        {"property": "og:image:type", "content": "image/png"},
        {"property": "og:image:width", "content": "1200"},
        {"property": "og:image:height", "content": "630"},
        {"property": "og:image:alt", "content": "Co-Packer Production Planner"},
        {"name": "twitter:card", "content": "summary_large_image"},
        {"name": "twitter:image", "content": "https://lailarallc.com/og/s/forecast.png"},
        {
            "name": "description",
            "content": (
                "Demand signals, capacity constraints, and seasonality in one "
                "S&OP model: what the next launch does to existing commitments."
            ),
        },
    ],
)
server = app.server
_secret_key = os.environ.get("FLASK_SECRET_KEY")
if not _secret_key:
    logger.warning(
        "FLASK_SECRET_KEY not set — using a per-process random key. "
        "Sessions will not survive worker restarts and will differ across "
        "Gunicorn workers. Set FLASK_SECRET_KEY in .env or fly secrets."
    )
    _secret_key = _secrets.token_hex(32)
server.secret_key = _secret_key
init_cache(server)

app.layout = wrap(
    create_layout(),
    tool_name="CO-PACKER PRODUCTION PLANNER",
    footer_note="Data: Cinderhaven Provisions synthetic dataset.",
)
register_callbacks(app)


def _prewarm_cache():
    """Pre-warm all cached queries so the first visitor gets a sub-second response.

    In snapshot mode (default): reads ~50 rows from forecast_snapshot — sub-second.
    In live mode (LIVE_COMPUTE=1): runs the full pipeline (~750K rows, STL ×50 SKUs).
    """
    with server.app_context():
        try:
            from app.data import _LIVE_COMPUTE, get_product_master, get_sop_summary
            mode = "live computation" if _LIVE_COMPUTE else "snapshot tables"
            logger.info("Pre-warming cache (%s)...", mode)
            get_sop_summary()
            get_product_master()
            logger.info("Cache pre-warm complete (%s)", mode)
        except Exception:
            logger.exception("Cache pre-warm failed — first request will be slow")


threading.Thread(target=_prewarm_cache, daemon=True).start()


@server.after_request
def _add_security_headers(response):
    response.headers["X-Frame-Options"] = "SAMEORIGIN"
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
    # Dash loads Bootstrap CSS and Plotly JS inline; unsafe-inline is required.
    # Tighten script-src if Dash ever supports nonces.
    response.headers["Content-Security-Policy"] = (
        "default-src 'self'; "
        "script-src 'self' 'unsafe-inline'; "
        "style-src 'self' 'unsafe-inline'; "
        "img-src 'self' data:; "
        "font-src 'self';"
    )
    return response


@server.route("/health")
def health():
    try:
        from app.db import get_conn
        with get_conn() as conn:
            cur = conn.cursor()
            cur.execute("SELECT 1")
        return jsonify({"status": "ok"})
    except Exception:
        return jsonify({"status": "error"}), 503


if __name__ == "__main__":
    debug = os.environ.get("FLASK_DEBUG", "").lower() in ("1", "true", "yes")
    app.run(debug=debug, port=8050)
