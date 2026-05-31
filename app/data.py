"""SQL query layer — stub.

Replaced with full implementation in U6.
Each public function returns a DataFrame. Results are cached with
@cache.memoize so repeated tab switches don't re-query Postgres.

Cache is initialized in run.py via init_cache(server).
"""

from __future__ import annotations

import logging
import os

import pandas as pd
from flask_caching import Cache

cache = Cache()
logger = logging.getLogger(__name__)


def init_cache(server) -> None:
    cache_dir = os.environ.get("CACHE_DIR", "/cache")
    try:
        cache.init_app(server, config={
            "CACHE_TYPE": "FileSystemCache",
            "CACHE_DIR": cache_dir,
            "CACHE_DEFAULT_TIMEOUT": 3600,
        })
    except Exception:
        cache.init_app(server, config={
            "CACHE_TYPE": "SimpleCache",
            "CACHE_DEFAULT_TIMEOUT": 3600,
        })


@cache.memoize(timeout=3600)
def get_product_master() -> pd.DataFrame:
    """All SKUs from product_master. Stub — replaced in U6."""
    from app.db import get_conn
    try:
        with get_conn() as conn:
            return pd.read_sql(
                "SELECT sku, product_name, product_line FROM product_master ORDER BY sku",
                conn,
            )
    except Exception:
        logger.exception("get_product_master failed")
        return pd.DataFrame()
