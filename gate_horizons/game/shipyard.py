"""Orbital facility and ship construction system for Gate Horizons.

Orbital facilities are built at colonies and enable ship construction:
  - Spaceport: basic docking + storage. No ship building.
  - Drydock: builds scouts, small/medium freighters, miners, corvettes.
  - Orbital Yard: builds all ships including colony ships and large freighters.

Ship construction consumes components, credits, time, and dock capacity.
Queues are per facility with limited parallelism per orbital yard.
"""

from __future__ import annotations

import uuid
from typing import Optional


class OrbitalFacility:
    """An orbital facility at a colony."""

    def __init__(
        self,
        id: str = None,
        facility_type: str = "spaceport",  # spaceport, drydock, orbital_yard
        level: int = 1,
        building: bool = False,
        build_turns_remaining: int = 0,
        storage_bonus: int = 0,
    ):
        self.id = id or str(uuid.uuid4())[:8]
        self.facility_type = facility_type
        self.level = level
        self.building = building
        self.build_turns_remaining = build_turns_remaining
        self.storage_bonus = storage_bonus

    def can_build_ships(self, config: dict) -> bool:
        """Check if this facility type can build ships."""
        if self.building:
            return False
        facility_info = config.get("orbital_facility_types", {}).get(self.facility_type, {})
        return facility_info.get("can_build_ships", False)

    def get_buildable_classes(self, config: dict) -> list:
        """Get ship classes this facility can build."""
        facility_info = config.get("orbital_facility_types", {}).get(self.facility_type, {})
        return list(facility_info.get("buildable_classes", []))

    def get_max_concurrent_builds(self, config: dict) -> int:
        facility_info = config.get("orbital_facility_types", {}).get(self.facility_type, {})
        return facility_info.get("max_concurrent_builds", 0) * self.level

    def process_tick(self) -> bool:
        """Process one tick. Returns True if construction completed this tick."""
        if not self.building:
            return False
        self.build_turns_remaining -= 1
        if self.build_turns_remaining <= 0:
            self.building = False
            self.build_turns_remaining = 0
            return True
        return False

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "facility_type": self.facility_type,
            "level": self.level,
            "building": self.building,
            "build_turns_remaining": self.build_turns_remaining,
            "storage_bonus": self.storage_bonus,
        }

    @classmethod
    def from_dict(cls, data: dict) -> "OrbitalFacility":
        return cls(
            id=data.get("id"),
            facility_type=data.get("facility_type", "spaceport"),
            level=data.get("level", 1),
            building=data.get("building", False),
            build_turns_remaining=data.get("build_turns_remaining", 0),
            storage_bonus=data.get("storage_bonus", 0),
        )


class ShipBuildOrder:
    """A ship under construction in an orbital facility."""

    def __init__(
        self,
        id: str = None,
        blueprint_id: str = "",
        ship_name: str = "New Ship",
        facility_id: str = "",
        turns_remaining: int = 1,
        total_turns: int = None,
        components_consumed: dict = None,
        credits_consumed: int = 0,
    ):
        self.id = id or str(uuid.uuid4())[:8]
        self.blueprint_id = blueprint_id
        self.ship_name = ship_name
        self.facility_id = facility_id
        self.turns_remaining = turns_remaining
        self.total_turns = total_turns if total_turns is not None else turns_remaining
        self.components_consumed = components_consumed or {}
        self.credits_consumed = credits_consumed

    def process_tick(self) -> bool:
        """Advance construction. Returns True if complete."""
        self.turns_remaining -= 1
        return self.turns_remaining <= 0

    @property
    def progress_pct(self) -> float:
        """Estimated progress percentage."""
        if self.total_turns <= 0:
            return 100.0
        done = max(0, self.total_turns - max(0, self.turns_remaining))
        return min(100.0, (done / self.total_turns) * 100.0)

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "blueprint_id": self.blueprint_id,
            "ship_name": self.ship_name,
            "facility_id": self.facility_id,
            "turns_remaining": self.turns_remaining,
            "total_turns": self.total_turns,
            "components_consumed": dict(self.components_consumed),
            "credits_consumed": self.credits_consumed,
        }

    @classmethod
    def from_dict(cls, data: dict) -> "ShipBuildOrder":
        return cls(
            id=data.get("id"),
            blueprint_id=data.get("blueprint_id", ""),
            ship_name=data.get("ship_name", "New Ship"),
            facility_id=data.get("facility_id", ""),
            turns_remaining=data.get("turns_remaining", 1),
            total_turns=data.get("total_turns"),
            components_consumed=dict(data.get("components_consumed", {})),
            credits_consumed=data.get("credits_consumed", 0),
        )


class ConstructionQueue:
    """Queue of ship construction orders for a facility."""

    def __init__(self, facility_id: str, pending: list = None, active: list = None):
        self.facility_id = facility_id
        self.pending: list[ShipBuildOrder] = pending or []
        self.active: list[ShipBuildOrder] = active or []

    def enqueue(self, order: ShipBuildOrder) -> None:
        self.pending.append(order)

    def start_next(self, max_parallel: int) -> list[ShipBuildOrder]:
        started = []
        while self.pending and len(self.active) < max_parallel:
            order = self.pending.pop(0)
            self.active.append(order)
            started.append(order)
        return started

    def cancel(self, order_id: str) -> Optional[ShipBuildOrder]:
        for pool in (self.pending, self.active):
            for order in list(pool):
                if order.id == order_id:
                    pool.remove(order)
                    return order
        return None

    def rush(self, order_id: str, turns: int = 1) -> Optional[ShipBuildOrder]:
        for order in self.active:
            if order.id == order_id:
                order.turns_remaining = max(0, order.turns_remaining - turns)
                return order
        return None

    def to_dict(self) -> dict:
        return {
            "facility_id": self.facility_id,
            "pending": [o.to_dict() for o in self.pending],
            "active": [o.to_dict() for o in self.active],
        }

    @classmethod
    def from_dict(cls, data: dict) -> "ConstructionQueue":
        return cls(
            facility_id=data.get("facility_id", ""),
            pending=[ShipBuildOrder.from_dict(o) for o in data.get("pending", [])],
            active=[ShipBuildOrder.from_dict(o) for o in data.get("active", [])],
        )


class Shipyard:
    """Convenience wrapper for a facility + its construction queue."""

    def __init__(self, facility: OrbitalFacility, queue: ConstructionQueue):
        self.facility = facility
        self.queue = queue


class ShipyardManager:
    """Manages orbital facilities and ship build queues across all colonies."""

    def __init__(self):
        # Per-system orbital facilities
        self.facilities: dict[str, list[OrbitalFacility]] = {}
        self.construction_queues: dict[str, ConstructionQueue] = {}

    @property
    def build_orders(self) -> list[ShipBuildOrder]:
        return [
            order for queue in self.construction_queues.values() for order in queue.active
        ]

    def get_facilities(self, system_id: str) -> list:
        return list(self.facilities.get(system_id, []))

    def get_shipyards(self, system_id: str) -> list[Shipyard]:
        shipyards = []
        for facility in self.facilities.get(system_id, []):
            queue = self._get_queue(facility.id)
            shipyards.append(Shipyard(facility, queue))
        return shipyards

    def get_best_facility(self, system_id: str) -> Optional[OrbitalFacility]:
        """Get the highest-tier facility at a system."""
        facilities = self.facilities.get(system_id, [])
        if not facilities:
            return None
        priority = {"orbital_yard": 3, "drydock": 2, "spaceport": 1}
        return max(facilities, key=lambda f: priority.get(f.facility_type, 0))

    def build_facility(
        self,
        system_id: str,
        facility_type: str,
        config: dict,
        inventory: dict,
        colony=None,
        resources=None,
    ) -> Optional[OrbitalFacility]:
        """Start building an orbital facility.

        Checks prerequisites, consumes resources, creates building facility.
        """
        facility_config = config.get("orbital_facility_types", {}).get(facility_type)
        if not facility_config:
            return None

        # Check prerequisite
        prereq = facility_config.get("prerequisite")
        if prereq:
            existing_types = {
                f.facility_type for f in self.facilities.get(system_id, [])
                if not f.building
            }
            if prereq not in existing_types:
                return None

        # Check cost
        build_cost = facility_config.get("build_cost", {})
        for res, amount in build_cost.items():
            if res == "credits":
                if colony and colony.stockpiles.get("credits", 0) < amount:
                    return None
                if resources and resources.global_resources.get("credits", 0) < amount:
                    return None
            else:
                if inventory.get(res, 0) < amount:
                    return None

        # Consume resources
        for res, amount in build_cost.items():
            if res == "credits":
                if resources:
                    if colony:
                        resources.spend_from_colony("credits", amount, colony)
                    else:
                        resources.spend("credits", amount)
            else:
                inventory[res] = max(0, inventory.get(res, 0) - amount)

        facility = OrbitalFacility(
            facility_type=facility_type,
            level=1,
            building=True,
            build_turns_remaining=facility_config.get("build_turns", 5),
            storage_bonus=facility_config.get("storage_bonus", 0),
        )

        if system_id not in self.facilities:
            self.facilities[system_id] = []
        self.facilities[system_id].append(facility)
        self.construction_queues[facility.id] = ConstructionQueue(facility.id)
        return facility

    def can_build_ship(
        self,
        system_id: str,
        blueprint_id: str,
        config: dict,
    ) -> tuple:
        """Check if a ship blueprint can be built at a system.

        Returns (can_build: bool, reason: str).
        """
        blueprint = config.get("ship_blueprints", {}).get(blueprint_id)
        if not blueprint:
            return False, f"Unknown blueprint: {blueprint_id}"

        # Find a facility that can build this ship
        suitable_facility = None
        for facility in self.facilities.get(system_id, []):
            if facility.building:
                continue
            buildable = facility.get_buildable_classes(config)
            if blueprint_id in buildable:
                suitable_facility = facility
                break

        if not suitable_facility:
            return False, f"No facility at {system_id} can build {blueprint_id}"

        return True, "OK"

    def start_build(
        self,
        system_id: str,
        blueprint_id: str,
        ship_name: str,
        config: dict,
        inventory: dict,
        colony=None,
        resources=None,
        build_time_reduction: int = 0,
    ) -> Optional[ShipBuildOrder]:
        return self.start_ship_build(
            system_id,
            blueprint_id,
            ship_name,
            config,
            inventory,
            colony,
            resources,
            build_time_reduction,
        )

    def start_ship_build(
        self,
        system_id: str,
        blueprint_id: str,
        ship_name: str,
        config: dict,
        inventory: dict,
        colony=None,
        resources=None,
        build_time_reduction: int = 0,
    ) -> Optional[ShipBuildOrder]:
        """Start building a ship from a blueprint.

        Consumes components from inventory and credits from resources.
        """
        can_build, _ = self.can_build_ship(system_id, blueprint_id, config)
        if not can_build:
            return None

        blueprint = config.get("ship_blueprints", {}).get(blueprint_id)
        if not blueprint:
            return None

        # Find the suitable facility
        suitable_facility = None
        for facility in self.facilities.get(system_id, []):
            if facility.building:
                continue
            buildable = facility.get_buildable_classes(config)
            if blueprint_id in buildable:
                suitable_facility = facility
                break

        if not suitable_facility:
            return None

        # Check component costs
        components = blueprint.get("components", {})
        for comp, amount in components.items():
            if inventory.get(comp, 0) < amount:
                return None

        # Check credit cost
        credit_cost = blueprint.get("credits", 0)
        if credit_cost > 0 and resources:
            if colony and colony.stockpiles.get("credits", 0) < credit_cost:
                return None
            if resources.global_resources.get("credits", 0) < credit_cost:
                return None

        # Consume components
        for comp, amount in components.items():
            inventory[comp] = max(0, inventory.get(comp, 0) - amount)

        # Consume credits
        if credit_cost > 0 and resources:
            if colony:
                resources.spend_from_colony("credits", credit_cost, colony)
            else:
                resources.spend("credits", credit_cost)

        total_turns = max(1, blueprint.get("build_turns", 4) - build_time_reduction)
        order = ShipBuildOrder(
            blueprint_id=blueprint_id,
            ship_name=ship_name,
            facility_id=suitable_facility.id,
            turns_remaining=total_turns,
            total_turns=total_turns,
            components_consumed=dict(components),
            credits_consumed=credit_cost,
        )

        queue = self._get_queue(suitable_facility.id)
        queue.enqueue(order)
        self._advance_queue(suitable_facility, queue, config)
        return order

    def cancel_build(
        self,
        order_id: str,
        config: dict,
        inventory: dict,
        resources=None,
        refund_ratio: Optional[float] = None,
    ) -> bool:
        """Cancel a build order and refund a portion of costs."""
        queue = self._find_queue_with_order(order_id)
        if not queue:
            return False
        order = queue.cancel(order_id)
        if not order:
            return False

        balance = config.get("shipyard_balance", {})
        refund = refund_ratio if refund_ratio is not None else balance.get("cancel_refund_ratio", 0.5)
        refund = max(0.0, min(1.0, refund))

        if refund > 0:
            for comp, amount in order.components_consumed.items():
                inventory[comp] = inventory.get(comp, 0) + int(amount * refund)
            if resources and order.credits_consumed > 0:
                resources.add("credits", int(order.credits_consumed * refund))
        return True

    def rush_build(
        self,
        order_id: str,
        config: dict,
        resources=None,
        turns: int = 1,
    ) -> bool:
        """Spend credits to reduce remaining build time."""
        queue = self._find_queue_with_order(order_id)
        if not queue:
            return False

        balance = config.get("shipyard_balance", {})
        cost_per_turn = balance.get("rush_cost_per_turn", 0)
        total_cost = max(0, cost_per_turn * max(1, turns))
        if resources and total_cost > 0:
            if resources.global_resources.get("credits", 0) < total_cost:
                return False
            resources.spend("credits", total_cost)

        order = queue.rush(order_id, turns=turns)
        return order is not None

    def process_tick(self, fleet=None, config: dict = None) -> dict:
        """Process one tick for all facilities and build orders.

        Returns report of completions.
        """
        report = {
            "facilities_completed": [],
            "ships_completed": [],
        }

        # Process facility construction
        for system_id, facilities in self.facilities.items():
            for facility in facilities:
                if facility.process_tick():
                    report["facilities_completed"].append({
                        "system_id": system_id,
                        "facility_type": facility.facility_type,
                        "facility_id": facility.id,
                    })
                    queue = self._get_queue(facility.id)
                    if config:
                        self._advance_queue(facility, queue, config)

        # Process ship build orders
        for facility_id, queue in self.construction_queues.items():
            completed_orders = []
            for order in list(queue.active):
                if order.process_tick():
                    completed_orders.append(order)

            for order in completed_orders:
                queue.active.remove(order)
                ship_data = None
                if config:
                    ship_data = config.get("ship_blueprints", {}).get(order.blueprint_id)

                build_system_id = self._get_system_for_facility(order.facility_id)

                report["ships_completed"].append({
                    "order_id": order.id,
                    "blueprint_id": order.blueprint_id,
                    "ship_name": order.ship_name,
                    "system_id": build_system_id or "",
                    "ship_data": ship_data,
                })

            facility = self._get_facility_by_id(facility_id)
            if facility and config:
                self._advance_queue(facility, queue, config)

        return report

    def get_build_queue_summary(self) -> list:
        summary = []
        for facility_id, queue in self.construction_queues.items():
            for order in queue.active:
                summary.append({
                    "id": order.id,
                    "blueprint": order.blueprint_id,
                    "name": order.ship_name,
                    "turns_left": order.turns_remaining,
                    "facility_id": facility_id,
                    "status": "active",
                    "progress": order.progress_pct,
                })
            for order in queue.pending:
                summary.append({
                    "id": order.id,
                    "blueprint": order.blueprint_id,
                    "name": order.ship_name,
                    "turns_left": order.turns_remaining,
                    "facility_id": facility_id,
                    "status": "queued",
                    "progress": 0.0,
                })
        return summary

    def get_facilities_summary(self) -> dict:
        return {
            system_id: [
                {
                    "id": f.id,
                    "type": f.facility_type,
                    "level": f.level,
                    "building": f.building,
                    "turns_left": f.build_turns_remaining,
                }
                for f in facilities
            ]
            for system_id, facilities in self.facilities.items()
        }

    def _get_queue(self, facility_id: str) -> ConstructionQueue:
        if facility_id not in self.construction_queues:
            self.construction_queues[facility_id] = ConstructionQueue(facility_id)
        return self.construction_queues[facility_id]

    def _advance_queue(self, facility: OrbitalFacility, queue: ConstructionQueue, config: dict) -> None:
        if facility.building:
            return
        max_parallel = facility.get_max_concurrent_builds(config)
        if max_parallel <= 0:
            return
        queue.start_next(max_parallel)

    def _get_system_for_facility(self, facility_id: str) -> Optional[str]:
        for system_id, facilities in self.facilities.items():
            for facility in facilities:
                if facility.id == facility_id:
                    return system_id
        return None

    def _get_facility_by_id(self, facility_id: str) -> Optional[OrbitalFacility]:
        for facilities in self.facilities.values():
            for facility in facilities:
                if facility.id == facility_id:
                    return facility
        return None

    def _find_queue_with_order(self, order_id: str) -> Optional[ConstructionQueue]:
        for queue in self.construction_queues.values():
            if any(order.id == order_id for order in queue.active + queue.pending):
                return queue
        return None

    def to_dict(self) -> dict:
        return {
            "facilities": {
                sid: [f.to_dict() for f in facs]
                for sid, facs in self.facilities.items()
            },
            "construction_queues": {
                fid: queue.to_dict() for fid, queue in self.construction_queues.items()
            },
        }

    @classmethod
    def from_dict(cls, data: dict) -> "ShipyardManager":
        sm = cls()
        for sid, facs_data in data.get("facilities", {}).items():
            sm.facilities[sid] = [OrbitalFacility.from_dict(f) for f in facs_data]
        queues = data.get("construction_queues")
        if queues:
            sm.construction_queues = {
                fid: ConstructionQueue.from_dict(qdata) for fid, qdata in queues.items()
            }
        else:
            # Backward compatibility: migrate build_orders into queues
            for order_data in data.get("build_orders", []):
                order = ShipBuildOrder.from_dict(order_data)
                queue = sm._get_queue(order.facility_id)
                queue.active.append(order)
        return sm
