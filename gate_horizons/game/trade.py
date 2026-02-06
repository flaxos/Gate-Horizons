"""Trade route system for Gate Horizons."""

import uuid
from typing import Optional


class TradeRoute:
    def __init__(
        self,
        id: str = None,
        source_system: str = "",
        destination_system: str = "",
        assigned_ships: list = None,
        resource_manifest: dict = None,
        active: bool = True,
        efficiency: float = 1.0,
    ):
        self.id = id or str(uuid.uuid4())[:8]
        self.source_system = source_system
        self.destination_system = destination_system
        self.assigned_ships = assigned_ships or []
        self.resource_manifest = resource_manifest or {
            "outbound": {},
            "inbound": {},
        }
        self.active = active
        self.efficiency = efficiency

    def calculate_throughput(self, fleet=None) -> dict:
        """Per-turn resource transfer based on freighter count and capacity."""
        if not self.active or not fleet:
            return {"outbound": {}, "inbound": {}}

        total_capacity = 0
        for ship_id in self.assigned_ships:
            ship = fleet.ships.get(ship_id)
            if ship:
                total_capacity += ship.stats.cargo_capacity

        throughput = {"outbound": {}, "inbound": {}}

        for direction in ("outbound", "inbound"):
            manifest = self.resource_manifest.get(direction, {})
            total_requested = sum(manifest.values())
            if total_requested == 0:
                continue

            # Scale by capacity and efficiency
            scale = min(1.0, total_capacity / max(1, total_requested)) * self.efficiency
            for resource, amount in manifest.items():
                throughput[direction][resource] = int(amount * scale)

        return throughput

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "source_system": self.source_system,
            "destination_system": self.destination_system,
            "assigned_ships": list(self.assigned_ships),
            "resource_manifest": {
                k: dict(v) for k, v in self.resource_manifest.items()
            },
            "active": self.active,
            "efficiency": self.efficiency,
        }

    @classmethod
    def from_dict(cls, data: dict) -> "TradeRoute":
        return cls(**data)


class TradeManager:
    def __init__(self):
        self.routes: dict[str, TradeRoute] = {}

    def create_route(
        self,
        source: str,
        dest: str,
        ships: list,
        manifest: dict,
        galaxy=None,
    ) -> Optional[TradeRoute]:
        """Create a new trade route between two systems."""
        # Validate path exists
        if galaxy:
            path = galaxy.get_path(source, dest)
            if not path:
                return None
            distance = len(path) - 1
        else:
            distance = 1

        route = TradeRoute(
            source_system=source,
            destination_system=dest,
            assigned_ships=list(ships),
            resource_manifest=manifest,
        )

        # Efficiency decreases with distance
        route.efficiency = max(0.3, 1.0 - (distance - 1) * 0.1)

        self.routes[route.id] = route
        return route

    def cancel_route(self, route_id: str) -> bool:
        if route_id in self.routes:
            del self.routes[route_id]
            return True
        return False

    def process_turn(self, resources=None, fleet=None) -> list:
        """Process all active trade routes for one turn."""
        reports = []

        for route in self.routes.values():
            if not route.active:
                continue

            throughput = route.calculate_throughput(fleet)
            report = {
                "route_id": route.id,
                "source": route.source_system,
                "destination": route.destination_system,
                "transferred": {},
                "disrupted": False,
            }

            if resources:
                # Outbound: move resources from source to destination
                for resource, amount in throughput.get("outbound", {}).items():
                    if amount > 0 and resources.global_resources.get(resource, 0) >= amount:
                        resources.spend(resource, amount, route.source_system)
                        resources.add(resource, amount, route.destination_system)
                        report["transferred"][f"outbound_{resource}"] = amount

                # Inbound: move resources from destination to source
                for resource, amount in throughput.get("inbound", {}).items():
                    if amount > 0 and resources.global_resources.get(resource, 0) >= amount:
                        resources.spend(resource, amount, route.destination_system)
                        resources.add(resource, amount, route.source_system)
                        report["transferred"][f"inbound_{resource}"] = amount

            reports.append(report)

        return reports

    def get_route_summary(self) -> list:
        return [
            {
                "id": r.id,
                "source": r.source_system,
                "destination": r.destination_system,
                "active": r.active,
                "efficiency": r.efficiency,
                "ships": len(r.assigned_ships),
            }
            for r in self.routes.values()
        ]

    def to_dict(self) -> dict:
        return {
            "routes": {rid: r.to_dict() for rid, r in self.routes.items()}
        }

    @classmethod
    def from_dict(cls, data: dict) -> "TradeManager":
        tm = cls()
        for rid, rdata in data.get("routes", {}).items():
            tm.routes[rid] = TradeRoute.from_dict(rdata)
        return tm
