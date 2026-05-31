"""Top-level callback dispatcher — stub.

Tab callbacks registered here as U7, U8, U9 are implemented.
"""

from __future__ import annotations

from app.tabs import sop_view


def register_callbacks(app) -> None:
    sop_view.register_callbacks(app)
    # U8: scenario_controls.register_callbacks(app) — added in U8
    # U9: doom_loop.register_callbacks(app) — added in U9
