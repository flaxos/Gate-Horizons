"""Master game state for Gate Horizons."""

from __future__ import annotations

from importlib import resources
import hashlib
import random
import json
from typing import Optional
from uuid import uuid4
from pathlib import Path

from .galaxy import GalaxyMap
from .ships import FleetManager
from .resources import ResourceManager, RESOURCE_TYPES
from .colonies import ColonyManager, Colony, FOUNDING_COST, COLONY_UPGRADE_COSTS
from .trade import TradeManager, TradeRoute
from .combat import CombatResolver, EncounterData
from .diplomacy import DiplomacyManager
from .events import EventEngine
from .tech import TechTree
from .turn import TurnProcessor, TurnReport, turn_to_date
from .clock import GameClock
from .production import ProductionManager, ProductionConfig, ExtractionSite, Factory
from .logistics import CargoRule, LogisticsManager, Waypoint
from .missions import MissionManager
from .shipyard import ShipyardManager, OrbitalFacility


CURRENT_SCHEMA_VERSION = 10


# Default data paths (relative to gate_horizons package)
def _get_data_path(*parts):
    return resources.files("gate_horizons").joinpath("data", *parts)


def _coerce_rng_state(value):
    if isinstance(value, list):
        return tuple(_coerce_rng_state(item) for item in value)
    return value


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
        self.missions = MissionManager()
        self.diplomacy = DiplomacyManager()
        self.pending_ship_actions: list[dict] = []
        self.pending_ship_orders: list[dict] = []
        self.encounter_resolution_mode: str = "auto"
        self.pending_encounters: list[dict] = []
        self.rng_seed: int = 0
        self.rng = random.Random(self.rng_seed)

    def rng_for_context(self, context: str) -> random.Random:
        seed_source = f"{self.rng_seed}:{context}"
        seed = int(hashlib.sha256(seed_source.encode("utf-8")).hexdigest()[:8], 16)
        return random.Random(seed)

    @classmethod
    def new_game(
        cls,
        difficulty: str = "normal",
        use_procedural_galaxy: bool = False,
        galaxy_seed: int | None = None,
        system_count: int = 12,
    ) -> "GameState":
        """Initialize a fresh game with starting conditions."""
        state = cls()
        state.difficulty = difficulty

        # Initialize deterministic RNG seed for turn-level randomness.
        state.rng_seed = int(galaxy_seed or 0)
        state.rng = random.Random(state.rng_seed)

        # Load galaxy
        if use_procedural_galaxy:
            state.galaxy.generate_procedural(
                seed=galaxy_seed,
                system_count=system_count,
            )
        else:
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

        # Starting colony at Sol/Earth (or procedural fallback)
        sol = state.galaxy.systems.get("sol")
        starting_system_id = "sol"
        colony = None
        if sol:
            sol.discovered = True
            sol.surveyed = True
            sol.tier = 1

            colony = state.colonies.establish_colony(
                system_id="sol",
                planet_id="sol_earth",
                name="Earth",
                initial_pop=500,
                level=2,  # Start as a Colony (level 2)
                world_traits=["hub"],
            )
        else:
            starting_system = next(iter(state.galaxy.systems.values()), None)
            if starting_system:
                starting_system_id = starting_system.id
                starting_system.discovered = True
                starting_system.surveyed = True
                starting_system.tier = max(1, starting_system.tier)
                colonizable = None
                for planet in starting_system.planets:
                    if planet.colonizable:
                        colonizable = planet
                        break
                if not colonizable and starting_system.planets:
                    colonizable = starting_system.planets[0]
                    colonizable.colonizable = True
                if colonizable:
                    colony = state.colonies.establish_colony(
                        system_id=starting_system.id,
                        planet_id=colonizable.id,
                        name=colonizable.name,
                        initial_pop=500,
                        level=2,
                        world_traits=list(colonizable.traits or ["frontier"]),
                    )
        if colony:
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
            state.shipyard.facilities[starting_system_id] = [
                OrbitalFacility(facility_type="spaceport", level=1),
            ]

        # Starting ships
        scout = state.fleet.create_ship("scout", starting_system_id, "ISS Pathfinder")
        corvette = state.fleet.create_ship("corvette", starting_system_id, "ISS Sentinel")
        freighter = state.fleet.create_ship("freighter", starting_system_id, "ISS Hauler")

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

        state.encounter_resolution_mode = "tactical"

        return state

    def process_turn(self) -> TurnReport:
        """Process one game turn."""
        return self.turn_processor.process_turn(self)

    def set_encounter_resolution_mode(self, mode: str) -> tuple[bool, str]:
        """Set encounter resolution mode (auto/manual/tactical)."""
        normalized = (mode or "").strip().lower()
        if normalized not in {"auto", "manual", "tactical"}:
            return False, f"Unsupported encounter resolution mode: {mode}"
        self.encounter_resolution_mode = normalized
        return True, f"Encounter resolution set to {normalized}"

    def resolve_encounter(self, attacker_ships: list, encounter, system, report) -> None:
        """Resolve an encounter using the configured resolution mode."""
        encounter_id = f"enc-{uuid4().hex[:8]}"
        encounter_spec = self.combat.create_encounter_spec(
            attacker_ships=attacker_ships,
            defender=encounter,
            system=system,
            encounter_id=encounter_id,
        )
        branch_options = self._get_encounter_branches(encounter)
        pending_entry = {
            "encounter_id": encounter_id,
            "spec": encounter_spec.to_dict(),
            "attacker_ship_ids": [ship.id for ship in attacker_ships],
            "defender": encounter.to_dict(),
            "system_id": getattr(system, "id", ""),
            "branch_options": branch_options,
        }
        self.pending_encounters.append(pending_entry)
        self.log.append(f"Encounter {encounter_id} awaiting resolution")
        report.combat_encounters.append(
            {
                "encounter_id": encounter_id,
                "status": "pending_resolution",
                "narrative": "Encounter pending resolution.",
                "encounter_spec": encounter_spec.to_dict(),
                "branch_options": branch_options,
            }
        )

    def submit_encounter_result(self, result_spec: dict) -> tuple[bool, str]:
        """Apply a ResultSpec for a pending manual encounter."""
        valid, message = self.combat.validate_result_spec(result_spec)
        if not valid:
            return False, message
        encounter_id = result_spec.get("encounterId") if isinstance(result_spec, dict) else None
        if not encounter_id:
            return False, "ResultSpec missing encounterId"
        pending_index = next(
            (
                index
                for index, entry in enumerate(self.pending_encounters)
                if entry.get("encounter_id") == encounter_id
            ),
            None,
        )
        if pending_index is None:
            return False, f"No pending encounter with id {encounter_id}"
        pending = self.pending_encounters.pop(pending_index)
        attacker_ship_ids = pending.get("attacker_ship_ids", [])
        attacker_ships = [
            self.fleet.ships[ship_id]
            for ship_id in attacker_ship_ids
            if ship_id in self.fleet.ships
        ]
        defender = EncounterData.from_dict(pending.get("defender", {}))
        combat_result = self.combat.result_from_spec(attacker_ships, defender, result_spec)
        combat_result.encounter_id = pending.get("encounter_id", "")
        combat_result.encounter_contract = dict(pending.get("spec", {}) or {})
        self._apply_manual_combat_result(combat_result, attacker_ships)
        system_id = pending.get("system_id")
        if system_id:
            self._apply_gate_damage(system_id, defender, combat_result)
            self._apply_encounter_outcome_effects(system_id, result_spec)
        self._apply_relation_changes(result_spec)
        self.log.append(f"Encounter {encounter_id} resolved manually")
        return True, "Encounter result applied"

    def resolve_diplomacy_action(self, encounter_id: str, action: str) -> tuple[bool, str]:
        """Resolve a pending encounter through diplomacy."""
        pending_index = next(
            (
                index
                for index, entry in enumerate(self.pending_encounters)
                if entry.get("encounter_id") == encounter_id
            ),
            None,
        )
        if pending_index is None:
            return False, f"No pending encounter with id {encounter_id}"
        pending = self.pending_encounters[pending_index]
        defender = pending.get("defender", {})
        faction_id = defender.get("faction_id") or defender.get("type", "unknown")
        outcome = self.diplomacy.resolve_action(faction_id, action)
        result_spec = {
            "contractVersion": "1.0",
            "encounterId": encounter_id,
            "outcome": "success" if outcome.relation_delta >= 0 else "failure",
            "loot": {"resources": dict(outcome.resource_delta)},
            "assetStatus": {},
            "objectiveResults": {},
            "casualties": {},
            "notes": outcome.summary,
            "missionTime": "",
            "relations": {faction_id: outcome.relation_delta},
        }
        return self.submit_encounter_result(result_spec)

    def resolve_evasion(self, encounter_id: str) -> tuple[bool, str]:
        """Resolve a pending encounter through evasion."""
        pending_index = next(
            (
                index
                for index, entry in enumerate(self.pending_encounters)
                if entry.get("encounter_id") == encounter_id
            ),
            None,
        )
        if pending_index is None:
            return False, f"No pending encounter with id {encounter_id}"
        pending = self.pending_encounters[pending_index]
        attacker_ship_ids = pending.get("attacker_ship_ids", [])
        ships = [self.fleet.ships[ship_id] for ship_id in attacker_ship_ids if ship_id in self.fleet.ships]
        defender = EncounterData.from_dict(pending.get("defender", {}))
        avg_speed = sum(ship.stats.speed for ship in ships) / max(1, len(ships))
        seed = int(hashlib.sha256(encounter_id.encode("utf-8")).hexdigest()[:8], 16)
        rng = random.Random(seed)
        flee_bonus = avg_speed * 0.1
        roll = rng.random()
        success = roll > defender.flee_difficulty - flee_bonus
        status = {}
        if not success and ships:
            status[ships[0].id] = "damaged"
        result_spec = {
            "contractVersion": "1.0",
            "encounterId": encounter_id,
            "outcome": "retreat" if success else "failure",
            "loot": {"resources": {}},
            "assetStatus": status,
            "objectiveResults": {},
            "casualties": {},
            "notes": "Evasion successful." if success else "Evasion failed; ships took damage.",
            "missionTime": "",
        }
        return self.submit_encounter_result(result_spec)

    def _get_encounter_branches(self, encounter: EncounterData) -> list[str]:
        branches = ["tactical", "evasion"]
        if hasattr(self, "diplomacy") and encounter.faction_id in self.diplomacy.relations:
            branches.append("diplomacy")
        return branches

    def _apply_manual_combat_result(self, combat_result, attacker_ships: list) -> None:
        self._apply_resource_delta(combat_result.loot)
        if combat_result.intel_gained:
            self.resources.add("intel", combat_result.intel_gained)
        for ship in attacker_ships:
            damage = combat_result.attacker_damage.get(ship.id)
            if damage:
                ship.hull -= damage
                if ship.hull <= 0:
                    ship.hull = 0
                    if ship.id not in combat_result.ships_destroyed:
                        combat_result.ships_destroyed.append(ship.id)
        for destroyed_id in combat_result.ships_destroyed:
            self.fleet.destroy_ship(destroyed_id)

    def _apply_resource_delta(self, delta: dict) -> None:
        for resource, amount in (delta or {}).items():
            if amount == 0:
                continue
            if amount > 0:
                self.resources.add(resource, amount)
            else:
                self.resources.spend(resource, abs(amount))

    def _apply_encounter_outcome_effects(self, system_id: str, result_spec: dict) -> None:
        outcome = ""
        if isinstance(result_spec, dict):
            outcome = result_spec.get("outcome", "") or ""
        outcome = outcome.lower()
        stability_delta = {
            "success": 2,
            "victory": 2,
            "partial_success": 1,
            "partial": 1,
            "failure": -2,
            "defeat": -3,
            "loss": -3,
        }.get(outcome, 0)
        if stability_delta == 0:
            return
        colony = self.colonies.colonies.get(system_id) if hasattr(self, "colonies") else None
        if not colony:
            return
        colony.stability = max(0, min(100, colony.stability + stability_delta))
        self.log.append(
            f"{colony.name} stability {'+' if stability_delta > 0 else ''}{stability_delta} from encounter"
        )

    def _apply_relation_changes(self, result_spec: dict) -> None:
        if not hasattr(self, "diplomacy"):
            return
        if not isinstance(result_spec, dict):
            return
        relations = result_spec.get("relations") or {}
        if not isinstance(relations, dict):
            return
        for faction_id, delta in relations.items():
            if faction_id:
                self.diplomacy.adjust_score(faction_id, int(delta))

    def export_encounter_spec(
        self,
        system_id: str,
        encounter_type: str = "pirates",
        encounter_id: Optional[str] = None,
        exports_dir: str = "exports/encounters",
    ) -> tuple[bool, str]:
        system = self.galaxy.systems.get(system_id)
        if not system:
            return False, f"System {system_id} not found"
        defender = self._build_placeholder_encounter(encounter_type)
        if not defender:
            return False, f"Unsupported encounter type: {encounter_type}"

        attacker_ships = self.fleet.get_ships_at(system_id)
        if not attacker_ships:
            attacker_ships = list(self.fleet.ships.values())[:1]

        encounter_id = encounter_id or f"enc-{uuid4().hex[:8]}"
        encounter_spec = self.combat.create_encounter_spec(
            attacker_ships=attacker_ships,
            defender=defender,
            system=system,
            encounter_id=encounter_id,
            intent=f"Resolve {defender.type} encounter",
        )

        export_path = Path(exports_dir)
        export_path.mkdir(parents=True, exist_ok=True)
        filepath = export_path / "EncounterSpec.json"
        payload = encounter_spec.to_dict()
        valid, message = self.combat.validate_encounter_spec(payload)
        if not valid:
            return False, message
        pending_entry = {
            "encounter_id": encounter_id,
            "spec": payload,
            "attacker_ship_ids": [ship.id for ship in attacker_ships],
            "defender": defender.to_dict(),
            "system_id": system_id,
            "branch_options": self._get_encounter_branches(defender),
        }
        self.pending_encounters.append(pending_entry)
        filepath.write_text(json.dumps(payload, indent=2), encoding="utf-8")
        self.log.append(f"EncounterSpec exported to {filepath}")
        return True, str(filepath)

    def import_result_spec(
        self,
        imports_dir: str = "imports/results",
        filename: str = "ResultSpec.json",
    ) -> tuple[bool, str]:
        path = Path(imports_dir) / filename
        if not path.exists():
            return False, f"ResultSpec not found at {path}"
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            return False, f"ResultSpec invalid JSON at {path}"
        return self.submit_encounter_result(data)

    @staticmethod
    def _build_placeholder_encounter(encounter_type: str) -> Optional[EncounterData]:
        encounter_type = (encounter_type or "").lower()
        if encounter_type == "pirates":
            return EncounterData(
                type="pirates",
                strength=12,
                description="Pirate raiders ambush the convoy.",
                loot_table={"credits": [10, 30], "metals": [5, 15]},
                flee_difficulty=0.3,
                faction_id="pirates",
            )
        if encounter_type == "anomaly":
            return EncounterData(
                type="hazard",
                strength=8,
                description="Spatial anomaly destabilizes ship systems.",
                loot_table={"intel": [2, 6]},
                flee_difficulty=0.2,
                faction_id="anomaly",
            )
        if encounter_type == "rogue_ai":
            return EncounterData(
                type="rogue_ai",
                strength=15,
                description="A rogue AI drone squadron blocks the jump.",
                loot_table={"metals": [6, 12], "intel": [1, 4]},
                flee_difficulty=0.35,
                faction_id="rogue_ai",
            )
        return None

    def _apply_gate_damage(self, system_id: str, encounter, combat_result, report=None) -> None:
        system = self.galaxy.systems.get(system_id)
        if not system or not encounter:
            return

        strength = max(0, int(getattr(encounter, "strength", 0) or 0))
        if strength <= 0:
            return

        base_damage = min(0.25, 0.01 + strength * 0.002)
        if combat_result.victory:
            damage = base_damage * 0.5
        elif combat_result.fled:
            damage = base_damage * 0.75
        else:
            damage = base_damage

        if damage <= 0:
            return

        before = system.gate_status
        system.gate_status = max(0.0, system.gate_status - damage)
        self.galaxy.invalidate_cache()
        impact = {
            "system_id": system_id,
            "gate_status_before": round(before, 3),
            "gate_status_after": round(system.gate_status, 3),
            "damage": round(damage, 3),
        }
        combat_result.gate_impact = impact
        if report is not None:
            report.warnings.append(
                f"Gate in {system.name} suffered {impact['damage']:.2f} damage"
            )
        self.log.append(
            f"Gate in {system.name} damaged ({impact['damage']:.2f}); status {impact['gate_status_after']:.2f}"
        )

    def execute_ship_action(
        self,
        ship_id: str,
        action_name: str,
        params: Optional[dict] = None,
    ) -> tuple[bool, str]:
        """Dispatch a ship action and store its outcome for the next turn report."""
        ship = self.fleet.ships.get(ship_id)
        if not ship:
            return False, "Ship not found"

        if ship.path:
            return False, f"{ship.name} is currently in transit"

        success, message, report_entry = self._dispatch_ship_action(
            ship,
            action_name,
            params or {},
        )
        if success and report_entry:
            self.pending_ship_actions.append(report_entry)
            self.log.append(report_entry.get("summary", message))
        return success, message

    def issue_ship_order(
        self,
        ship_id: str,
        action_name: str,
        params: Optional[dict] = None,
    ) -> tuple[bool, str, Optional[dict]]:
        """Queue a ship order for execution during the turn resolution."""
        ship = self.fleet.ships.get(ship_id)
        if not ship:
            return False, "Ship not found", None

        if ship.path:
            return False, f"{ship.name} is currently in transit", None

        handler = self._get_ship_action_handler(action_name)
        if not handler:
            return False, f"Unsupported action: {action_name}", None

        order = {
            "order_id": f"ord-{uuid4().hex[:8]}",
            "ship_id": ship_id,
            "action": action_name.strip(),
            "params": dict(params or {}),
            "status": "queued",
            "submitted_turn": self.turn_number,
        }
        self.pending_ship_orders.append(order)
        self.log.append(f"Order queued: {ship.name} -> {order['action']}")
        return True, "Order queued", order

    def process_ship_orders(self, report: TurnReport) -> None:
        """Execute queued ship orders with validation and resolution steps."""
        if not self.pending_ship_orders:
            return

        remaining_orders = []
        for order in list(self.pending_ship_orders):
            order_id = order.get("order_id", "unknown")
            ship_id = order.get("ship_id")
            ship = self.fleet.ships.get(ship_id)
            if not ship:
                order["status"] = "failed"
                warning = f"Order {order_id} failed: ship not found"
                report.warnings.append(warning)
                report.ship_orders.append(
                    {
                        "order_id": order_id,
                        "ship_id": ship_id,
                        "ship_name": "Unknown",
                        "action": order.get("action"),
                        "status": order["status"],
                        "result": warning,
                        "submitted_turn": order.get("submitted_turn"),
                        "summary": warning,
                    }
                )
                continue

            if ship.path:
                order["status"] = "delayed"
                remaining_orders.append(order)
                report.ship_orders.append(
                    {
                        "order_id": order_id,
                        "ship_id": ship_id,
                        "ship_name": ship.name,
                        "action": order.get("action"),
                        "status": order["status"],
                        "result": "Ship in transit",
                        "submitted_turn": order.get("submitted_turn"),
                        "summary": f"Order {order_id} delayed: {ship.name} in transit",
                    }
                )
                continue

            handler = self._get_ship_action_handler(order.get("action", ""))
            if not handler:
                order["status"] = "failed"
                warning = f"Order {order_id} failed: unsupported action"
                report.warnings.append(warning)
                report.ship_orders.append(
                    {
                        "order_id": order_id,
                        "ship_id": ship_id,
                        "ship_name": ship.name,
                        "action": order.get("action"),
                        "status": order["status"],
                        "result": warning,
                        "submitted_turn": order.get("submitted_turn"),
                        "summary": warning,
                    }
                )
                continue

            success, message, report_entry = handler(ship, order.get("params", {}) or {})
            order["status"] = "completed" if success else "failed"
            order["result"] = message
            if success and report_entry:
                report_entry["order_id"] = order_id
                self.pending_ship_actions.append(report_entry)
                self.log.append(report_entry.get("summary", message))
            elif not success:
                warning = f"Order {order_id} failed: {message}"
                report.warnings.append(warning)
            report.ship_orders.append(
                {
                    "order_id": order_id,
                    "ship_id": ship_id,
                    "ship_name": ship.name,
                    "action": order.get("action"),
                    "status": order["status"],
                    "result": order.get("result"),
                    "submitted_turn": order.get("submitted_turn"),
                    "summary": message if not success else report_entry.get("summary", message),
                }
            )

        self.pending_ship_orders = remaining_orders

    def _get_ship_action_handler(self, action_name: str):
        normalized = (action_name or "").strip().lower()
        return self._ship_action_handlers().get(normalized)

    def _dispatch_ship_action(
        self,
        ship,
        action_name: str,
        params: dict,
    ) -> tuple[bool, str, dict]:
        handler = self._get_ship_action_handler(action_name)
        if not handler:
            return False, f"Unsupported action: {action_name}", {}
        return handler(ship, params)

    def _ship_action_handlers(self) -> dict:
        return {
            "scan system": self._handle_scan_system,
            "deploy probe": self._handle_deploy_probe,
            "patrol": self._handle_patrol,
            "escort": self._handle_escort,
            "blockade": self._handle_blockade,
            "investigate anomaly": self._handle_investigate_anomaly,
            "repair": self._handle_repair,
            "refuel": self._handle_refuel,
        }

    def _handle_scan_system(self, ship, params: dict) -> tuple[bool, str, dict]:
        system = self.galaxy.systems.get(ship.location)
        if not system:
            return False, "System not found", {}

        discoveries = []
        if not system.discovered:
            system.discovered = True
            discoveries.append(f"Discovered {system.name}")

        if system.surveyed:
            return False, f"{system.name} has already been surveyed", {}

        system.surveyed = True
        discoveries.append(f"Surveyed {system.name}")
        return True, f"Survey completed in {system.name}", {
            "ship_id": ship.id,
            "ship_name": ship.name,
            "action": "Scan System",
            "system_id": system.id,
            "summary": f"{ship.name} surveyed {system.name}",
            "discoveries": discoveries,
        }

    def _handle_deploy_probe(self, ship, params: dict) -> tuple[bool, str, dict]:
        system = self.galaxy.systems.get(ship.location)
        if not system:
            return False, "System not found", {}

        cost = {"credits": int(params.get("credits", 5))}
        if not self.resources.can_afford(cost):
            return False, f"Cannot afford probe deployment cost: {cost}", {}

        self.resources.spend_dict(cost)

        range_bonus = int(params.get("range_bonus", 1))
        probe_range = max(1, ship.stats.sensor_range + range_bonus)
        newly_found = self._reveal_systems_in_range(system.id, probe_range)
        discoveries = [f"Detected {name}" for name in newly_found]
        summary = f"{ship.name} deployed a probe from {system.name}"
        if newly_found:
            summary += f" (revealed {len(newly_found)} system(s))"

        return True, "Probe deployed", {
            "ship_id": ship.id,
            "ship_name": ship.name,
            "action": "Deploy Probe",
            "system_id": system.id,
            "summary": summary,
            "discoveries": discoveries,
            "resources_spent": cost,
        }

    def _handle_patrol(self, ship, params: dict) -> tuple[bool, str, dict]:
        ship.mission = "patrol"
        return True, "Patrol initiated", {
            "ship_id": ship.id,
            "ship_name": ship.name,
            "action": "Patrol",
            "system_id": ship.location,
            "summary": f"{ship.name} began patrol duty in {ship.location}",
        }

    def _handle_escort(self, ship, params: dict) -> tuple[bool, str, dict]:
        target_id = params.get("target_ship_id")
        if not target_id:
            return False, "Escort requires target_ship_id", {}

        target_ship = self.fleet.ships.get(target_id)
        if not target_ship:
            return False, "Escort target not found", {}

        ship.mission = "escort"
        ship.mission_target = target_id
        return True, f"Escorting {target_ship.name}", {
            "ship_id": ship.id,
            "ship_name": ship.name,
            "action": "Escort",
            "system_id": ship.location,
            "summary": f"{ship.name} is escorting {target_ship.name}",
        }

    def _handle_blockade(self, ship, params: dict) -> tuple[bool, str, dict]:
        ship.mission = "blockade"
        return True, "Blockade established", {
            "ship_id": ship.id,
            "ship_name": ship.name,
            "action": "Blockade",
            "system_id": ship.location,
            "summary": f"{ship.name} is blockading {ship.location}",
        }

    def _handle_investigate_anomaly(self, ship, params: dict) -> tuple[bool, str, dict]:
        event = self.investigate_anomaly(ship.location)
        if not event:
            return False, "No anomalies available to investigate", {}

        summary = f"{ship.name} investigated an anomaly in {ship.location}"
        if getattr(event, "title", ""):
            summary = f"{summary} ({event.title})"
        return True, "Anomaly investigated", {
            "ship_id": ship.id,
            "ship_name": ship.name,
            "action": "Investigate Anomaly",
            "system_id": ship.location,
            "summary": summary,
            "anomaly_investigated": True,
            "event_triggered": getattr(event, "id", ""),
        }

    def _handle_repair(self, ship, params: dict) -> tuple[bool, str, dict]:
        colony = self.colonies.colonies.get(ship.location)
        if not colony:
            return False, "No colony available for repairs", {}

        has_spaceport = colony.infrastructure.get("spaceport", {}).get("level", 0) > 0
        if not has_spaceport:
            return False, "No spaceport available for repairs", {}

        missing = ship.stats.max_hull - ship.hull
        if missing <= 0:
            return False, "Hull is already fully repaired", {}

        repair_amount = min(int(params.get("amount", missing)), missing)
        repair_cost = {"credits": repair_amount * 2}
        if not self.resources.can_afford(repair_cost):
            return False, f"Cannot afford repair cost: {repair_cost}", {}

        self.resources.spend_dict(repair_cost)
        ship.hull = min(ship.stats.max_hull, ship.hull + repair_amount)
        return True, "Repairs completed", {
            "ship_id": ship.id,
            "ship_name": ship.name,
            "action": "Repair",
            "system_id": ship.location,
            "summary": f"{ship.name} repaired {repair_amount} hull at {colony.name}",
            "resources_spent": repair_cost,
        }

    def _handle_refuel(self, ship, params: dict) -> tuple[bool, str, dict]:
        colony = self.colonies.colonies.get(ship.location)
        if not colony:
            return False, "No colony available for refueling", {}

        has_spaceport = colony.infrastructure.get("spaceport", {}).get("level", 0) > 0
        if not has_spaceport:
            return False, "No spaceport available for refueling", {}

        missing = ship.stats.fuel_capacity - ship.fuel
        if missing <= 0:
            return False, "Fuel tanks are already full", {}

        refuel_amount = min(int(params.get("amount", missing)), missing)
        refuel_cost = {"energy": refuel_amount}
        if not self.resources.can_afford(refuel_cost):
            return False, f"Cannot afford refuel cost: {refuel_cost}", {}

        self.resources.spend_dict(refuel_cost)
        ship.fuel = min(ship.stats.fuel_capacity, ship.fuel + refuel_amount)
        return True, "Refueling completed", {
            "ship_id": ship.id,
            "ship_name": ship.name,
            "action": "Refuel",
            "system_id": ship.location,
            "summary": f"{ship.name} refueled {refuel_amount} at {colony.name}",
            "resources_spent": refuel_cost,
        }

    def _reveal_systems_in_range(self, center_id: str, range_remaining: int) -> list[str]:
        if range_remaining <= 0:
            return []

        from collections import deque

        newly_discovered = []
        visited = {center_id}
        queue = deque([(center_id, 0)])

        while queue:
            current_id, depth = queue.popleft()
            if depth >= range_remaining:
                continue

            system = self.galaxy.systems.get(current_id)
            if not system:
                continue

            for neighbor_id in system.gate_connections:
                if neighbor_id in visited:
                    continue
                visited.add(neighbor_id)

                neighbor = self.galaxy.systems.get(neighbor_id)
                if neighbor and not neighbor.discovered:
                    neighbor.discovered = True
                    newly_discovered.append(neighbor.name)

                queue.append((neighbor_id, depth + 1))

        return newly_discovered

    def execute_local_move(self, ship_id: str, target_system_id: str) -> tuple[bool, str]:
        """Move a ship within the same star system without advancing the turn.

        Intra-system moves resolve immediately and do not trigger any
        turn processing (research, production, etc. remain unchanged).

        Returns (success, message).
        """
        ship = self.fleet.ships.get(ship_id)
        if not ship:
            return False, "Ship not found"

        if not self.fleet.is_intra_system_move(ship.location, target_system_id):
            return False, "Not an intra-system move — use normal movement for inter-system travel"

        ok = self.fleet.move_ship_local(ship_id, target_system_id)
        if ok:
            self.log.append(f"{ship.name} repositioned within {ship.location}")
            return True, f"{ship.name} repositioned within system"
        return False, "Local move failed"

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

    def investigate_anomaly(self, system_id: str):
        """Investigate the next uninvestigated anomaly in a system.

        Returns the queued event if one is selected, otherwise None.
        """
        system = self.galaxy.systems.get(system_id)
        if not system or not system.anomalies:
            return None

        target_anomaly = None
        for anomaly in system.anomalies:
            if isinstance(anomaly, dict):
                if anomaly.get("investigated"):
                    continue
                target_anomaly = anomaly
                break
            target_anomaly = anomaly
            break

        if not target_anomaly:
            return None

        if isinstance(target_anomaly, dict):
            target_anomaly["investigated"] = True
            bonus_resources = target_anomaly.get("bonus_resources", {})
            for resource, amount in bonus_resources.items():
                self.resources.add(resource, amount, system_id)

            tags = ["anomaly"]
            if target_anomaly.get("type"):
                tags.append(target_anomaly["type"])
        else:
            tags = ["anomaly"]

        return self.events.select_event_by_tags(tags, self)

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

    def can_afford_production_cost(self, inventory: dict, cost: dict) -> bool:
        for resource, amount in cost.items():
            if resource in ("turns",):
                continue
            if resource in RESOURCE_TYPES:
                if self.resources.global_resources.get(resource, 0) < amount:
                    return False
            elif inventory.get(resource, 0) < amount:
                return False
        return True

    def spend_production_cost(self, inventory: dict, cost: dict) -> bool:
        if not self.can_afford_production_cost(inventory, cost):
            return False
        for resource, amount in cost.items():
            if resource in ("turns",):
                continue
            if resource in RESOURCE_TYPES:
                self.resources.spend(resource, amount)
            else:
                inventory[resource] = max(0, inventory.get(resource, 0) - amount)
        return True

    def build_factory(self, system_id: str) -> tuple:
        """Start building a factory at a colony.

        Returns (success: bool, message: str).
        """
        colony = self.colonies.colonies.get(system_id)
        if not colony:
            return False, "No colony at this system"

        max_by_level = self.production.config.factory_balance.get(
            "max_factories_per_colony_level", {}
        )
        max_factories = int(max_by_level.get(str(colony.level), 0))
        if len(colony.factories) >= max_factories:
            return False, "Factory limit reached for this colony level"

        cost = self.production.config.factory_balance.get("factory_build_cost", {})
        if not self.spend_production_cost(colony.production_inventory, cost):
            return False, f"Cannot afford factory build cost: {cost}"

        build_turns = self.production.config.factory_balance.get("factory_build_turns", 3)
        colony.factories.append(
            Factory(
                building=True,
                build_turns_remaining=build_turns,
            )
        )
        self.log.append(f"Factory construction started at {colony.name}")
        return True, "Factory construction started"

    def build_extraction_site(self, system_id: str, resource_id: str) -> tuple:
        """Start building an extraction site for a specific resource.

        Returns (success: bool, message: str).
        """
        colony = self.colonies.colonies.get(system_id)
        if not colony:
            return False, "No colony at this system"

        max_sites = self.production.config.extraction_balance.get(
            "max_extraction_sites_per_colony", 0
        )
        if max_sites and len(colony.extraction_sites) >= max_sites:
            return False, "Extraction site limit reached for this colony"

        system = self.galaxy.systems.get(system_id)
        planet = None
        if system:
            for candidate in system.planets:
                if candidate.id == colony.planet_id:
                    planet = candidate
                    break
        if not planet:
            return False, "No planet data available for this colony"

        researched = {t.id for t in self.tech.techs.values() if t.researched}
        available = self.production.determine_extraction_resources(
            planet.type,
            seed=planet.id,
            researched_techs=researched,
        )
        resource_info = next(
            (res for res in available if res["resource_id"] == resource_id),
            None,
        )
        if not resource_info:
            return False, "Resource not available for extraction at this world"

        cost = self.production.config.extraction_balance.get(
            "extraction_site_build_cost", {}
        )
        if not self.spend_production_cost(colony.production_inventory, cost):
            return False, f"Cannot afford extraction build cost: {cost}"

        build_turns = self.production.config.extraction_balance.get(
            "extraction_site_build_turns", 2
        )
        colony.extraction_sites.append(
            ExtractionSite(
                resource_id=resource_id,
                base_yield=resource_info.get("base_yield", 1),
                level=1,
                building=True,
                turns_remaining=build_turns,
            )
        )
        self.log.append(
            f"Extraction site ({resource_id}) construction started at {colony.name}"
        )
        return True, "Extraction site construction started"

    def create_trade_route(
        self,
        source: str,
        dest: str,
        manifest: dict,
        capacity_per_turn: int = None,
        latency_turns: int = 1,
        assigned_ships: list = None,
        auto_policy: str = "manual",
        auto_allowlist: list = None,
        auto_max_per_resource: dict = None,
    ) -> tuple[Optional[TradeRoute], str]:
        """Create a logistics trade route between two colonies.

        Requires Logistics I (logistics_1) to be researched.
        If capacity_per_turn is None, auto-compute from source colony logistics.

        Returns (route, message).
        """
        tech_effects = self.tech.get_effects()
        trade_routes_unlocked = tech_effects.get("unlock_trade_routes")
        if trade_routes_unlocked is None:
            tech = self.tech.techs.get("logistics_1")
            trade_routes_unlocked = bool(tech and tech.researched)
        if not trade_routes_unlocked:
            return None, "Trade routes require Logistics I research."
        # Compute capacity from colony infrastructure if not specified
        if capacity_per_turn is None:
            source_colony = self.colonies.colonies.get(source)
            if source_colony:
                capacity_per_turn = source_colony.get_logistics_capacity()

                # Apply tech bonuses
                logistics_bonus = tech_effects.get("logistics_capacity_bonus", 0)
                if logistics_bonus > 0:
                    capacity_per_turn = int(capacity_per_turn * (1 + logistics_bonus))
            else:
                capacity_per_turn = 10

        route = self.trade.create_route(
            source=source,
            dest=dest,
            capacity_per_turn=capacity_per_turn,
            latency_turns=latency_turns,
            manifest=manifest,
            auto_policy=auto_policy,
            auto_allowlist=auto_allowlist,
            auto_max_per_resource=auto_max_per_resource,
            galaxy=self.galaxy,
            ships=assigned_ships or [],
        )
        if not route:
            return None, "No valid path between systems."
        return route, "Trade route created."

    def create_freighter_route(
        self,
        source_system_id: str,
        dest_system_id: str,
        ship_id: str,
        resource_id: str,
        amount: int = 0,
        name: str = None,
        min_threshold: int = 0,
        max_threshold: int = 0,
    ) -> tuple:
        """Create a physical freighter route between two systems.

        Returns (success: bool, message: str).
        """
        if source_system_id == dest_system_id:
            return False, "Source and destination must be different"
        if source_system_id not in self.galaxy.systems or dest_system_id not in self.galaxy.systems:
            return False, "Invalid source or destination system"

        ship = self.fleet.ships.get(ship_id)
        if not ship:
            return False, "Assigned ship not found"
        if ship.ship_class != "freighter":
            return False, "Only freighters can run logistics routes"
        if ship.trade_route:
            return False, "Ship already assigned to a trade route"
        if self.logistics.get_route_for_ship(ship_id):
            return False, "Ship already assigned to a freight route"

        allowed_resources = set(self.production.config.resource_definitions.keys())
        allowed_resources.update(RESOURCE_TYPES)
        if resource_id not in allowed_resources:
            return False, "Resource is not supported for freight routes"

        safe_amount = max(0, int(amount))
        safe_min = max(0, int(min_threshold))
        safe_max = max(0, int(max_threshold))

        waypoints = [
            Waypoint(
                system_id=source_system_id,
                cargo_rules=[
                    CargoRule(
                        resource_id=resource_id,
                        action="load",
                        amount=safe_amount,
                        min_threshold=safe_min,
                    )
                ],
            ),
            Waypoint(
                system_id=dest_system_id,
                cargo_rules=[
                    CargoRule(
                        resource_id=resource_id,
                        action="unload",
                        amount=safe_amount,
                        max_threshold=safe_max,
                    )
                ],
            ),
        ]

        route_name = name or f"{source_system_id}->{dest_system_id} ({resource_id})"
        route = self.logistics.create_route(
            name=route_name,
            waypoints=waypoints,
            assigned_ship_id=ship_id,
        )
        ship.mission = "freight"
        return True, f"Freight route '{route.name}' created"

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
            "missions": self.missions.to_dict(),
            "diplomacy": self.diplomacy.to_dict(),
            "pending_ship_actions": list(self.pending_ship_actions),
            "pending_ship_orders": list(self.pending_ship_orders),
            "encounter_resolution_mode": self.encounter_resolution_mode,
            "pending_encounters": list(self.pending_encounters),
            "rng_seed": self.rng_seed,
            "rng_state": self.rng.getstate(),
        }

    @classmethod
    def from_dict(cls, data: dict) -> "GameState":
        state = cls()
        schema_version = int(data.get("schema_version", 0) or 0)
        if schema_version > CURRENT_SCHEMA_VERSION:
            schema_version = CURRENT_SCHEMA_VERSION
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
        log = data.get("log", [])
        state.log = list(log) if isinstance(log, list) else []

        # Schema v4+: production + logistics + shipyard subsystems
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

        pending_actions = data.get("pending_ship_actions", [])
        pending_orders = data.get("pending_ship_orders", [])
        pending_encounters = data.get("pending_encounters", [])
        state.pending_ship_actions = list(pending_actions) if isinstance(pending_actions, list) else []
        state.pending_ship_orders = list(pending_orders) if isinstance(pending_orders, list) else []
        state.encounter_resolution_mode = data.get("encounter_resolution_mode", "auto")
        state.pending_encounters = list(pending_encounters) if isinstance(pending_encounters, list) else []
        rng_seed = int(data.get("rng_seed", 0) or 0)
        rng_state = data.get("rng_state")
        state.rng_seed = rng_seed
        state.rng = random.Random(rng_seed)
        if rng_state is not None:
            try:
                state.rng.setstate(_coerce_rng_state(rng_state))
            except (TypeError, ValueError):
                state.rng = random.Random(rng_seed)
        if schema_version >= 7:
            state.missions = MissionManager.from_dict(data.get("missions", {}))
        else:
            state.missions = MissionManager()
        if schema_version >= 9:
            state.diplomacy = DiplomacyManager.from_dict(data.get("diplomacy", {}))
        else:
            state.diplomacy = DiplomacyManager()

        return state
