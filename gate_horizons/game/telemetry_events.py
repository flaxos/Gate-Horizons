"""Stable telemetry event names and required payload fields."""

from __future__ import annotations

from enum import Enum


class RoadmapTelemetryEvent(str, Enum):
    FLEET_GROUP_CREATED = "fleet_group_created"
    FLEET_GROUP_ORDER_ISSUED = "fleet_group_order_issued"
    FLEET_GROUP_ORDER_RESULT = "fleet_group_order_result"


REQUIRED_FIELDS: dict[RoadmapTelemetryEvent, tuple[str, ...]] = {
    RoadmapTelemetryEvent.FLEET_GROUP_CREATED: (
        "group_id",
        "ship_count",
        "system_id",
        "turn_index",
    ),
    RoadmapTelemetryEvent.FLEET_GROUP_ORDER_ISSUED: (
        "group_id",
        "order_type",
        "target_id",
        "ship_count",
        "turn_index",
    ),
    RoadmapTelemetryEvent.FLEET_GROUP_ORDER_RESULT: (
        "group_id",
        "order_type",
        "result",
        "reason",
        "turn_index",
    ),
}
