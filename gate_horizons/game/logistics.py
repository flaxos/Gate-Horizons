"""Freighter-based logistics system for Gate Horizons.

Ships execute player-defined routes (A -> B -> C) with:
- Cargo capacity (mass units)
- Travel time based on ship speed and distance
- Operating costs per trip
- Load/unload rules per waypoint (resource, min/max thresholds)

This complements the existing abstracted trade system by adding
physical freighter movement along routes.
"""

from __future__ import annotations

import uuid
from typing import Optional


class CargoRule:
    """Defines what to load/unload at a waypoint."""

    def __init__(
        self,
        resource_id: str = "",
        action: str = "load",  # "load" or "unload"
        amount: int = 0,  # 0 = as much as possible
        min_threshold: int = 0,  # Only load if source has > min
        max_threshold: int = 0,  # Only unload if dest has < max (0 = ignore)
    ):
        self.resource_id = resource_id
        self.action = action
        self.amount = amount
        self.min_threshold = min_threshold
        self.max_threshold = max_threshold

    def to_dict(self) -> dict:
        return {
            "resource_id": self.resource_id,
            "action": self.action,
            "amount": self.amount,
            "min_threshold": self.min_threshold,
            "max_threshold": self.max_threshold,
        }

    @classmethod
    def from_dict(cls, data: dict) -> "CargoRule":
        return cls(
            resource_id=data.get("resource_id", ""),
            action=data.get("action", "load"),
            amount=data.get("amount", 0),
            min_threshold=data.get("min_threshold", 0),
            max_threshold=data.get("max_threshold", 0),
        )


class Waypoint:
    """A stop on a freight route."""

    def __init__(
        self,
        system_id: str = "",
        cargo_rules: list = None,
        wait_turns: int = 0,
    ):
        self.system_id = system_id
        self.cargo_rules = cargo_rules or []
        self.wait_turns = wait_turns  # Turns to wait at this stop

    def to_dict(self) -> dict:
        return {
            "system_id": self.system_id,
            "cargo_rules": [r.to_dict() for r in self.cargo_rules],
            "wait_turns": self.wait_turns,
        }

    @classmethod
    def from_dict(cls, data: dict) -> "Waypoint":
        return cls(
            system_id=data.get("system_id", ""),
            cargo_rules=[CargoRule.from_dict(r) for r in data.get("cargo_rules", [])],
            wait_turns=data.get("wait_turns", 0),
        )


class FreighterRoute:
    """A player-defined freight route with ordered waypoints.

    Ships assigned to a route cycle through waypoints, loading/unloading
    cargo per the rules at each stop.
    """

    def __init__(
        self,
        id: str = None,
        name: str = "Unnamed Route",
        waypoints: list = None,
        assigned_ship_id: str = None,
        active: bool = True,
        current_waypoint_index: int = 0,
        waiting_turns: int = 0,
    ):
        self.id = id or str(uuid.uuid4())[:8]
        self.name = name
        self.waypoints = waypoints or []
        self.assigned_ship_id = assigned_ship_id
        self.active = active
        self.current_waypoint_index = current_waypoint_index
        self.waiting_turns = waiting_turns

    @property
    def current_waypoint(self) -> Optional[Waypoint]:
        if not self.waypoints:
            return None
        idx = self.current_waypoint_index % len(self.waypoints)
        return self.waypoints[idx]

    def advance_waypoint(self) -> None:
        """Move to the next waypoint in the cycle."""
        if self.waypoints:
            self.current_waypoint_index = (
                (self.current_waypoint_index + 1) % len(self.waypoints)
            )
            self.waiting_turns = 0

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "name": self.name,
            "waypoints": [w.to_dict() for w in self.waypoints],
            "assigned_ship_id": self.assigned_ship_id,
            "active": self.active,
            "current_waypoint_index": self.current_waypoint_index,
            "waiting_turns": self.waiting_turns,
        }

    @classmethod
    def from_dict(cls, data: dict) -> "FreighterRoute":
        return cls(
            id=data.get("id"),
            name=data.get("name", "Unnamed Route"),
            waypoints=[Waypoint.from_dict(w) for w in data.get("waypoints", [])],
            assigned_ship_id=data.get("assigned_ship_id"),
            active=data.get("active", True),
            current_waypoint_index=data.get("current_waypoint_index", 0),
            waiting_turns=data.get("waiting_turns", 0),
        )


class LogisticsManager:
    """Manages freighter routes and their execution."""

    def __init__(self):
        self.routes: dict[str, FreighterRoute] = {}

    def create_route(
        self,
        name: str,
        waypoints: list,
        assigned_ship_id: str = None,
    ) -> FreighterRoute:
        """Create a new freight route."""
        route = FreighterRoute(
            name=name,
            waypoints=[
                Waypoint.from_dict(w) if isinstance(w, dict) else w
                for w in waypoints
            ],
            assigned_ship_id=assigned_ship_id,
        )
        self.routes[route.id] = route
        return route

    def cancel_route(self, route_id: str) -> bool:
        if route_id in self.routes:
            del self.routes[route_id]
            return True
        return False

    def get_route_for_ship(self, ship_id: str) -> Optional[FreighterRoute]:
        for route in self.routes.values():
            if route.assigned_ship_id == ship_id:
                return route
        return None

    def process_routes(self, fleet, colonies, galaxy, production_inventories) -> list:
        """Execute one tick of all active freight routes.

        For each active route with an assigned ship:
        1. If ship is at current waypoint system: execute cargo rules, then
           set course for next waypoint.
        2. If ship is in transit: do nothing (movement handled by FleetManager).
        3. If ship is idle at wrong system: set course for current waypoint.

        Args:
            fleet: FleetManager
            colonies: ColonyManager
            galaxy: GalaxyMap
            production_inventories: dict of {system_id: dict} for production resources

        Returns:
            List of route execution reports.
        """
        reports = []

        for route in self.routes.values():
            if not route.active or not route.assigned_ship_id:
                continue
            if not route.waypoints:
                continue

            ship = fleet.ships.get(route.assigned_ship_id)
            if not ship:
                continue

            report = {
                "route_id": route.id,
                "route_name": route.name,
                "ship_id": ship.id,
                "ship_name": ship.name,
                "actions": [],
            }

            waypoint = route.current_waypoint
            if not waypoint:
                continue

            # Ship is in transit — skip
            if ship.path:
                report["actions"].append({"type": "in_transit", "to": ship.destination})
                reports.append(report)
                continue

            # Ship at current waypoint
            if ship.location == waypoint.system_id:
                # Wait if required
                if route.waiting_turns < waypoint.wait_turns:
                    route.waiting_turns += 1
                    report["actions"].append({
                        "type": "waiting",
                        "turns_left": waypoint.wait_turns - route.waiting_turns,
                    })
                    reports.append(report)
                    continue

                # Execute cargo rules
                cargo_actions = self._execute_cargo_rules(
                    ship, waypoint, colonies, production_inventories,
                )
                report["actions"].extend(cargo_actions)

                # Advance to next waypoint and set course
                route.advance_waypoint()
                next_wp = route.current_waypoint
                if next_wp and next_wp.system_id != ship.location:
                    moved = fleet.move_ship(ship.id, next_wp.system_id, galaxy)
                    if moved:
                        report["actions"].append({
                            "type": "departing",
                            "to": next_wp.system_id,
                        })
                    else:
                        report["actions"].append({
                            "type": "no_path",
                            "to": next_wp.system_id,
                        })
            else:
                # Ship is idle but not at waypoint — set course
                moved = fleet.move_ship(ship.id, waypoint.system_id, galaxy)
                if moved:
                    report["actions"].append({
                        "type": "repositioning",
                        "to": waypoint.system_id,
                    })

            reports.append(report)

        return reports

    def _execute_cargo_rules(
        self,
        ship,
        waypoint: Waypoint,
        colonies,
        production_inventories: dict,
    ) -> list:
        """Execute cargo load/unload rules at a waypoint.

        Operates on both legacy colony stockpiles and production inventories.
        """
        actions = []
        system_id = waypoint.system_id
        colony = colonies.colonies.get(system_id) if colonies else None
        prod_inv = production_inventories.setdefault(system_id, {})

        for rule in waypoint.cargo_rules:
            res = rule.resource_id
            if rule.action == "load":
                actions.extend(
                    self._load_cargo(ship, res, rule, colony, prod_inv)
                )
            elif rule.action == "unload":
                actions.extend(
                    self._unload_cargo(ship, res, rule, colony, prod_inv)
                )

        return actions

    def _load_cargo(self, ship, resource_id, rule, colony, prod_inv) -> list:
        """Load cargo from colony/production inventory onto ship."""
        actions = []
        available = 0

        # Check production inventory first
        if resource_id in prod_inv:
            available = prod_inv.get(resource_id, 0)
        elif colony and resource_id in colony.stockpiles:
            available = colony.stockpiles.get(resource_id, 0)

        # Apply min threshold
        if rule.min_threshold > 0 and available <= rule.min_threshold:
            return actions

        # Don't take below threshold
        loadable = available - rule.min_threshold if rule.min_threshold > 0 else available

        # Respect specified amount
        if rule.amount > 0:
            loadable = min(loadable, rule.amount)

        # Respect ship cargo capacity
        loadable = min(loadable, ship.cargo_free)

        if loadable <= 0:
            return actions

        # Deduct from source
        if resource_id in prod_inv and prod_inv.get(resource_id, 0) >= loadable:
            prod_inv[resource_id] -= loadable
        elif colony and resource_id in colony.stockpiles:
            colony.stockpiles[resource_id] = max(
                0, colony.stockpiles.get(resource_id, 0) - loadable
            )

        ship.add_cargo(resource_id, loadable)
        actions.append({
            "type": "loaded",
            "resource": resource_id,
            "amount": loadable,
            "at": ship.location,
        })
        return actions

    def _unload_cargo(self, ship, resource_id, rule, colony, prod_inv) -> list:
        """Unload cargo from ship to colony/production inventory."""
        actions = []
        on_ship = ship.cargo.get(resource_id, 0)
        if on_ship <= 0:
            return actions

        # Apply max threshold (only unload if dest is below max)
        if rule.max_threshold > 0:
            current_at_dest = prod_inv.get(resource_id, 0)
            if colony and resource_id in colony.stockpiles:
                current_at_dest = max(current_at_dest, colony.stockpiles.get(resource_id, 0))
            if current_at_dest >= rule.max_threshold:
                return actions

        unloadable = on_ship
        if rule.amount > 0:
            unloadable = min(unloadable, rule.amount)

        if unloadable <= 0:
            return actions

        ship.remove_cargo(resource_id, unloadable)

        # Add to production inventory or colony stockpile
        if resource_id in prod_inv or resource_id not in (colony.stockpiles if colony else {}):
            prod_inv[resource_id] = prod_inv.get(resource_id, 0) + unloadable
        elif colony:
            colony.stockpiles[resource_id] = colony.stockpiles.get(resource_id, 0) + unloadable

        actions.append({
            "type": "unloaded",
            "resource": resource_id,
            "amount": unloadable,
            "at": ship.location,
        })
        return actions

    def get_route_summary(self) -> list:
        return [
            {
                "id": r.id,
                "name": r.name,
                "waypoints": [w.system_id for w in r.waypoints],
                "ship_id": r.assigned_ship_id,
                "active": r.active,
                "current_wp": r.current_waypoint_index,
            }
            for r in self.routes.values()
        ]

    def to_dict(self) -> dict:
        return {
            "routes": {rid: r.to_dict() for rid, r in self.routes.items()},
        }

    @classmethod
    def from_dict(cls, data: dict) -> "LogisticsManager":
        lm = cls()
        for rid, rdata in data.get("routes", {}).items():
            lm.routes[rid] = FreighterRoute.from_dict(rdata)
        return lm
