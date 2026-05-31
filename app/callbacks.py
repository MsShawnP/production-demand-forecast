"""Top-level callback dispatcher — stub.

Tab callbacks registered here as U7, U8, U9 are implemented.
"""

from __future__ import annotations

from app.tabs import doom_loop, scenario_controls, sop_view


def register_callbacks(app) -> None:
    sop_view.register_callbacks(app)
    scenario_controls.register_callbacks(app)
    doom_loop.register_callbacks(app)
