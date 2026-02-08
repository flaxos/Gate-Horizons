"""Ship system with contextual actions for Gate Horizons."""

import json
import uuid
from dataclasses import dataclass, field
from typing import Optional, Union

from .types import Traversable


@dataclass
class ShipStats:
    max_hull: int = 30
    speed: int = 1
    cargo_capacity: int = 10
    freight_capacity: int = 0
    sensor_range: int = 1
    fuel_capacity: int = 8
    combat_power: int = 5
    maintenance_cost: int = 3
    abilities: list = field(default_factory=list)

    def to_dict(self) -> dict:
        return {
            "max_hull": self.max_hull,
            "speed": self.speed,
            "cargo_capacity": self.cargo_capacity,
            "freight_capacity": self.freight_capacity,
            "sensor_range": self.sensor_range,
            "fuel_capacity": self.fuel_capacity,
            "combat_power": self.combat_power,
            "maintenance_cost": self.maintenance_cost,
            "abilities": list(self.abilities),
        }

    @classmethod
    def from_dict(cls, data: dict) -> "ShipStats":
        return cls(**{k: v for k, v in data.items() if k in cls.__dataclass_fields__})


@dataclass
class TradeRoute:
    id: str = ""
    source_system: str = ""
    destination_system: str = ""
    resource_manifest: dict = field(default_factory=dict)
    active: bool = True

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "source_system": self.source_system,
            "destination_system": self.destination_system,
            "resource_manifest": dict(self.resource_manifest),
            "active": self.active,
        }

    @classmethod
    def from_dict(cls, data: dict) -> "TradeRoute":
        return cls(**{k: v for k, v in data.items() if k in cls.__dataclass_fields__})


@dataclass
class Action:
    name: str
    description: str = ""
    cost: dict = field(default_factory=dict)
    turns: int = 0
    risk: str = "none"  # none, low, medium, high

    def to_dict(self) -> dict:
        return {
            "name": self.name,
            "description": self.description,
            "cost": dict(self.cost),
            "turns": self.turns,
            "risk": self.risk,
        }


@dataclass
class MovementResult:
    ship_id: str
    arrived: bool = False
    current_location: str = ""
    remaining_path: list = field(default_factory=list)
    fuel_consumed: int = 0
    discoveries: list = field(default_factory=list)


class Ship:
    def __init__(
        self,
        id: str = None,
        name: str = "Unnamed Ship",
        ship_class: str = "scout",
        location: str = "",
        destination: str = None,
        path: list = None,
        stats: dict = None,
        cargo: dict = None,
        fuel: int = 0,
        hull: int = 0,
        morale: int = 80,
        mission: str = None,
        mission_target: str = None,
        trade_route: dict = None,
        mining: bool = False,
    ):
        self.id = id or str(uuid.uuid4())[:8]
        self.name = name
        self.ship_class = ship_class
        self.location = location
        self.destination = destination
        self.path = path or []
        self.stats = ShipStats.from_dict(stats) if isinstance(stats, dict) else (stats or ShipStats())
        self.cargo = cargo or {}
        self.fuel = fuel if fuel else (self.stats.fuel_capacity if self.stats else 8)
        self.hull = hull if hull else (self.stats.max_hull if self.stats else 30)
        self.morale = morale
        self.mission = mission
        self.mission_target = mission_target
        self.trade_route = (
            TradeRoute.from_dict(trade_route)
            if isinstance(trade_route, dict) and trade_route
            else trade_route
        )
        self.mining = mining

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "name": self.name,
            "ship_class": self.ship_class,
            "location": self.location,
            "destination": self.destination,
            "path": list(self.path),
            "stats": self.stats.to_dict(),
            "cargo": dict(self.cargo),
            "fuel": self.fuel,
            "hull": self.hull,
            "morale": self.morale,
            "mission": self.mission,
            "mission_target": self.mission_target,
            "trade_route": self.trade_route.to_dict() if isinstance(self.trade_route, TradeRoute) else self.trade_route,
            "mining": self.mining,
        }

    _INIT_FIELDS = {
        "id", "name", "ship_class", "location", "destination", "path",
        "stats", "cargo", "fuel", "hull", "morale", "mission",
        "mission_target", "trade_route", "mining",
    }

    @classmethod
    def from_dict(cls, data: dict) -> "Ship":
        d = {k: v for k, v in data.items() if k in cls._INIT_FIELDS}
        return cls(**d)

    @property
    def cargo_used(self) -> int:
        return sum(self.cargo.values())

    @property
    def cargo_free(self) -> int:
        return self.stats.cargo_capacity - self.cargo_used

    @property
    def hull_percent(self) -> float:
        if self.stats.max_hull == 0:
            return 0.0
        return self.hull / self.stats.max_hull

    def add_cargo(self, resource: str, amount: int) -> int:
        """Add cargo, returns amount actually added."""
        can_add = min(amount, self.cargo_free)
        if can_add > 0:
            self.cargo[resource] = self.cargo.get(resource, 0) + can_add
        return can_add

    def remove_cargo(self, resource: str, amount: int) -> int:
        """Remove cargo, returns amount actually removed."""
        current = self.cargo.get(resource, 0)
        removed = min(amount, current)
        if removed > 0:
            self.cargo[resource] = current - removed
            if self.cargo[resource] <= 0:
                del self.cargo[resource]
        return removed


class FleetManager:
    def __init__(self):
        self.ships: dict[str, Ship] = {}
        self._ship_templates: dict[str, dict] = {}

    def load_templates(self, filepath: Union[str, Traversable]) -> None:
        if hasattr(filepath, "read_text"):
            self._ship_templates = json.loads(filepath.read_text(encoding="utf-8"))
        else:
            with open(filepath, "r", encoding="utf-8") as f:
                self._ship_templates = json.load(f)

    def create_ship(self, ship_class: str, location: str, name: str = None) -> Optional[Ship]:
        template = self._ship_templates.get(ship_class)
        if not template:
            return None

        stats = ShipStats(
            max_hull=template["max_hull"],
            speed=template["speed"],
            cargo_capacity=template["cargo_capacity"],
            freight_capacity=template.get("freight_capacity", 0),
            sensor_range=template["sensor_range"],
            fuel_capacity=template["fuel_capacity"],
            combat_power=template["combat_power"],
            maintenance_cost=template["maintenance_cost"],
            abilities=list(template.get("abilities", [])),
        )

        ship = Ship(
            name=name or template["name"],
            ship_class=ship_class,
            location=location,
            stats=stats,
            fuel=template["fuel_capacity"],
            hull=template["max_hull"],
        )

        self.ships[ship.id] = ship
        return ship

    def move_ship(self, ship_id: str, destination_id: str, galaxy=None) -> bool:
        """Set a ship's destination. If galaxy provided, validates and computes path."""
        ship = self.ships.get(ship_id)
        if not ship:
            return False
        if destination_id == ship.location:
            return False

        if galaxy:
            path = galaxy.get_path(ship.location, destination_id)
            if not path:
                return False
            path = path[1:]  # Remove current location
            if not path:
                return False
            ship.path = path
        else:
            ship.path = [destination_id]

        ship.destination = destination_id
        ship.mission = "moving"
        ship.mining = False
        return True

    def process_movement(self, ship_id: str, fuel_efficiency: float = 1.0) -> MovementResult:
        """Advance a ship along its path by its speed stat.

        Args:
            ship_id: Ship to move.
            fuel_efficiency: Tech multiplier (e.g. 1.2 = 20% less fuel).
                Fuel cost = max(1, round(hops / efficiency)).
        """
        ship = self.ships.get(ship_id)
        if not ship or not ship.path:
            return MovementResult(
                ship_id=ship_id,
                arrived=True,
                current_location=ship.location if ship else "",
            )

        moves = min(ship.stats.speed, len(ship.path))

        # Calculate fuel cost with efficiency
        eff = max(1.0, fuel_efficiency)
        fuel_cost = max(1, round(moves / eff))

        if ship.fuel < fuel_cost:
            # Reduce moves to what fuel allows
            affordable_moves = max(0, int(ship.fuel * eff))
            moves = min(moves, affordable_moves)
            if moves == 0:
                return MovementResult(
                    ship_id=ship_id,
                    arrived=False,
                    current_location=ship.location,
                    remaining_path=list(ship.path),
                    fuel_consumed=0,
                )
            fuel_cost = max(1, round(moves / eff))

        for _ in range(moves):
            ship.location = ship.path.pop(0)

        ship.fuel -= fuel_cost

        arrived = len(ship.path) == 0
        if arrived:
            ship.destination = None
            ship.mission = None

        return MovementResult(
            ship_id=ship_id,
            arrived=arrived,
            current_location=ship.location,
            remaining_path=list(ship.path),
            fuel_consumed=fuel_cost,
        )

    def get_ships_at(self, system_id: str) -> list:
        return [s for s in self.ships.values() if s.location == system_id]

    @staticmethod
    def is_intra_system_move(origin_system_id: str, destination_system_id: str) -> bool:
        """Check if a move is within the same star system (no turn cost).

        Uses system ID comparison — same system means same gravity well.
        """
        if not origin_system_id or not destination_system_id:
            return False
        return origin_system_id == destination_system_id

    def move_ship_local(self, ship_id: str, destination_system_id: str) -> bool:
        """Move a ship within the same system instantly (no turn cost).

        This represents intra-system repositioning — e.g. moving from
        one planet to another within the same star system. The ship's
        location stays the same system_id since the game model tracks
        ships by system. This method validates the move is local and
        clears any existing path/mission.

        Returns True if the ship was already at the system (local move).
        """
        ship = self.ships.get(ship_id)
        if not ship:
            return False
        if not self.is_intra_system_move(ship.location, destination_system_id):
            return False
        # Ship is already at this system — clear movement state
        ship.path.clear()
        ship.destination = None
        ship.mission = None
        ship.mining = False
        return True

    def get_contextual_actions(self, ship_id: str, galaxy=None, colonies=None) -> list:
        """Return available actions based on ship class, location, and state."""
        ship = self.ships.get(ship_id)
        if not ship:
            return []

        actions = []
        abilities = ship.stats.abilities
        location = galaxy.systems.get(ship.location) if galaxy else None
        has_colony = False
        has_spaceport = False
        has_anomaly = location and len(location.anomalies) > 0 if location else False
        has_asteroids = False
        has_hostiles = False

        if colonies and ship.location in colonies.colonies:
            has_colony = True
            colony = colonies.colonies[ship.location]
            has_spaceport = colony.infrastructure.get("spaceport", {}).get("level", 0) > 0

        if location:
            for planet in location.planets:
                if planet.type == "barren" or "asteroid" in planet.type.lower():
                    has_asteroids = True
                if planet.resources.get("metals", 0) > 0 or planet.resources.get("exotics", 0) > 0:
                    has_asteroids = True

        # Movement is always available
        actions.append(Action(
            name="Move To",
            description="Set course for another system",
        ))

        # Ship is in transit
        if ship.path:
            actions.insert(0, Action(name="Continue", description="Continue on current course"))
            actions.append(Action(name="Reroute", description="Change destination"))
            actions.append(Action(name="Emergency Stop", description="Halt at current position"))
            return actions

        # Scout actions
        if ship.ship_class == "scout":
            if location and not location.surveyed:
                actions.insert(0, Action(
                    name="Scan System",
                    description="Perform detailed survey of this system",
                    turns=1,
                ))
            if "probe_deploy" in abilities:
                actions.append(Action(
                    name="Deploy Probe",
                    description="Deploy a long-range sensor probe",
                    cost={"credits": 5},
                ))
            if has_anomaly and "investigate" in abilities:
                actions.append(Action(
                    name="Investigate Anomaly",
                    description="Investigate detected anomaly",
                    risk="medium",
                ))
            if not ship.path:
                actions.append(Action(
                    name="Patrol",
                    description="Patrol this system for threats",
                ))
            actions.append(Action(
                name="Return Home",
                description="Return to nearest colony",
            ))

        # Freighter actions
        elif ship.ship_class == "freighter":
            if has_colony:
                if ship.cargo_used > 0:
                    actions.insert(0, Action(
                        name="Unload Cargo",
                        description="Unload cargo at this colony",
                    ))
                actions.append(Action(
                    name="Load Cargo",
                    description="Load available resources",
                ))
                if "set_trade_route" in abilities:
                    actions.append(Action(
                        name="Set Trade Route",
                        description="Establish automated trade route",
                    ))
            if "emergency_jettison" in abilities and ship.cargo_used > 0:
                actions.append(Action(
                    name="Emergency Jettison",
                    description="Dump cargo for speed boost",
                    risk="low",
                ))

        # Miner actions
        elif ship.ship_class == "miner":
            if ship.mining:
                actions.insert(0, Action(
                    name="Continue Mining",
                    description="Continue current mining operation",
                ))
            elif has_asteroids or (location and any(
                p.resources for p in location.planets
            )):
                actions.insert(0, Action(
                    name="Begin Mining",
                    description="Start mining resources in this system",
                ))
                if "prospect" in abilities:
                    actions.append(Action(
                        name="Prospect",
                        description="Survey resource deposits for quality",
                    ))
            if "auto_mine" in abilities:
                actions.append(Action(
                    name="Set Auto-Mine",
                    description="Set up automated mining cycle",
                ))
            if ship.cargo_used > 0:
                actions.append(Action(
                    name="Deliver Cargo",
                    description="Deliver mined resources to nearest colony",
                ))

        # Corvette actions
        elif ship.ship_class == "corvette":
            if "patrol" in abilities:
                actions.insert(0, Action(
                    name="Patrol",
                    description="Patrol this system",
                ))
            if "escort" in abilities:
                actions.append(Action(
                    name="Escort",
                    description="Escort another ship",
                ))
            if has_hostiles:
                if "intercept" in abilities:
                    actions.append(Action(
                        name="Intercept",
                        description="Intercept hostile contacts",
                        risk="high",
                    ))
                if "engage" in abilities:
                    actions.append(Action(
                        name="Engage",
                        description="Engage enemy forces",
                        risk="high",
                    ))
                actions.append(Action(
                    name="Retreat",
                    description="Withdraw from engagement",
                ))
                actions.append(Action(
                    name="Hail",
                    description="Attempt communication",
                ))
            if "blockade" in abilities and has_colony:
                actions.append(Action(
                    name="Blockade",
                    description="Establish system blockade",
                ))

        # Universal actions at colony with spaceport
        if has_spaceport:
            if ship.hull < ship.stats.max_hull:
                actions.append(Action(
                    name="Repair",
                    description=f"Repair hull ({ship.hull}/{ship.stats.max_hull})",
                    cost={"credits": (ship.stats.max_hull - ship.hull) * 2},
                ))
            if ship.fuel < ship.stats.fuel_capacity:
                actions.append(Action(
                    name="Refuel",
                    description=f"Refuel ({ship.fuel}/{ship.stats.fuel_capacity})",
                    cost={"energy": (ship.stats.fuel_capacity - ship.fuel)},
                ))

        return actions

    def destroy_ship(self, ship_id: str) -> bool:
        if ship_id in self.ships:
            del self.ships[ship_id]
            return True
        return False

    def repair_ship(self, ship_id: str, amount: int) -> bool:
        ship = self.ships.get(ship_id)
        if not ship:
            return False
        ship.hull = min(ship.hull + amount, ship.stats.max_hull)
        return True

    def get_total_maintenance(self) -> int:
        return sum(s.stats.maintenance_cost for s in self.ships.values())

    def to_dict(self) -> dict:
        return {
            "ships": {sid: s.to_dict() for sid, s in self.ships.items()},
            "ship_templates": self._ship_templates,
        }

    @classmethod
    def from_dict(cls, data: dict) -> "FleetManager":
        fm = cls()
        fm._ship_templates = data.get("ship_templates", {})
        for sid, sdata in data.get("ships", {}).items():
            fm.ships[sid] = Ship.from_dict(sdata)
        return fm
