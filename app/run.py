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
