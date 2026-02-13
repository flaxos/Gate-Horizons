"""Runtime feature flag accessors."""

from __future__ import annotations

from gate_horizons.game.settings import GameSettings


_runtime_settings = GameSettings()


def initialize_runtime_flags(settings: GameSettings) -> None:
    """Initialize runtime flags from app-loaded settings."""
    global _runtime_settings
    _runtime_settings = settings


def fleet_groups_enabled(settings: GameSettings | None = None) -> bool:
    """Return whether fleet-group behavior should be enabled."""
    active_settings = settings or _runtime_settings
    return bool(getattr(active_settings, "enable_fleet_groups", False))
