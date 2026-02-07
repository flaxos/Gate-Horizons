"""Master game state for Gate Horizons."""

from __future__ import annotations

from importlib import resources
from typing import Optional

from .galaxy import GalaxyMap
from .ships import FleetManager
from .resources import ResourceManager
from .colonies import ColonyManager, Colony
from .trade import TradeManager
from .combat import CombatResolver
from .events import EventEngine
from .tech import TechTree
from .turn import TurnProcessor, TurnReport, turn_to_date
from .clock import GameClock


CURRENT_SCHEMA_VERSION = 2


# Default data paths (relative to gate_horizons package)
def _get_data_path(*parts):
    return resources.files("gate_horizons").joinpath("data", *parts)


class GameState:
    def __init__(self):
        self.galaxy = GalaxyMap()
        self.fleet = FleetManager()
        self.resources = ResourceManager()
        self.colonies = ColonyManager()
        self.trade = TradeManager()
        self.combat = CombatResolver()
        self.events = EventEngine()
        self.tech = TechTree()
        self.turn_processor = TurnProcessor()
        self.game_clock = GameClock()
        self.turn_number: int = self.game_clock.turn_number
        self.game_time: str = "January 2157"
        self.difficulty: str = "normal"
        self.log: list[str] = []

    @classmethod
    def new_game(cls, difficulty: str = "normal") -> "GameState":
        """Initialize a fresh game with starting conditions."""
        state = cls()
        state.difficulty = difficulty

        # Load galaxy
        galaxy_path = _get_data_path("galaxy_templates", "demo_galaxy.json")
        state.galaxy.load_from_json(galaxy_path)

        # Load ship templates
        ships_path = _get_data_path("ships.json")
        state.fleet.load_templates(ships_path)

        # Load tech tree
        tech_path = _get_data_path("tech_tree.json")
        state.tech.load_from_json(tech_path)

        # Load events
        events_path = _get_data_path("events")
        state.events.load_events(events_path)

        # Starting resources
        state.resources.global_resources = {
            "energy": 50,
            "metals": 40,
            "exotics": 5,
            "credits": 100,
            "intel": 10,
        }

        # Starting colony at Sol/Earth
        sol = state.galaxy.systems.get("sol")
        if sol:
            sol.discovered = True
            sol.surveyed = True
            sol.tier = 1

            colony = state.colonies.establish_colony(
                system_id="sol",
                planet_id="earth",
                name="Earth",
                initial_pop=500,
            )
            # Starting infrastructure
            colony.infrastructure["housing"]["level"] = 3
            colony.infrastructure["industry"]["level"] = 2
            colony.infrastructure["defense"]["level"] = 1
            colony.infrastructure["research"]["level"] = 1
            colony.infrastructure["spaceport"]["level"] = 1
            colony.happiness = 75

        # Starting ships
        scout = state.fleet.create_ship("scout", "sol", "ISS Pathfinder")
        corvette = state.fleet.create_ship("corvette", "sol", "ISS Sentinel")
        freighter = state.fleet.create_ship("freighter", "sol", "ISS Hauler")

        # Mark initial fog of war
        state.game_clock = GameClock()
        state.turn_number = state.game_clock.turn_number
        state.game_time = "January 2157"
        state.log.append("Game started — January 2157")

        # Discover neighbors of Sol
        if sol:
            for conn_id in sol.gate_connections:
                neighbor = state.galaxy.systems.get(conn_id)
                if neighbor:
                    neighbor.discovered = True

        return state

    def process_turn(self) -> TurnReport:
        """Process one game turn."""
        return self.turn_processor.process_turn(self)

    def activate_gate(self, system_id: str) -> bool:
        """Activate a dormant gate, applying any tech-based cost reduction."""
        tech_effects = self.tech.get_effects()
        cost_reduction = tech_effects.get("gate_cost_reduction", 0.0)
        return self.galaxy.activate_gate(
            system_id,
            resources=self.resources,
            cost_reduction=cost_reduction,
        )

    def build_ship(self, system_id: str, ship_class: str, name: str = None) -> bool:
        """Start constructing a ship at a colony's spaceport.

        Validates the colony has a spaceport with a free slot, checks and
        deducts build costs, and queues the ship.  Returns True on success.
        """
        colony = self.colonies.colonies.get(system_id)
        if not colony:
            return False

        templates = self.fleet._ship_templates
        if not colony.can_build_ship(ship_class, templates):
            return False

        cost = colony.get_ship_build_cost(ship_class, templates)
        if not self.resources.can_afford(cost):
            return False

        template = templates.get(ship_class, {})
        build_turns = template.get("build_turns", 3)
        tech_effects = self.tech.get_effects()
        build_time_reduction = int(tech_effects.get("build_time_reduction", 0))
        ship_name = name or template.get("name", f"New {ship_class.title()}")

        self.resources.spend_dict(cost)
        return colony.start_ship_build(
            ship_class, ship_name, build_turns, build_time_reduction
        )

    def save(self, filepath: str) -> None:
        """Save game state to JSON file."""
        import json
        with open(filepath, "w") as f:
            json.dump(self.to_dict(), f, indent=2)

    def load(self, filepath: str) -> "GameState":
        """Load game state from JSON file."""
        import json
        with open(filepath, "r") as f:
            data = json.load(f)
        return self.from_dict(data)

    def to_dict(self) -> dict:
        return {
            "schema_version": CURRENT_SCHEMA_VERSION,
            "galaxy": self.galaxy.to_dict(),
            "fleet": self.fleet.to_dict(),
            "resources": self.resources.to_dict(),
            "colonies": self.colonies.to_dict(),
            "trade": self.trade.to_dict(),
            "combat": self.combat.to_dict(),
            "events": self.events.to_dict(),
            "tech": self.tech.to_dict(),
            "game_clock": self.game_clock.to_dict(),
            "turn_number": self.turn_number,
            "game_time": self.game_time,
            "difficulty": self.difficulty,
            "log": list(self.log),
        }

    @classmethod
    def from_dict(cls, data: dict) -> "GameState":
        state = cls()
        schema_version = data.get("schema_version", 0)
        if schema_version < 1:
            data = dict(data)
            data.setdefault("game_time", "January 2157")
            data.setdefault("difficulty", "normal")
            data.setdefault("log", [])
        state.galaxy = GalaxyMap.from_dict(data.get("galaxy", {}))
        state.fleet = FleetManager.from_dict(data.get("fleet", {}))
        state.resources = ResourceManager.from_dict(data.get("resources", {}))
        state.colonies = ColonyManager.from_dict(data.get("colonies", {}))
        state.trade = TradeManager.from_dict(data.get("trade", {}))
        state.combat = CombatResolver.from_dict(data.get("combat", {}))
        state.events = EventEngine.from_dict(
            data.get("events", {}),
            events_directory=_get_data_path("events"),
        )
        state.tech = TechTree.from_dict(data.get("tech", {}))
        if schema_version >= 2 and "game_clock" in data:
            state.game_clock = GameClock.from_dict(data.get("game_clock", {}))
        else:
            turn_number = data.get("turn_number", 0)
            state.game_clock = GameClock(current_tick=turn_number, turn_number=turn_number)
        state.turn_number = state.game_clock.turn_number
        state.game_time = data.get("game_time", "January 2157")
        state.difficulty = data.get("difficulty", "normal")
        state.log = list(data.get("log", []))
        return state
