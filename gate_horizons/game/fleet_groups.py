"""Fleet-group foundation helpers with safe feature-gated behavior."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Sequence

from gate_horizons.game.feature_flags import fleet_groups_enabled
from gate_horizons.game.telemetry import TelemetryAdapter
from gate_horizons.game.telemetry_events import RoadmapTelemetryEvent


@dataclass(frozen=True)
class FleetGroupCommandResult:
    accepted: bool
    reason: str | None = None


def can_create_or_dispatch(settings=None) -> bool:
    return fleet_groups_enabled(settings)


def create_group(
    *,
    game_state: Any,
    group_id: str,
    ship_ids: Sequence[str],
    system_id: str,
    turn_index: int,
    telemetry: TelemetryAdapter,
    settings=None,
) -> FleetGroupCommandResult:
    del game_state
    if not can_create_or_dispatch(settings):
        return FleetGroupCommandResult(accepted=False, reason="feature_disabled")

    telemetry.emit(
        RoadmapTelemetryEvent.FLEET_GROUP_CREATED,
        {
            "group_id": group_id,
            "ship_count": len(ship_ids),
            "system_id": system_id,
            "turn_index": turn_index,
        },
    )
    return FleetGroupCommandResult(accepted=True)


def dispatch_group_order(
    *,
    group_id: str,
    order_type: str,
    target_id: str,
    ship_count: int,
    turn_index: int,
    telemetry: TelemetryAdapter,
    settings=None,
) -> FleetGroupCommandResult:
    if not can_create_or_dispatch(settings):
        return FleetGroupCommandResult(accepted=False, reason="feature_disabled")

    telemetry.emit(
        RoadmapTelemetryEvent.FLEET_GROUP_ORDER_ISSUED,
        {
            "group_id": group_id,
            "order_type": order_type,
            "target_id": target_id,
            "ship_count": ship_count,
            "turn_index": turn_index,
        },
    )
    return FleetGroupCommandResult(accepted=True)
