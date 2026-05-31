"""Dash app entry point.

Init order: load_dotenv → Dash → cache → layout → callbacks → health route.
Matches competitive-shelf-intelligence/app/run.py pattern exactly.
"""

from __future__ import annotations

import os
import pathlib
import secrets as _secrets

from dotenv import load_dotenv

load_dotenv(pathlib.Path(__file__).resolve().parent.parent / ".env")

import dash_bootstrap_components as dbc
from dash import Dash
from flask import jsonify

from app.callbacks import register_callbacks
from app.data import cache, init_cache
from app.layout import create_layout

app = Dash(
    __name__,
    external_stylesheets=[dbc.themes.BOOTSTRAP],
    suppress_callback_exceptions=True,
)
server = app.server
server.secret_key = os.environ.get("FLASK_SECRET_KEY") or _secrets.token_hex(32)
init_cache(server)

app.layout = create_layout()
register_callbacks(app)


@server.after_request
def _add_security_headers(response):
    response.headers["X-Frame-Options"] = "SAMEORIGIN"
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
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
