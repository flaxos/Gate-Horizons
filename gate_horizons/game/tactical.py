"""Tactical hex combat MVP for Gate Horizons."""

from __future__ import annotations

from dataclasses import dataclass, field
import math
import random
from typing import Dict, Iterable, List, Optional, Tuple


@dataclass(frozen=True)
class TerrainType:
    name: str
    move_cost: int
    cover_bonus: float
    color: Tuple[float, float, float]


TERRAIN_TYPES: Dict[str, TerrainType] = {
    "open": TerrainType(name="open", move_cost=1, cover_bonus=0.0, color=(0.08, 0.12, 0.2)),
    "asteroid": TerrainType(name="asteroid", move_cost=2, cover_bonus=0.2, color=(0.25, 0.25, 0.3)),
    "nebula": TerrainType(name="nebula", move_cost=2, cover_bonus=0.1, color=(0.15, 0.2, 0.3)),
}


@dataclass
class HexCell:
    q: int
    r: int
    terrain: TerrainType


class HexGrid:
    """Axial-coordinate hex grid with deterministic terrain generation."""

    def __init__(self, width: int, height: int, cells: Dict[Tuple[int, int], HexCell]):
        self.width = width
        self.height = height
        self.cells = cells

    @classmethod
    def generate(cls, width: int, height: int, seed: int) -> "HexGrid":
        rng = random.Random(seed)
        cells: Dict[Tuple[int, int], HexCell] = {}
        terrain_keys = ["open", "asteroid", "nebula"]
        for q in range(width):
            for r in range(height):
                roll = rng.random()
                if roll < 0.15:
                    terrain_key = "asteroid"
                elif roll < 0.3:
                    terrain_key = "nebula"
                else:
                    terrain_key = "open"
                terrain = TERRAIN_TYPES[terrain_key]
                cells[(q, r)] = HexCell(q=q, r=r, terrain=terrain)

        # Ensure at least two terrain types are present
        cells[(0, 0)].terrain = TERRAIN_TYPES["open"]
        cells[(min(1, width - 1), min(1, height - 1))].terrain = TERRAIN_TYPES["asteroid"]
        return cls(width=width, height=height, cells=cells)

    def in_bounds(self, coord: Tuple[int, int]) -> bool:
        q, r = coord
        return 0 <= q < self.width and 0 <= r < self.height

    def terrain_at(self, coord: Tuple[int, int]) -> TerrainType:
        return self.cells[coord].terrain

    @staticmethod
    def neighbors(coord: Tuple[int, int]) -> Iterable[Tuple[int, int]]:
        q, r = coord
        directions = [(1, 0), (1, -1), (0, -1), (-1, 0), (-1, 1), (0, 1)]
        for dq, dr in directions:
            yield (q + dq, r + dr)

    @staticmethod
    def distance(a: Tuple[int, int], b: Tuple[int, int]) -> int:
        aq, ar = a
        bq, br = b
        return int((abs(aq - bq) + abs(aq + ar - bq - br) + abs(ar - br)) / 2)


@dataclass
class TacticalUnit:
    unit_id: str
    name: str
    faction: str
    hp: int
    max_hp: int
    move_points: int
    weapon_range: int
    weapon_damage: int
    accuracy: float
    position: Tuple[int, int]
    remaining_move: int = 0
    can_attack: bool = True

    def reset_turn(self) -> None:
        self.remaining_move = self.move_points
        self.can_attack = True

    @property
    def destroyed(self) -> bool:
        return self.hp <= 0


@dataclass
class TacticalOutcome:
    winner: str
    summary: str
    damage: Dict[str, int] = field(default_factory=dict)
    losses: List[str] = field(default_factory=list)
    salvage: Dict[str, int] = field(default_factory=dict)


class TacticalCombat:
    """Turn-based tactical combat with deterministic RNG."""

    def __init__(
        self,
        grid: HexGrid,
        units: List[TacticalUnit],
        rng: Optional[random.Random] = None,
        defender_loot: Optional[dict] = None,
    ):
        self.grid = grid
        self.units = units
        self.rng = rng or random.Random(0)
        self.defender_loot = defender_loot or {}
        self.current_faction = "player"
        self._start_turn()

    def _start_turn(self) -> None:
        for unit in self.units:
            if unit.faction == self.current_faction and not unit.destroyed:
                unit.reset_turn()

    def end_turn(self) -> None:
        self.current_faction = "enemy" if self.current_faction == "player" else "player"
        self._start_turn()

    def units_for_faction(self, faction: str) -> List[TacticalUnit]:
        return [u for u in self.units if u.faction == faction and not u.destroyed]

    def get_unit(self, unit_id: str) -> Optional[TacticalUnit]:
        for unit in self.units:
            if unit.unit_id == unit_id:
                return unit
        return None

    def occupied_positions(self) -> Dict[Tuple[int, int], TacticalUnit]:
        return {
            unit.position: unit
            for unit in self.units
            if not unit.destroyed
        }

    def can_move(self, unit: TacticalUnit, dest: Tuple[int, int]) -> bool:
        if unit.destroyed or unit.faction != self.current_faction:
            return False
        if not self.grid.in_bounds(dest):
            return False
        if dest in self.occupied_positions():
            return False
        distance = self.grid.distance(unit.position, dest)
        if distance != 1:
            return False
        cost = self.grid.terrain_at(dest).move_cost
        return unit.remaining_move >= cost

    def move_unit(self, unit_id: str, dest: Tuple[int, int]) -> bool:
        unit = self.get_unit(unit_id)
        if not unit or not self.can_move(unit, dest):
            return False
        cost = self.grid.terrain_at(dest).move_cost
        unit.position = dest
        unit.remaining_move -= cost
        return True

    def can_attack(self, attacker: TacticalUnit, target: TacticalUnit) -> bool:
        if attacker.destroyed or target.destroyed:
            return False
        if attacker.faction != self.current_faction:
            return False
        if not attacker.can_attack:
            return False
        distance = self.grid.distance(attacker.position, target.position)
        return distance <= attacker.weapon_range

    def attack(self, attacker_id: str, target_id: str) -> Tuple[bool, int]:
        attacker = self.get_unit(attacker_id)
        target = self.get_unit(target_id)
        if not attacker or not target or not self.can_attack(attacker, target):
            return False, 0
        cover = self.grid.terrain_at(target.position).cover_bonus
        hit_chance = max(0.05, min(0.95, attacker.accuracy - cover))
        hit = self.rng.random() <= hit_chance
        damage = 0
        if hit:
            damage = attacker.weapon_damage
            target.hp = max(0, target.hp - damage)
        attacker.can_attack = False
        return hit, damage

    def winner(self) -> Optional[str]:
        player_alive = any(u for u in self.units if u.faction == "player" and not u.destroyed)
        enemy_alive = any(u for u in self.units if u.faction == "enemy" and not u.destroyed)
        if player_alive and enemy_alive:
            return None
        if player_alive:
            return "player"
        if enemy_alive:
            return "enemy"
        return "draw"

    def resolve_ai_turn(self) -> List[str]:
        """Very simple deterministic AI: move towards nearest player, attack if possible."""
        logs: List[str] = []
        enemies = self.units_for_faction("enemy")
        players = self.units_for_faction("player")
        if not enemies or not players:
            return logs

        for enemy in enemies:
            if not players:
                break
            target = min(
                players,
                key=lambda unit: self.grid.distance(enemy.position, unit.position),
            )
            if self.can_attack(enemy, target):
                hit, damage = self.attack(enemy.unit_id, target.unit_id)
                logs.append(
                    f"{enemy.name} fires on {target.name} ({'hit' if hit else 'miss'} for {damage})."
                )
                continue
            neighbor_options = [
                pos for pos in self.grid.neighbors(enemy.position)
                if self.grid.in_bounds(pos) and pos not in self.occupied_positions()
            ]
            if neighbor_options:
                best = min(
                    neighbor_options,
                    key=lambda pos: self.grid.distance(pos, target.position),
                )
                if self.move_unit(enemy.unit_id, best):
                    logs.append(f"{enemy.name} advances.")
        return logs

    def build_outcome(self) -> TacticalOutcome:
        winner = self.winner() or "draw"
        damage: Dict[str, int] = {}
        losses: List[str] = []
        for unit in self.units:
            lost = unit.destroyed
            if lost:
                losses.append(unit.unit_id)
            damage_taken = unit.max_hp - unit.hp
            if damage_taken > 0:
                damage[unit.unit_id] = damage_taken
        salvage: Dict[str, int] = {}
        if winner == "player":
            for resource, amount in (self.defender_loot or {}).items():
                if isinstance(amount, list) and len(amount) == 2:
                    salvage[resource] = self.rng.randint(amount[0], amount[1])
                elif isinstance(amount, (int, float)):
                    salvage[resource] = int(amount)
        summary = f"Tactical engagement resolved. Winner: {winner}."
        return TacticalOutcome(
            winner=winner,
            summary=summary,
            damage=damage,
            losses=losses,
            salvage=salvage,
        )

    @staticmethod
    def outcome_to_result_spec(
        outcome: TacticalOutcome,
        encounter_id: str,
        player_units: Iterable[TacticalUnit],
    ) -> dict:
        status_map: Dict[str, str] = {}
        for unit in player_units:
            if unit.destroyed:
                status_map[unit.unit_id] = "destroyed"
            elif outcome.damage.get(unit.unit_id):
                status_map[unit.unit_id] = "damaged"
            else:
                status_map[unit.unit_id] = "operational"

        result_outcome = "victory" if outcome.winner == "player" else "defeat"
        if outcome.winner == "draw":
            result_outcome = "partial_success"
        return {
            "contractVersion": "1.0",
            "encounterId": encounter_id,
            "outcome": result_outcome,
            "loot": {"resources": dict(outcome.salvage)},
            "assetStatus": status_map,
            "objectiveResults": {},
            "casualties": {},
            "notes": outcome.summary,
            "missionTime": "",
            "tacticalReport": {
                "winner": outcome.winner,
                "damage": dict(outcome.damage),
                "losses": list(outcome.losses),
                "salvage": dict(outcome.salvage),
            },
        }
