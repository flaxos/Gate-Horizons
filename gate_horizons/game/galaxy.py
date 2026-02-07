"""Star map graph system for Gate Horizons."""

import json
from importlib.resources.abc import Traversable
from typing import Union
from collections import deque
from dataclasses import dataclass, field
from typing import Optional


@dataclass
class Planet:
    id: str
    name: str
    type: str  # rocky, gas_giant, ice, volcanic, oceanic, barren, desert, toxic, garden
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
        planets: list = None,
        stationed_ships: list = None,
        colony: dict = None,
        gate_connections: list = None,
        gate_active: bool = True,
        gate_activation_cost: dict = None,
        anomalies: list = None,
    ):
        self.id = id
        self.name = name
        self.x = x
        self.y = y
        self.discovered = discovered
        self.surveyed = surveyed
        self.tier = tier
        self.planets = [
            Planet.from_dict(p) if isinstance(p, dict) else p
            for p in (planets or [])
        ]
        self.stationed_ships = stationed_ships or []
        self.colony = colony
        self.gate_connections = gate_connections or []
        self.gate_active = gate_active
        self.gate_activation_cost = gate_activation_cost or {}
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
            "planets": [p.to_dict() for p in self.planets],
            "stationed_ships": list(self.stationed_ships),
            "colony": self.colony,
            "gate_connections": list(self.gate_connections),
            "gate_active": self.gate_active,
            "gate_activation_cost": dict(self.gate_activation_cost),
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
            "planets", "stationed_ships", "colony", "gate_connections",
            "gate_active", "gate_activation_cost", "anomalies",
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
            if neighbor and system.gate_active and neighbor.gate_active:
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
