"""Orbital facility and ship construction system for Gate Horizons.

Orbital facilities are built at colonies and enable ship construction:
  - Spaceport: basic docking + storage. No ship building.
  - Drydock: builds scouts, small/medium freighters, miners, corvettes.
  - Orbital Yard: builds all ships including colony ships and large freighters.

Ship construction consumes components, credits, time, and dock capacity.
Only one (drydock) or two (orbital yard) ships can be built concurrently.
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
        components_consumed: dict = None,
        credits_consumed: int = 0,
    ):
        self.id = id or str(uuid.uuid4())[:8]
        self.blueprint_id = blueprint_id
        self.ship_name = ship_name
        self.facility_id = facility_id
        self.turns_remaining = turns_remaining
        self.components_consumed = components_consumed or {}
        self.credits_consumed = credits_consumed

    def process_tick(self) -> bool:
        """Advance construction. Returns True if complete."""
        self.turns_remaining -= 1
        return self.turns_remaining <= 0

    @property
    def progress_pct(self) -> float:
        """Estimated progress (requires knowing original build time)."""
        return 0.0  # Caller computes from blueprint

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "blueprint_id": self.blueprint_id,
            "ship_name": self.ship_name,
            "facility_id": self.facility_id,
            "turns_remaining": self.turns_remaining,
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
            components_consumed=dict(data.get("components_consumed", {})),
            credits_consumed=data.get("credits_consumed", 0),
        )


class ShipyardManager:
    """Manages orbital facilities and ship build queues across all colonies."""

    def __init__(self):
        # Per-system orbital facilities
        self.facilities: dict[str, list[OrbitalFacility]] = {}
        # Active build orders
        self.build_orders: list[ShipBuildOrder] = []

    def get_facilities(self, system_id: str) -> list:
        return list(self.facilities.get(system_id, []))

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
                if resources and resources.global_resources.get("credits", 0) < amount:
                    return None
            else:
                if inventory.get(res, 0) < amount:
                    return None

        # Consume resources
        for res, amount in build_cost.items():
            if res == "credits":
                if resources:
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

        required_facility = blueprint.get("required_facility", "drydock")

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
            return False, f"No facility at {system_id} can build {blueprint_id} (need {required_facility})"

        # Check concurrent build limit
        active_builds = sum(
            1 for o in self.build_orders
            if o.facility_id == suitable_facility.id
        )
        max_concurrent = suitable_facility.get_max_concurrent_builds(config)
        if active_builds >= max_concurrent:
            return False, f"Facility at capacity ({active_builds}/{max_concurrent} builds)"

        return True, "OK"

    def start_ship_build(
        self,
        system_id: str,
        blueprint_id: str,
        ship_name: str,
        config: dict,
        inventory: dict,
        resources=None,
    ) -> Optional[ShipBuildOrder]:
        """Start building a ship from a blueprint.

        Consumes components from inventory and credits from resources.
        """
        can_build, reason = self.can_build_ship(system_id, blueprint_id, config)
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
            if resources.global_resources.get("credits", 0) < credit_cost:
                return None

        # Consume components
        for comp, amount in components.items():
            inventory[comp] = max(0, inventory.get(comp, 0) - amount)

        # Consume credits
        if credit_cost > 0 and resources:
            resources.spend("credits", credit_cost)

        order = ShipBuildOrder(
            blueprint_id=blueprint_id,
            ship_name=ship_name,
            facility_id=suitable_facility.id,
            turns_remaining=blueprint.get("build_turns", 4),
            components_consumed=dict(components),
            credits_consumed=credit_cost,
        )
        self.build_orders.append(order)
        return order

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

        # Process ship build orders
        completed_orders = []
        for order in self.build_orders:
            if order.process_tick():
                completed_orders.append(order)
                ship_data = None
                if config:
                    ship_data = config.get("ship_blueprints", {}).get(order.blueprint_id)

                # Find which system this facility is at
                build_system_id = None
                for system_id, facilities in self.facilities.items():
                    for facility in facilities:
                        if facility.id == order.facility_id:
                            build_system_id = system_id
                            break
                    if build_system_id:
                        break

                report["ships_completed"].append({
                    "order_id": order.id,
                    "blueprint_id": order.blueprint_id,
                    "ship_name": order.ship_name,
                    "system_id": build_system_id or "",
                    "ship_data": ship_data,
                })

        for order in completed_orders:
            self.build_orders.remove(order)

        return report

    def get_build_queue_summary(self) -> list:
        return [
            {
                "id": o.id,
                "blueprint": o.blueprint_id,
                "name": o.ship_name,
                "turns_left": o.turns_remaining,
                "facility_id": o.facility_id,
            }
            for o in self.build_orders
        ]

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

    def to_dict(self) -> dict:
        return {
            "facilities": {
                sid: [f.to_dict() for f in facs]
                for sid, facs in self.facilities.items()
            },
            "build_orders": [o.to_dict() for o in self.build_orders],
        }

    @classmethod
    def from_dict(cls, data: dict) -> "ShipyardManager":
        sm = cls()
        for sid, facs_data in data.get("facilities", {}).items():
            sm.facilities[sid] = [OrbitalFacility.from_dict(f) for f in facs_data]
        sm.build_orders = [
            ShipBuildOrder.from_dict(o) for o in data.get("build_orders", [])
        ]
        return sm
