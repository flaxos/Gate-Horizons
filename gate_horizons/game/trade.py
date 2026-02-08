"""Logistics and trade route system for Gate Horizons.

This is NOT Factorio. Resources flow as abstracted per-turn quantities.
No belt/item micromanagement. Each trade route has:
- capacity_per_turn: max resources shipped per turn (constrained by logistics infra)
- latency_turns: transit delay before goods arrive
- risk_factor: chance of partial loss per shipment (0.0-1.0)
- in-transit queue: goods that have been shipped but not yet arrived

Turn resolution for logistics:
1) Apply arrivals from in-transit queue -> add to colony stockpiles
2) Compute trade flows -> create in-transit shipments with latency
"""

import uuid
from typing import Optional


class Shipment:
    """A batch of resources in transit between two worlds."""

    def __init__(
        self,
        route_id: str,
        from_world: str,
        to_world: str,
        resources: dict,
        turns_remaining: int,
    ):
        self.route_id = route_id
        self.from_world = from_world
        self.to_world = to_world
        self.resources = dict(resources)  # {resource: amount}
        self.turns_remaining = turns_remaining

    def tick(self) -> bool:
        """Advance one turn. Returns True if shipment has arrived."""
        self.turns_remaining -= 1
        return self.turns_remaining <= 0

    def to_dict(self) -> dict:
        return {
            "route_id": self.route_id,
            "from_world": self.from_world,
            "to_world": self.to_world,
            "resources": dict(self.resources),
            "turns_remaining": self.turns_remaining,
        }

    @classmethod
    def from_dict(cls, data: dict) -> "Shipment":
        return cls(
            route_id=data.get("route_id", ""),
            from_world=data.get("from_world", ""),
            to_world=data.get("to_world", ""),
            resources=dict(data.get("resources", {})),
            turns_remaining=data.get("turns_remaining", 0),
        )


class TradeRoute:
    """An abstracted logistics link between two worlds.

    Unlike the old ship-based system, this is purely abstract:
    capacity comes from colony logistics infrastructure plus assigned freighters.
    """

    def __init__(
        self,
        id: str = None,
        source_system: str = "",
        destination_system: str = "",
        capacity_per_turn: int = 10,
        latency_turns: int = 1,
        risk_factor: float = 0.0,
        enabled: bool = True,
        resource_manifest: dict = None,
        auto_policy: str = "manual",
        auto_allowlist: list = None,
        auto_max_per_resource: dict = None,
        # Legacy fields preserved for backward compatibility
        assigned_ships: list = None,
        active: bool = True,
        efficiency: float = 1.0,
    ):
        self.id = id or str(uuid.uuid4())[:8]
        self.source_system = source_system
        self.destination_system = destination_system
        self.capacity_per_turn = capacity_per_turn
        self.latency_turns = max(1, latency_turns)
        self.risk_factor = max(0.0, min(1.0, risk_factor))
        self.enabled = enabled
        self.resource_manifest = resource_manifest or {
            "outbound": {},  # {resource: amount_per_turn} from source to dest
            "inbound": {},   # {resource: amount_per_turn} from dest to source
        }
        self.auto_policy = auto_policy or "manual"
        self.auto_allowlist = list(auto_allowlist or [])
        self.auto_max_per_resource = dict(auto_max_per_resource or {})
        # Legacy compatibility
        self.assigned_ships = assigned_ships or []
        self.active = active
        self.efficiency = efficiency

    def get_effective_capacity(self, fleet=None, tech_effects: dict = None) -> int:
        base_capacity = self.capacity_per_turn
        freighter_capacity = 0
        if fleet:
            for ship_id in self.assigned_ships:
                ship = fleet.ships.get(ship_id)
                if not ship:
                    continue
                if getattr(ship.stats, "freight_capacity", 0) > 0:
                    freighter_capacity += ship.stats.freight_capacity
                elif "freighter" in ship.ship_class:
                    freighter_capacity += max(1, ship.stats.cargo_capacity // 10)

        bonus = 1.0
        if tech_effects:
            bonus += tech_effects.get("logistics_capacity_bonus", 0)
        return max(0, int((base_capacity + freighter_capacity) * bonus))

    def calculate_throughput(
        self,
        fleet=None,
        tech_effects: dict = None,
        manifest_override: Optional[dict] = None,
    ) -> dict:
        """Per-turn resource transfer, constrained by capacity.

        The fleet parameter is kept for backward compatibility but the
        new logistics system uses capacity_per_turn from colony infrastructure.
        """
        if not self.enabled:
            return {"outbound": {}, "inbound": {}}

        capacity = self.get_effective_capacity(fleet=fleet, tech_effects=tech_effects)
        throughput = {"outbound": {}, "inbound": {}}

        for direction in ("outbound", "inbound"):
            manifest_source = manifest_override or self.resource_manifest
            manifest = manifest_source.get(direction, {})
            total_requested = sum(manifest.values())
            if total_requested == 0:
                continue

            # Scale by capacity constraint
            if capacity <= 0:
                scale = 0.0
            elif total_requested > capacity:
                scale = capacity / total_requested
            else:
                scale = 1.0

            # Apply efficiency (legacy compatibility)
            scale *= self.efficiency

            for resource, amount in manifest.items():
                throughput[direction][resource] = max(0, int(amount * scale))

        return throughput

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "source_system": self.source_system,
            "destination_system": self.destination_system,
            "capacity_per_turn": self.capacity_per_turn,
            "latency_turns": self.latency_turns,
            "risk_factor": self.risk_factor,
            "enabled": self.enabled,
            "resource_manifest": {
                k: dict(v) for k, v in self.resource_manifest.items()
            },
            "auto_policy": self.auto_policy,
            "auto_allowlist": list(self.auto_allowlist),
            "auto_max_per_resource": dict(self.auto_max_per_resource),
            "assigned_ships": list(self.assigned_ships),
            "active": self.active,
            "efficiency": self.efficiency,
        }

    _INIT_FIELDS = {
        "id", "source_system", "destination_system",
        "capacity_per_turn", "latency_turns", "risk_factor", "enabled",
        "resource_manifest", "auto_policy", "auto_allowlist", "auto_max_per_resource",
        "assigned_ships", "active", "efficiency",
    }

    @classmethod
    def from_dict(cls, data: dict) -> "TradeRoute":
        return cls(**{k: v for k, v in data.items() if k in cls._INIT_FIELDS})


class TradeManager:
    def __init__(self):
        self.routes: dict[str, TradeRoute] = {}
        self.in_transit: list[Shipment] = []  # Goods currently being shipped

    @staticmethod
    def _build_auto_manifest(route: TradeRoute, colonies=None, capacity: int = 0) -> dict:
        if not colonies:
            return {"outbound": {}, "inbound": {}}

        source = colonies.colonies.get(route.source_system)
        dest = colonies.colonies.get(route.destination_system)
        if not source or not dest:
            return {"outbound": {}, "inbound": {}}

        caps = dest.get_storage_caps()
        allowlist = list(route.auto_allowlist or caps.keys())
        deficits = {}
        for resource_id in allowlist:
            cap = caps.get(resource_id, 0)
            if cap <= 0:
                continue
            current = dest.stockpiles.get(resource_id, 0)
            deficit = max(0, cap - current)
            if deficit <= 0:
                continue
            max_per = route.auto_max_per_resource.get(resource_id, 0)
            if max_per > 0:
                deficit = min(deficit, max_per)
            deficits[resource_id] = deficit

        manifest = {"outbound": {}, "inbound": {}}
        remaining = max(0, capacity)

        for resource_id, deficit in sorted(deficits.items(), key=lambda item: item[1], reverse=True):
            if remaining <= 0:
                break
            available = source.stockpiles.get(resource_id, 0)
            if available <= 0:
                continue
            amount = min(deficit, available, remaining)
            if amount <= 0:
                continue
            manifest["outbound"][resource_id] = amount
            remaining -= amount

        return manifest

    @staticmethod
    def _apply_gate_capacity(throughput: dict, capacity_limit: Optional[int]) -> dict:
        if capacity_limit is None:
            return throughput
        if capacity_limit <= 0:
            return {"outbound": {}, "inbound": {}}

        total = sum(throughput.get("outbound", {}).values()) + sum(
            throughput.get("inbound", {}).values()
        )
        if total <= capacity_limit or total == 0:
            return throughput

        scale = capacity_limit / total
        scaled = {"outbound": {}, "inbound": {}}
        for direction in ("outbound", "inbound"):
            for resource, amount in throughput.get(direction, {}).items():
                scaled[direction][resource] = max(0, int(amount * scale))
        return scaled

    def build_flow_segments(
        self,
        colonies=None,
        fleet=None,
        tech_effects: dict = None,
        galaxy=None,
    ) -> list[dict]:
        segments: list[dict] = []
        for route in self.routes.values():
            if not route.enabled:
                continue

            capacity = route.get_effective_capacity(fleet=fleet, tech_effects=tech_effects)
            manifest_override = None
            if route.auto_policy and route.auto_policy != "manual":
                manifest_override = self._build_auto_manifest(
                    route,
                    colonies=colonies,
                    capacity=capacity,
                )

            throughput = route.calculate_throughput(
                fleet=fleet,
                tech_effects=tech_effects,
                manifest_override=manifest_override,
            )

            if galaxy:
                gate_capacity = galaxy.get_path_capacity(
                    route.source_system,
                    route.destination_system,
                )
                throughput = self._apply_gate_capacity(throughput, gate_capacity)

            directions = {
                "outbound": (route.source_system, route.destination_system),
                "inbound": (route.destination_system, route.source_system),
            }
            for direction, (source, destination) in directions.items():
                resources = throughput.get(direction, {})
                if not resources:
                    continue
                dominant_resource, amount = max(
                    resources.items(),
                    key=lambda item: item[1],
                )
                if amount <= 0:
                    continue
                segments.append(
                    {
                        "source": source,
                        "destination": destination,
                        "direction": direction,
                        "resource": dominant_resource,
                        "amount": amount,
                    }
                )
        return segments

    def create_route(
        self,
        source: str,
        dest: str,
        capacity_per_turn: int = 10,
        latency_turns: int = 1,
        risk_factor: float = 0.0,
        manifest: dict = None,
        auto_policy: str = "manual",
        auto_allowlist: list = None,
        auto_max_per_resource: dict = None,
        galaxy=None,
        ships: list = None,
        colonies=None,
    ) -> Optional[TradeRoute]:
        """Create a new logistics route between two systems."""
        # Validate path exists
        distance = 1
        if galaxy:
            path = galaxy.get_path(source, dest)
            if not path:
                return None
            distance = len(path) - 1
        if latency_turns is None or latency_turns <= 0:
            latency_turns = distance

        if capacity_per_turn is None or capacity_per_turn <= 0:
            capacity_per_turn = self._infer_capacity_from_colonies(
                source,
                dest,
                colonies,
            )

        # Auto-compute latency from distance if not specified
        effective_latency = max(1, latency_turns if latency_turns > 1 else distance)

        route = TradeRoute(
            source_system=source,
            destination_system=dest,
            capacity_per_turn=capacity_per_turn,
            latency_turns=effective_latency,
            risk_factor=risk_factor,
            resource_manifest=manifest or {"outbound": {}, "inbound": {}},
            auto_policy=auto_policy,
            auto_allowlist=auto_allowlist or [],
            auto_max_per_resource=auto_max_per_resource or {},
            assigned_ships=list(ships or []),
        )

        # Efficiency decreases with distance (legacy behavior)
        route.efficiency = max(0.3, 1.0 - (distance - 1) * 0.1)

        self.routes[route.id] = route
        return route

    def _infer_capacity_from_colonies(self, source: str, dest: str, colonies=None) -> int:
        if not colonies:
            return 10

        source_colony = colonies.colonies.get(source)
        dest_colony = colonies.colonies.get(dest)

        capacities = []
        if source_colony:
            capacities.append(source_colony.get_logistics_capacity())
        if dest_colony:
            capacities.append(dest_colony.get_logistics_capacity())

        if not capacities:
            return 10

        return min(capacities)

    def cancel_route(self, route_id: str) -> bool:
        if route_id in self.routes:
            del self.routes[route_id]
            return True
        return False

    def process_arrivals(self, colonies=None) -> list:
        """Step 1 of turn resolution: deliver arrived shipments to colony stockpiles.

        Returns list of arrival reports.
        """
        arrivals = []
        still_in_transit = []

        for shipment in self.in_transit:
            if shipment.tick():
                # Shipment arrived - add to colony stockpiles
                report = {
                    "route_id": shipment.route_id,
                    "to_world": shipment.to_world,
                    "from_world": shipment.from_world,
                    "delivered": dict(shipment.resources),
                }

                if colonies:
                    colony = colonies.colonies.get(shipment.to_world)
                    if colony:
                        caps = colony.get_storage_caps()
                        for resource, amount in shipment.resources.items():
                            current = colony.stockpiles.get(resource, 0)
                            cap = caps.get(resource, 100)
                            added = min(amount, cap - current)
                            colony.stockpiles[resource] = current + max(0, added)
                            report["delivered"][resource] = max(0, added)

                arrivals.append(report)
            else:
                still_in_transit.append(shipment)

        self.in_transit = still_in_transit
        return arrivals

    def compute_and_ship(
        self,
        colonies=None,
        resources=None,
        fleet=None,
        tech_effects: dict = None,
        rng=None,
        galaxy=None,
    ) -> list:
        """Step 5 of turn resolution: compute trade flows and create shipments.

        For each active route:
        1. Calculate throughput (constrained by capacity)
        2. Check source has resources in stockpile (or global pool)
        3. Deduct from source
        4. Apply risk factor (partial loss)
        5. Create in-transit shipment with latency

        Returns list of shipment reports.
        """
        reports = []

        for route in self.routes.values():
            if not route.enabled:
                continue

            capacity = route.get_effective_capacity(fleet=fleet, tech_effects=tech_effects)
            manifest_override = None
            if route.auto_policy and route.auto_policy != "manual":
                manifest_override = self._build_auto_manifest(
                    route, colonies=colonies, capacity=capacity,
                )

            throughput = route.calculate_throughput(
                fleet=fleet,
                tech_effects=tech_effects,
                manifest_override=manifest_override,
            )
            gate_capacity = None
            if galaxy:
                gate_capacity = galaxy.get_path_capacity(
                    route.source_system,
                    route.destination_system,
                )
                throughput = self._apply_gate_capacity(throughput, gate_capacity)
            report = {
                "route_id": route.id,
                "source": route.source_system,
                "destination": route.destination_system,
                "shipped": {},
                "lost_to_risk": {},
                "disrupted": False,
            }
            if gate_capacity is not None and gate_capacity <= 0:
                report["disrupted"] = True
                report["disruption_reason"] = "gate_capacity"
                reports.append(report)
                continue
            if gate_capacity is not None:
                report["gate_capacity"] = gate_capacity

            # Process outbound (source -> destination)
            outbound_resources = {}
            for resource, amount in throughput.get("outbound", {}).items():
                if amount <= 0:
                    continue

                # Try to deduct from colony stockpile first, then global
                actual = 0
                if colonies:
                    source_colony = colonies.colonies.get(route.source_system)
                    if source_colony:
                        available = source_colony.stockpiles.get(resource, 0)
                        take = min(amount, available)
                        source_colony.stockpiles[resource] = available - take
                        actual = take

                # Fall back to global resources if colony doesn't have enough
                if actual < amount and resources:
                    remaining = amount - actual
                    taken = resources.spend_and_return_actual(
                        resource, remaining, route.source_system
                    )
                    actual += taken

                if actual > 0:
                    # Apply risk factor
                    lost = 0
                    if route.risk_factor > 0 and rng:
                        if rng.random() < route.risk_factor:
                            lost = max(1, int(actual * 0.3))
                            actual = max(0, actual - lost)
                            report["lost_to_risk"][resource] = lost

                    outbound_resources[resource] = actual
                    report["shipped"][f"outbound_{resource}"] = actual

            if outbound_resources:
                self.in_transit.append(Shipment(
                    route_id=route.id,
                    from_world=route.source_system,
                    to_world=route.destination_system,
                    resources=outbound_resources,
                    turns_remaining=route.latency_turns,
                ))

            # Process inbound (destination -> source)
            inbound_resources = {}
            for resource, amount in throughput.get("inbound", {}).items():
                if amount <= 0:
                    continue

                actual = 0
                if colonies:
                    dest_colony = colonies.colonies.get(route.destination_system)
                    if dest_colony:
                        available = dest_colony.stockpiles.get(resource, 0)
                        take = min(amount, available)
                        dest_colony.stockpiles[resource] = available - take
                        actual = take

                if actual < amount and resources:
                    remaining = amount - actual
                    taken = resources.spend_and_return_actual(
                        resource, remaining, route.destination_system
                    )
                    actual += taken

                if actual > 0:
                    lost = 0
                    if route.risk_factor > 0 and rng:
                        if rng.random() < route.risk_factor:
                            lost = max(1, int(actual * 0.3))
                            actual = max(0, actual - lost)
                            report["lost_to_risk"][resource] = lost

                    inbound_resources[resource] = actual
                    report["shipped"][f"inbound_{resource}"] = actual

            if inbound_resources:
                self.in_transit.append(Shipment(
                    route_id=route.id,
                    from_world=route.destination_system,
                    to_world=route.source_system,
                    resources=inbound_resources,
                    turns_remaining=route.latency_turns,
                ))

            reports.append(report)

        return reports

    def process_turn(self, resources=None, fleet=None, tech_effects: dict = None, galaxy=None) -> list:
        """Legacy method: process trade routes with immediate transfer.

        Kept for backward compatibility. New code should use
        process_arrivals() + compute_and_ship() for latency-based logistics.
        """
        reports = []

        for route in self.routes.values():
            if not route.active or not route.enabled:
                continue

            throughput = route.calculate_throughput(fleet=fleet, tech_effects=tech_effects)
            gate_capacity = None
            if galaxy:
                gate_capacity = galaxy.get_path_capacity(
                    route.source_system,
                    route.destination_system,
                )
                throughput = self._apply_gate_capacity(throughput, gate_capacity)
            report = {
                "route_id": route.id,
                "source": route.source_system,
                "destination": route.destination_system,
                "transferred": {},
                "disrupted": False,
            }
            if gate_capacity is not None and gate_capacity <= 0:
                report["disrupted"] = True
                report["disruption_reason"] = "gate_capacity"
                reports.append(report)
                continue
            if gate_capacity is not None:
                report["gate_capacity"] = gate_capacity

            if resources:
                for resource, amount in throughput.get("outbound", {}).items():
                    if amount > 0 and resources.global_resources.get(resource, 0) >= amount:
                        resources.spend(resource, amount, route.source_system)
                        resources.add(resource, amount, route.destination_system)
                        report["transferred"][f"outbound_{resource}"] = amount

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
                "enabled": r.enabled,
                "efficiency": r.efficiency,
                "capacity": r.capacity_per_turn,
                "latency": r.latency_turns,
                "risk": r.risk_factor,
                "ships": len(r.assigned_ships),
            }
            for r in self.routes.values()
        ]

    def get_in_transit_summary(self) -> list:
        return [
            {
                "route_id": s.route_id,
                "from": s.from_world,
                "to": s.to_world,
                "resources": dict(s.resources),
                "arrives_in": s.turns_remaining,
            }
            for s in self.in_transit
        ]

    def to_dict(self) -> dict:
        return {
            "routes": {rid: r.to_dict() for rid, r in self.routes.items()},
            "in_transit": [s.to_dict() for s in self.in_transit],
        }

    @classmethod
    def from_dict(cls, data: dict) -> "TradeManager":
        tm = cls()
        for rid, rdata in data.get("routes", {}).items():
            tm.routes[rid] = TradeRoute.from_dict(rdata)
        tm.in_transit = [
            Shipment.from_dict(s) for s in data.get("in_transit", [])
        ]
        return tm
