"""Typed telemetry adapter with required-field validation."""

from __future__ import annotations

from typing import Any, Callable, Mapping

from gate_horizons.game.telemetry_events import REQUIRED_FIELDS, RoadmapTelemetryEvent


class TelemetryAdapter:
    """Validate and emit roadmap telemetry events."""

    def __init__(
        self,
        emit: Callable[[str, Mapping[str, Any]], None] | None = None,
    ):
        self._emit = emit or (lambda _event_name, _payload: None)

    def emit(self, event: RoadmapTelemetryEvent, payload: Mapping[str, Any]) -> None:
        missing = [field for field in REQUIRED_FIELDS[event] if field not in payload]
        if missing:
            raise ValueError(
                f"Telemetry event '{event.value}' missing required fields: {', '.join(missing)}"
            )
        self._emit(event.value, payload)
