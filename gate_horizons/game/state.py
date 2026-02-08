"""Master game state for Gate Horizons."""

from __future__ import annotations

from importlib import resources
from typing import Optional

from .galaxy import GalaxyMap
from .ships import FleetManager
from .resources import ResourceManager, RESOURCE_TYPES
from .colonies import ColonyManager, Colony, FOUNDING_COST, COLONY_UPGRADE_COSTS
from .trade import TradeManager
from .combat import CombatResolver
from .events import EventEngine
from .tech import TechTree
from .turn import TurnProcessor, TurnReport, turn_to_date
from .clock import GameClock
from .production import ProductionManager, ProductionConfig, ExtractionSite
from .logistics import LogisticsManager
from .shipyard import ShipyardManager, OrbitalFacility


CURRENT_SCHEMA_VERSION = 4


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
        # New production + logistics + shipyard subsystems
        self.production = ProductionManager()
        self.logistics = LogisticsManager()
        self.shipyard = ShipyardManager()

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

        # Load production config
        prod_path = _get_data_path("production_config.json")
        state.production.config.load_from_json(prod_path)

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
                level=2,  # Start as a Colony (level 2)
                world_traits=["hub"],
            )
            # Starting infrastructure
            colony.infrastructure["housing"]["level"] = 3
            colony.infrastructure["industry"]["level"] = 2
            colony.infrastructure["defense"]["level"] = 1
            colony.infrastructure["research"]["level"] = 1
            colony.infrastructure["spaceport"]["level"] = 1
            colony.infrastructure["power"]["level"] = 2
            colony.infrastructure["mining"]["level"] = 1
            colony.infrastructure["logistics"]["level"] = 1
            colony.happiness = 75
            colony.stability = 80
            # Starting stockpiles
            colony.stockpiles = {
                "energy": 40, "metals": 30, "exotics": 3,
                "credits": 50, "intel": 5,
            }

            # Starting production: Earth has ore_iron and silicates extraction
            colony.extraction_sites = [
                ExtractionSite(resource_id="ore_iron", base_yield=3, level=1),
                ExtractionSite(resource_id="silicates", base_yield=2, level=1),
            ]
            # Starting production inventory with some alloys for early construction
            colony.production_inventory["ore_iron"] = 10
            colony.production_inventory["metal_alloys"] = 8

            # Starting orbital: Earth has a spaceport
            state.shipyard.facilities["sol"] = [
                OrbitalFacility(facility_type="spaceport", level=1),
            ]

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

    def found_colony(self, system_id: str, planet_id: str, name: str = None) -> tuple:
        """Found a new outpost colony on a world.

        Requires colonisation tech and resource costs.
        Returns (success: bool, message: str).
        """
        # Get researched tech set
        researched = {t.id for t in self.tech.techs.values() if t.researched}

        can_found, reason = self.colonies.can_found_colony(
            system_id, planet_id,
            galaxy=self.galaxy,
            researched_techs=researched,
        )
        if not can_found:
            return False, reason

        # Check and spend resources
        cost = self.colonies.get_founding_cost()
        if not self.resources.can_afford(cost):
            return False, f"Cannot afford founding cost: {cost}"
        self.resources.spend_dict(cost)

        # Get planet info for traits
        system = self.galaxy.systems.get(system_id)
        planet = None
        world_traits = []
        if system:
            for p in system.planets:
                if p.id == planet_id:
                    planet = p
                    world_traits = list(p.traits) if p.traits else []
                    break

        colony_name = name or (planet.name if planet else f"Colony at {system_id}")

        colony = self.colonies.establish_colony(
            system_id=system_id,
            planet_id=planet_id,
            name=colony_name,
            initial_pop=50,  # Outposts start small
            level=0,  # Outpost
            world_traits=world_traits,
        )
        colony.stability = 50  # New outposts are fragile

        # Auto-generate extraction sites based on planet body type
        if planet:
            researched = {t.id for t in self.tech.techs.values() if t.researched}
            available = self.production.determine_extraction_resources(
                planet.type, seed=planet.id, researched_techs=researched,
            )
            for res_info in available[:3]:  # Max 3 starting extraction sites
                colony.extraction_sites.append(
                    ExtractionSite(
                        resource_id=res_info["resource_id"],
                        base_yield=res_info["base_yield"],
                        level=1,
                    )
                )

        self.log.append(f"Founded outpost: {colony_name} at {system_id}")
        return True, f"Outpost {colony_name} established"

    def upgrade_colony(self, system_id: str) -> tuple:
        """Upgrade a colony to the next level.

        Returns (success: bool, message: str).
        """
        colony = self.colonies.colonies.get(system_id)
        if not colony:
            return False, "No colony at this system"

        researched = {t.id for t in self.tech.techs.values() if t.researched}
        if not colony.can_upgrade(researched):
            required = colony.get_upgrade_tech_requirements()
            return False, f"Cannot upgrade: tech requirements not met ({required})"

        cost = colony.get_upgrade_cost()
        if not cost:
            return False, "Colony is at maximum level"

        if not self.resources.can_afford(cost):
            return False, f"Cannot afford upgrade cost: {cost}"

        self.resources.spend_dict(cost)
        old_level = colony.level
        colony.upgrade()
        level_name = colony.get_level_info()["name"]

        self.log.append(f"Upgraded {colony.name} to {level_name} (level {colony.level})")
        return True, f"{colony.name} upgraded to {level_name}"

    def load_ship_cargo_from_colony(self, ship_id: str, manifest: Optional[dict] = None) -> dict:
        """Load ship cargo from local colony resources.

        If manifest is None, loads the most abundant resources first.
        Returns a dict of resources loaded.
        """
        ship = self.fleet.ships.get(ship_id)
        if not ship:
            return {}

        colony = self.colonies.colonies.get(ship.location)
        if not colony:
            return {}

        system_resources = self.resources.per_system_resources.get(ship.location, {})
        if not system_resources:
            return {}

        available = {
            res: min(
                self.resources.global_resources.get(res, 0),
                system_resources.get(res, 0),
            )
            for res in RESOURCE_TYPES
        }

        if manifest:
            resource_order = [res for res in manifest.keys() if res in available]
        else:
            resource_order = sorted(
                available,
                key=lambda res: (-available[res], res),
            )

        loaded = {}
        remaining_capacity = ship.cargo_free
        for res in resource_order:
            if remaining_capacity <= 0:
                break
            desired = manifest.get(res, available[res]) if manifest else available[res]
            if desired <= 0:
                continue
            amount = min(desired, available[res], remaining_capacity)
            spent = self.resources.spend_and_return_actual(res, amount, ship.location)
            if spent <= 0:
                continue
            ship.add_cargo(res, spent)
            loaded[res] = loaded.get(res, 0) + spent
            remaining_capacity -= spent
        return loaded

    def unload_ship_cargo_to_colony(self, ship_id: str) -> dict:
        """Unload ship cargo into local colony resources."""
        ship = self.fleet.ships.get(ship_id)
        if not ship:
            return {}

        colony = self.colonies.colonies.get(ship.location)
        if not colony:
            return {}

        unloaded = {}
        for resource, amount in list(ship.cargo.items()):
            if resource not in RESOURCE_TYPES or amount <= 0:
                continue
            self.resources.add(resource, amount, ship.location)
            ship.remove_cargo(resource, amount)
            unloaded[resource] = amount
        return unloaded

    def build_ship(self, system_id: str, ship_class: str, name: str = None) -> bool:
        """Start constructing a ship at a colony's spaceport."""
        if ship_class in self.production.config.ship_blueprints:
            return self.build_ship_orbital(system_id, ship_class, name)

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

    def build_ship_orbital(
        self,
        system_id: str,
        blueprint_id: str,
        name: str = None,
    ) -> bool:
        """Start building a ship via orbital shipyard (component-based).

        Consumes components from colony production inventory and credits.
        """
        colony = self.colonies.colonies.get(system_id)
        if not colony:
            return False

        blueprint = self.production.config.ship_blueprints.get(blueprint_id)
        if not blueprint:
            return False

        ship_name = name or blueprint.get("name", f"New {blueprint_id}")
        tech_effects = self.tech.get_effects()
        build_time_reduction = int(tech_effects.get("build_time_reduction", 0))

        order = self.shipyard.start_ship_build(
            system_id=system_id,
            blueprint_id=blueprint_id,
            ship_name=ship_name,
            config=self.production.config.to_dict(),
            inventory=colony.production_inventory,
            resources=self.resources,
            build_time_reduction=build_time_reduction,
        )
        return order is not None

    def create_trade_route(
        self,
        source: str,
        dest: str,
        manifest: dict,
        capacity_per_turn: int = None,
        latency_turns: int = 1,
        assigned_ships: list = None,
    ) -> Optional:
        """Create a logistics trade route between two colonies.

        If capacity_per_turn is None, auto-compute from source colony logistics.
        """
        # Compute capacity from colony infrastructure if not specified
        if capacity_per_turn is None:
            source_colony = self.colonies.colonies.get(source)
            if source_colony:
                capacity_per_turn = source_colony.get_logistics_capacity()

                # Apply tech bonuses
                tech_effects = self.tech.get_effects()
                logistics_bonus = tech_effects.get("logistics_capacity_bonus", 0)
                if logistics_bonus > 0:
                    capacity_per_turn = int(capacity_per_turn * (1 + logistics_bonus))
            else:
                capacity_per_turn = 10

        return self.trade.create_route(
            source=source,
            dest=dest,
            capacity_per_turn=capacity_per_turn,
            latency_turns=latency_turns,
            manifest=manifest,
            galaxy=self.galaxy,
            ships=assigned_ships or [],
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
            "production": self.production.to_dict(),
            "logistics": self.logistics.to_dict(),
            "shipyard": self.shipyard.to_dict(),
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

        # Schema v4: production + logistics + shipyard subsystems
        if schema_version >= 4:
            state.production = ProductionManager.from_dict(data.get("production", {}))
            state.logistics = LogisticsManager.from_dict(data.get("logistics", {}))
            state.shipyard = ShipyardManager.from_dict(data.get("shipyard", {}))
        else:
            # Migration: load production config for old saves
            state.production = ProductionManager()
            state.logistics = LogisticsManager()
            state.shipyard = ShipyardManager()
            try:
                prod_path = _get_data_path("production_config.json")
                state.production.config.load_from_json(prod_path)
            except Exception:
                pass  # Config may not exist in test environments

        return state
