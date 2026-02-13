"""Star map graph system for Gate Horizons."""

import json
import random
from typing import Union
from collections import deque
from dataclasses import dataclass, field
from typing import Optional

from .types import Traversable
from gate_horizons.astro import SystemGenerator


@dataclass
class Planet:
    id: str
    name: str
    type: str  # rocky, gas_giant, ice, volcanic, oceanic, barren, desert, toxic, garden, moon
    body_type: str = ""  # terrestrial, gas_giant, moon, asteroid_belt
    orbit_index: float = 0.0
    semi_major_axis_au: float = 0.0
    resources: dict = field(default_factory=dict)
    colonizable: bool = False
    description: str = ""
    habitability: float = 0.5  # 0.0 (hostile) to 1.0 (earthlike)
    gravity: float = 1.0  # relative to Earth (1.0)
    baseline_output: dict = field(default_factory=dict)  # base per-turn yields before infrastructure
    traits: list = field(default_factory=list)  # e.g. ["hub", "frontier", "mineral_rich"]

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "name": self.name,
            "type": self.type,
            "body_type": self.body_type,
            "orbit_index": self.orbit_index,
            "semi_major_axis_au": self.semi_major_axis_au,
            "resources": dict(self.resources),
            "colonizable": self.colonizable,
            "description": self.description,
            "habitability": self.habitability,
            "gravity": self.gravity,
            "baseline_output": dict(self.baseline_output),
            "traits": list(self.traits),
        }

    @classmethod
    def from_dict(cls, data: dict) -> "Planet":
        return cls(**{k: v for k, v in data.items() if k in cls.__dataclass_fields__})


class StarSystem:
    def __init__(
        self,
        id: str,
        name: str,
        x: float = 0.0,
        y: float = 0.0,
        discovered: bool = False,
        surveyed: bool = False,
        tier: int = 0,
        stars: list = None,
        planets: list = None,
        stationed_ships: list = None,
        colony: dict = None,
        gate_connections: list = None,
        gate_active: bool = True,
        gate_activation_cost: dict = None,
        gate_status: float = 1.0,
        gate_capacity: int = 100,
        gate_repair_cost: dict = None,
        anomalies: list = None,
    ):
        self.id = id
        self.name = name
        self.x = x
        self.y = y
        self.discovered = discovered
        self.surveyed = surveyed
        self.tier = tier
        self.stars = stars or []
        self.planets = [
            Planet.from_dict(p) if isinstance(p, dict) else p
            for p in (planets or [])
        ]
        self.stationed_ships = stationed_ships or []
        self.colony = colony
        self.gate_connections = gate_connections or []
        self.gate_active = gate_active
        self.gate_activation_cost = gate_activation_cost or {}
        self.gate_status = max(0.0, min(1.0, float(gate_status)))
        self.gate_capacity = max(0, int(gate_capacity))
        self.gate_repair_cost = gate_repair_cost or {}
        self.anomalies = anomalies or []

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "name": self.name,
            "x": self.x,
            "y": self.y,
            "discovered": self.discovered,
            "surveyed": self.surveyed,
            "tier": self.tier,
            "stars": list(self.stars),
            "planets": [p.to_dict() for p in self.planets],
            "stationed_ships": list(self.stationed_ships),
            "colony": self.colony,
            "gate_connections": list(self.gate_connections),
            "gate_active": self.gate_active,
            "gate_activation_cost": dict(self.gate_activation_cost),
            "gate_status": self.gate_status,
            "gate_capacity": self.gate_capacity,
            "gate_repair_cost": dict(self.gate_repair_cost),
            "anomalies": list(self.anomalies),
        }

    @classmethod
    def from_dict(cls, data: dict) -> "StarSystem":
        d = dict(data)
        d["planets"] = [Planet.from_dict(p) for p in d.get("planets", [])]
        # Normalize gate_connections from [{target, status}] to [str] if needed
        raw_conns = d.get("gate_connections", [])
        if raw_conns and isinstance(raw_conns[0], dict):
            d["gate_connections"] = [c["target"] for c in raw_conns]
        # Remove unknown keys that aren't constructor params
        valid_keys = {
            "id", "name", "x", "y", "discovered", "surveyed", "tier",
            "stars", "planets", "stationed_ships", "colony", "gate_connections",
            "gate_active", "gate_activation_cost", "gate_status",
            "gate_capacity", "gate_repair_cost", "anomalies",
        }
        d = {k: v for k, v in d.items() if k in valid_keys}
        return cls(**d)


class GalaxyMap:
    def __init__(self):
        self.systems: dict[str, StarSystem] = {}
        self._path_cache: dict[tuple, list] = {}

    def load_from_json(self, filepath: Union[str, Traversable]) -> None:
        if hasattr(filepath, "read_text"):
            data = json.loads(filepath.read_text(encoding="utf-8"))
        else:
            with open(filepath, "r", encoding="utf-8") as f:
                data = json.load(f)

        systems_data = data if isinstance(data, list) else data.get("systems", [])
        self.systems.clear()
        self._path_cache.clear()

        for sys_data in systems_data:
            # Normalize gate_connections from [{target, status}] to [str]
            raw_conns = sys_data.get("gate_connections", [])
            if raw_conns and isinstance(raw_conns[0], dict):
                sys_data["gate_connections"] = [
                    c["target"] for c in raw_conns
                ]
            system = StarSystem.from_dict(sys_data)
            self.systems[system.id] = system

    def generate_procedural(
        self,
        seed: int | None = None,
        system_count: int = 12,
        max_connections: int = 3,
        width: int = 1200,
        height: int = 700,
        known_system_ids: set[str] | None = None,
    ) -> None:
        rng = random.Random(seed)
        self.systems.clear()
        self._path_cache.clear()
        generator = SystemGenerator()
        known_system_ids = set(known_system_ids or [])

        system_ids = []
        for idx in range(system_count):
            sys_id = f"sys_{idx + 1:02d}"
            system_ids.append(sys_id)
            name = f"Sector {idx + 1:02d}"
            x = rng.uniform(80, width - 80)
            y = rng.uniform(80, height - 80)
            tier = rng.randint(1, 4)
            gate_connections = []

            generated = generator.generate_system(sys_id, name, rng, use_known=sys_id in known_system_ids)
            stars = generated.stars or [{"name": name, "spectral": "G"}]
            planets = [
                Planet.from_dict(p) if isinstance(p, dict) else p
                for p in generated.planets
            ]

            system = StarSystem(
                id=sys_id,
                name=name,
                x=round(x, 2),
                y=round(y, 2),
                discovered=False,
                surveyed=False,
                tier=tier,
                stars=stars,
                planets=planets,
                gate_connections=gate_connections,
                gate_active=True,
                gate_status=1.0,
                gate_capacity=rng.randint(60, 120),
            )
            self.systems[sys_id] = system

        # Ensure base connectivity by chaining systems
        for idx in range(1, len(system_ids)):
            a = system_ids[idx - 1]
            b = system_ids[idx]
            self._connect_systems(a, b)

        # Add extra random connections
        for sys_id in system_ids:
            connections = self.systems[sys_id].gate_connections
            target_count = rng.randint(2, max_connections)
            while len(connections) < target_count:
                candidate = rng.choice(system_ids)
                if candidate == sys_id:
                    continue
                if candidate in connections:
                    continue
                self._connect_systems(sys_id, candidate)

    def _connect_systems(self, a_id: str, b_id: str) -> None:
        if a_id not in self.systems or b_id not in self.systems:
            return
        if b_id not in self.systems[a_id].gate_connections:
            self.systems[a_id].gate_connections.append(b_id)
        if a_id not in self.systems[b_id].gate_connections:
            self.systems[b_id].gate_connections.append(a_id)

    def get_neighbors(self, system_id: str) -> list:
        system = self.systems.get(system_id)
        if not system:
            return []
        return [
            self.systems[sid]
            for sid in system.gate_connections
            if sid in self.systems
        ]

    def get_active_neighbors(self, system_id: str) -> list:
        """Get neighbors reachable through active gates only."""
        system = self.systems.get(system_id)
        if not system:
            return []
        neighbors = []
        for sid in system.gate_connections:
            neighbor = self.systems.get(sid)
            if not neighbor:
                continue
            if not self.is_gate_operational(system.id):
                continue
            if not self.is_gate_operational(neighbor.id):
                continue
            if system.gate_active and neighbor.gate_active:
                neighbors.append(neighbor)
        return neighbors

    def get_path(self, from_id: str, to_id: str) -> list:
        """BFS shortest path through active gates. Returns list of system IDs."""
        cache_key = (from_id, to_id)
        if cache_key in self._path_cache:
            return list(self._path_cache[cache_key])

        if from_id == to_id:
            return [from_id]

        if from_id not in self.systems or to_id not in self.systems:
            return []

        visited = {from_id}
        queue = deque([(from_id, [from_id])])

        while queue:
            current, path = queue.popleft()
            for neighbor in self.get_active_neighbors(current):
                if neighbor.id in visited:
                    continue
                new_path = path + [neighbor.id]
                if neighbor.id == to_id:
                    self._path_cache[cache_key] = list(new_path)
                    return new_path
                visited.add(neighbor.id)
                queue.append((neighbor.id, new_path))

        return []  # No path found

    def get_distance(self, from_id: str, to_id: str) -> int:
        """Path length through active gates. Returns -1 if unreachable."""
        path = self.get_path(from_id, to_id)
        if not path:
            return -1
        return len(path) - 1

    def activate_gate(
        self,
        system_id: str,
        resources: "ResourceManager" = None,
        cost_reduction: float = 0.0,
    ) -> bool:
        """Activate a dormant gate. Returns True if successful.

        Args:
            system_id: The system whose gate to activate.
            resources: ResourceManager to deduct costs from.
            cost_reduction: Fractional discount (0.0–1.0) applied to
                activation costs, e.g. from the Gate Resonance Tuning tech.
        """
        system = self.systems.get(system_id)
        if not system or system.gate_active:
            return False

        if resources and system.gate_activation_cost:
            reduction = max(0.0, min(1.0, cost_reduction))
            effective_cost = {
                res: max(0, int(amount * (1.0 - reduction)))
                for res, amount in system.gate_activation_cost.items()
            }
            if not resources.can_afford(effective_cost):
                return False
            for res, amount in effective_cost.items():
                resources.spend(res, amount)

        system.gate_active = True
        self._path_cache.clear()  # Invalidate cache on topology change
        return True

    def get_gate_activation_cost(
        self, system_id: str, cost_reduction: float = 0.0
    ) -> dict:
        """Return the effective activation cost for a dormant gate.

        Returns an empty dict if the gate is already active or the system
        does not exist.
        """
        system = self.systems.get(system_id)
        if not system or system.gate_active:
            return {}
        reduction = max(0.0, min(1.0, cost_reduction))
        return {
            res: max(0, int(amount * (1.0 - reduction)))
            for res, amount in system.gate_activation_cost.items()
        }

    def repair_gate(
        self,
        system_id: str,
        resources: "ResourceManager" = None,
        amount: float = 1.0,
        cost_reduction: float = 0.0,
    ) -> bool:
        """Repair a damaged gate by a fractional amount (0.0-1.0)."""
        system = self.systems.get(system_id)
        if not system:
            return False

        missing = max(0.0, 1.0 - system.gate_status)
        if missing <= 0:
            return False

        repair_amount = max(0.0, min(1.0, float(amount), missing))
        if repair_amount <= 0:
            return False

        if resources and system.gate_repair_cost:
            reduction = max(0.0, min(1.0, cost_reduction))
            effective_cost = {
                res: max(0, int(amount * repair_amount * (1.0 - reduction)))
                for res, amount in system.gate_repair_cost.items()
            }
            if not resources.can_afford(effective_cost):
                return False
            for res, amount in effective_cost.items():
                resources.spend(res, amount)

        system.gate_status = min(1.0, system.gate_status + repair_amount)
        self._path_cache.clear()
        return True

    def get_gate_repair_cost(
        self,
        system_id: str,
        amount: float = 1.0,
        cost_reduction: float = 0.0,
    ) -> dict:
        """Return effective repair cost for a fractional repair amount."""
        system = self.systems.get(system_id)
        if not system:
            return {}
        missing = max(0.0, 1.0 - system.gate_status)
        if missing <= 0:
            return {}
        repair_amount = max(0.0, min(1.0, float(amount), missing))
        if repair_amount <= 0:
            return {}
        reduction = max(0.0, min(1.0, cost_reduction))
        return {
            res: max(0, int(amount * repair_amount * (1.0 - reduction)))
            for res, amount in system.gate_repair_cost.items()
        }

    def get_gate_effective_capacity(self, system_id: str) -> int:
        system = self.systems.get(system_id)
        if not system or not system.gate_active:
            return 0
        capacity = max(0, int(system.gate_capacity))
        status = max(0.0, min(1.0, system.gate_status))
        return max(0, int(capacity * status))

    def is_gate_operational(self, system_id: str) -> bool:
        return self.get_gate_effective_capacity(system_id) > 0

    def get_path_capacity(self, from_id: str, to_id: str) -> int:
        """Return the minimum effective gate capacity along a path."""
        path = self.get_path(from_id, to_id)
        if not path:
            return 0
        capacities = [
            self.get_gate_effective_capacity(system_id)
            for system_id in path
        ]
        if not capacities:
            return 0
        return min(capacities)

    def can_support_throughput(self, from_id: str, to_id: str, amount: int) -> bool:
        return self.get_path_capacity(from_id, to_id) >= amount

    def get_systems_by_tier(self, tier: int) -> list:
        return [s for s in self.systems.values() if s.tier == tier]

    def invalidate_cache(self):
        self._path_cache.clear()

    def to_dict(self) -> dict:
        return {
            "systems": [s.to_dict() for s in self.systems.values()]
        }

    @classmethod
    def from_dict(cls, data: dict) -> "GalaxyMap":
        gmap = cls()
        for sys_data in data.get("systems", []):
            system = StarSystem.from_dict(sys_data)
            gmap.systems[system.id] = system
        return gmap
