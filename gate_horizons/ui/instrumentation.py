"""Lightweight UI instrumentation for Gate Horizons.

Provides auditable logging of UI actions and state changes so that
UI -> logic flows can be traced. Uses Python's standard logging module
so that output is configurable (file, console, etc.) without code changes.

Usage:
    from gate_horizons.ui.instrumentation import ui_action, state_change

    ui_action("build_infrastructure", colony_id="sol", infra_type="housing")
    state_change("colony_build_started", colony_id="sol", infra_type="housing", level=2)
"""

import logging

logger = logging.getLogger("gate_horizons.ui")


def ui_action(event_name: str, **payload) -> None:
    """Log a user-initiated UI action (button tap, selection, navigation)."""
    parts = [f"{k}={v}" for k, v in payload.items()]
    detail = ", ".join(parts) if parts else ""
    logger.info("UI_ACTION  %s  %s", event_name, detail)


def state_change(change_name: str, **payload) -> None:
    """Log a game state mutation triggered by a UI action."""
    parts = [f"{k}={v}" for k, v in payload.items()]
    detail = ", ".join(parts) if parts else ""
    logger.info("STATE_CHG  %s  %s", change_name, detail)


def screen_transition(from_screen: str, to_screen: str) -> None:
    """Log a screen navigation event."""
    logger.info("SCREEN     %s -> %s", from_screen, to_screen)
