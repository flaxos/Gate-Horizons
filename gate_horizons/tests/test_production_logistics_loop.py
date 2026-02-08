"""Tests for the production & logistics game loop.

Covers:
1. Extraction produces resources correctly by body type per tick.
2. Route execution moves cargo and respects capacity.
3. Factory recipe consumes inputs and produces outputs over time.
4. Ship build consumes components and completes only in orbital yard/drydock.
5. Save/load roundtrip preserves inventories, routes, and queues.
6. Full integration: extraction -> factory -> orbital build pipeline.
7. Body type resource availability is data-driven.
"""

import unittest

from gate_horizons.game.state import GameState
from gate_horizons.game.production import (
    ProductionConfig,
    ProductionManager,
    ExtractionSite,
    Factory,
    empty_production_inventory,
    ALL_PRODUCTION_RESOURCES,
)
from gate_horizons.game.logistics import (
    LogisticsManager,
    FreighterRoute,
    Waypoint,
    CargoRule,
)
from gate_horizons.game.shipyard import (
    ShipyardManager,
    OrbitalFacility,
    ShipBuildOrder,
)
from gate_horizons.game.colonies import ColonyManager, Colony
from gate_horizons.game.ships import FleetManager
from gate_horizons.game.resources import ResourceManager
from gate_horizons.game.galaxy import GalaxyMap, StarSystem, Planet
from gate_horizons.game.tech import TechTree, TechNode
from gate_horizons.game.trade import TradeManager
from gate_horizons.game.combat import CombatResolver
from gate_horizons.game.events import EventEngine
from gate_horizons.game.turn import TurnProcessor
from gate_horizons.game.clock import GameClock


def _load_production_config() -> ProductionConfig:
    """Load production config from data file."""
    from importlib import resources as pkg_resources
    config = ProductionConfig()
    path = pkg_resources.files("gate_horizons").joinpath("data", "production_config.json")
    config.load_from_json(path)
    return config


class TestExtractionByBodyType(unittest.TestCase):
    """Test 1: Extraction produces resources correctly by body type per tick."""

    def test_rocky_planet_extraction(self):
        """Rocky planet extraction sites produce ore_iron per tick."""
        config = _load_production_config()
        pm = ProductionManager(config)

        site = ExtractionSite(resource_id="ore_iron", base_yield=4, level=1)
        inventory = empty_production_inventory()

        # Process one tick with mining level 1
        extracted = pm.process_extraction(
            [site], inventory, mining_level=1, tech_mult=1.0,
        )

        self.assertIn("ore_iron", extracted)
        self.assertGreater(extracted["ore_iron"], 0)
        self.assertEqual(inventory["ore_iron"], extracted["ore_iron"])

    def test_gas_giant_extraction(self):
        """Gas giant extraction sites produce gas_h2."""
        config = _load_production_config()
        pm = ProductionManager(config)

        site = ExtractionSite(resource_id="gas_h2", base_yield=6, level=1)
        inventory = empty_production_inventory()

        extracted = pm.process_extraction([site], inventory)
        self.assertIn("gas_h2", extracted)
        self.assertGreater(extracted["gas_h2"], 0)

    def test_mining_level_increases_yield(self):
        """Higher mining infrastructure level increases extraction yield."""
        config = _load_production_config()
        pm = ProductionManager(config)

        site_low = ExtractionSite(resource_id="ore_iron", base_yield=4, level=1)
        inv_low = empty_production_inventory()
        pm.process_extraction([site_low], inv_low, mining_level=0)

        site_high = ExtractionSite(resource_id="ore_iron", base_yield=4, level=1)
        inv_high = empty_production_inventory()
        pm.process_extraction([site_high], inv_high, mining_level=3)

        self.assertGreater(
            inv_high["ore_iron"], inv_low["ore_iron"],
            "Higher mining level should produce more ore",
        )

    def test_building_site_produces_nothing(self):
        """Extraction site under construction produces nothing."""
        config = _load_production_config()
        pm = ProductionManager(config)

        site = ExtractionSite(resource_id="ore_iron", base_yield=4, level=1,
                              building=True, turns_remaining=2)
        inventory = empty_production_inventory()

        extracted = pm.process_extraction([site], inventory)
        self.assertEqual(extracted, {})
        self.assertEqual(inventory["ore_iron"], 0)

    def test_extraction_multi_turn_completes_build(self):
        """Extraction site finishes building after turns_remaining ticks."""
        site = ExtractionSite(
            resource_id="ore_iron", base_yield=4, level=1,
            building=True, turns_remaining=2,
        )
        config = _load_production_config()
        pm = ProductionManager(config)
        inv = empty_production_inventory()

        # Tick 1: still building
        pm.process_extraction([site], inv)
        self.assertTrue(site.building)
        self.assertEqual(inv["ore_iron"], 0)

        # Tick 2: finishes building
        pm.process_extraction([site], inv)
        self.assertFalse(site.building)
        self.assertEqual(inv["ore_iron"], 0)  # Produces nothing on completion tick

        # Tick 3: now produces
        pm.process_extraction([site], inv)
        self.assertGreater(inv["ore_iron"], 0)


class TestRouteExecutionMovesCargoAndRespectsCapacity(unittest.TestCase):
    """Test 2: Route execution moves cargo and respects capacity."""

    def _make_two_system_state(self):
        """Create minimal state with two connected systems, a colony, and a freighter."""
        galaxy = GalaxyMap()
        sys_a = StarSystem(
            id="sys_a", name="System A", x=0.3, y=0.5,
            discovered=True, surveyed=True, tier=1,
            gate_connections=["sys_b"], gate_active=True,
            planets=[Planet(id="p_a", name="Planet A", type="rocky",
                            colonizable=True, resources={})],
        )
        sys_b = StarSystem(
            id="sys_b", name="System B", x=0.7, y=0.5,
            discovered=True, surveyed=True, tier=1,
            gate_connections=["sys_a"], gate_active=True,
            planets=[Planet(id="p_b", name="Planet B", type="rocky",
                            colonizable=True, resources={})],
        )
        galaxy.systems["sys_a"] = sys_a
        galaxy.systems["sys_b"] = sys_b

        fleet = FleetManager()
        from importlib import resources as pkg_resources
        ships_path = pkg_resources.files("gate_horizons").joinpath("data", "ships.json")
        fleet.load_templates(ships_path)
        freighter = fleet.create_ship("freighter", "sys_a", "Test Hauler")

        colonies = ColonyManager()
        col_a = colonies.establish_colony("sys_a", "p_a", "Colony A", 100, 1)
        col_b = colonies.establish_colony("sys_b", "p_b", "Colony B", 50, 0)

        return galaxy, fleet, colonies, freighter

    def test_load_cargo_at_waypoint(self):
        """Freighter loads production resources at waypoint."""
        galaxy, fleet, colonies, freighter = self._make_two_system_state()
        logistics = LogisticsManager()

        # Stock production inventory at sys_a
        colonies.colonies["sys_a"].production_inventory["ore_iron"] = 50

        route = logistics.create_route(
            name="Iron Run",
            waypoints=[
                {"system_id": "sys_a", "cargo_rules": [
                    {"resource_id": "ore_iron", "action": "load", "amount": 20},
                ]},
                {"system_id": "sys_b", "cargo_rules": [
                    {"resource_id": "ore_iron", "action": "unload", "amount": 0},
                ]},
            ],
            assigned_ship_id=freighter.id,
        )

        # Process routes — ship is at sys_a (waypoint 0)
        prod_inv = {
            "sys_a": colonies.colonies["sys_a"].production_inventory,
            "sys_b": colonies.colonies["sys_b"].production_inventory,
        }
        reports = logistics.process_routes(fleet, colonies, galaxy, prod_inv)

        # Ship should have loaded ore_iron
        self.assertEqual(freighter.cargo.get("ore_iron", 0), 20)
        # Source inventory should be reduced
        self.assertEqual(colonies.colonies["sys_a"].production_inventory["ore_iron"], 30)

    def test_cargo_capacity_enforced(self):
        """Cannot load more than ship cargo capacity."""
        galaxy, fleet, colonies, freighter = self._make_two_system_state()
        logistics = LogisticsManager()

        # Stock more than freighter capacity (100)
        colonies.colonies["sys_a"].production_inventory["ore_iron"] = 500

        route = logistics.create_route(
            name="Overload Run",
            waypoints=[
                {"system_id": "sys_a", "cargo_rules": [
                    {"resource_id": "ore_iron", "action": "load", "amount": 0},  # 0 = as much as possible
                ]},
                {"system_id": "sys_b", "cargo_rules": [
                    {"resource_id": "ore_iron", "action": "unload"},
                ]},
            ],
            assigned_ship_id=freighter.id,
        )

        prod_inv = {
            "sys_a": colonies.colonies["sys_a"].production_inventory,
            "sys_b": colonies.colonies["sys_b"].production_inventory,
        }
        logistics.process_routes(fleet, colonies, galaxy, prod_inv)

        # Freighter capacity is 100
        self.assertLessEqual(freighter.cargo_used, freighter.stats.cargo_capacity)


class TestFactoryRecipe(unittest.TestCase):
    """Test 3: Factory recipe consumes inputs and produces outputs over time."""

    def test_metal_alloys_recipe(self):
        """metal_alloys recipe: 3 ore_iron -> 2 metal_alloys in 1 tick."""
        config = _load_production_config()
        factory = Factory(active=True)
        factory.queue_recipe("metal_alloys")

        inventory = empty_production_inventory()
        inventory["ore_iron"] = 10

        # Tick 1: should consume 3 ore_iron and produce 2 metal_alloys
        produced = factory.process_tick(inventory, config)

        self.assertIn("metal_alloys", produced)
        self.assertEqual(produced["metal_alloys"], 2)
        self.assertEqual(inventory["ore_iron"], 7)  # 10 - 3

    def test_electronics_recipe_takes_2_ticks(self):
        """electronics recipe: 2 rare_metals + 2 silicates -> 1 electronics in 2 ticks."""
        config = _load_production_config()
        factory = Factory(active=True)
        factory.queue_recipe("electronics")

        inventory = empty_production_inventory()
        inventory["rare_metals"] = 5
        inventory["silicates"] = 5

        # Tick 1: consumes inputs, starts processing
        produced1 = factory.process_tick(inventory, config, industry_level=1)
        self.assertEqual(produced1, {})
        self.assertEqual(inventory["rare_metals"], 3)  # 5 - 2
        self.assertEqual(inventory["silicates"], 3)  # 5 - 2

        # Tick 2: produces output
        produced2 = factory.process_tick(inventory, config, industry_level=1)
        self.assertIn("electronics", produced2)
        self.assertEqual(produced2["electronics"], 1)

    def test_factory_waits_when_no_inputs(self):
        """Factory does not consume or produce if inputs are insufficient."""
        config = _load_production_config()
        factory = Factory(active=True)
        factory.queue_recipe("metal_alloys")

        inventory = empty_production_inventory()
        inventory["ore_iron"] = 1  # Need 3

        produced = factory.process_tick(inventory, config)
        self.assertEqual(produced, {})
        self.assertEqual(inventory["ore_iron"], 1)  # Unchanged

    def test_recipe_prerequisite_blocks_low_industry(self):
        """Component recipes should respect minimum industry prerequisites."""
        config = _load_production_config()
        factory = Factory(active=True)
        factory.queue_recipe("hull_plating")

        inventory = empty_production_inventory()
        inventory["metal_alloys"] = 10
        inventory["silicates"] = 10

        produced = factory.process_tick(inventory, config, industry_level=0)
        self.assertEqual(produced, {})
        self.assertEqual(inventory["metal_alloys"], 10)

        produced = factory.process_tick(inventory, config, industry_level=1)
        self.assertEqual(produced, {})
        produced = factory.process_tick(inventory, config, industry_level=1)
        self.assertIn("hull_plating", produced)

    def test_factory_queue_processes_multiple_recipes(self):
        """Factory processes recipes from queue sequentially."""
        config = _load_production_config()
        factory = Factory(active=True)
        factory.queue_recipe("metal_alloys", count=2)

        inventory = empty_production_inventory()
        inventory["ore_iron"] = 20

        # First recipe completes in 1 tick
        produced1 = factory.process_tick(inventory, config)
        self.assertEqual(produced1.get("metal_alloys", 0), 2)

        # Second recipe starts and completes
        produced2 = factory.process_tick(inventory, config)
        self.assertEqual(produced2.get("metal_alloys", 0), 2)

        # Queue should be empty now
        self.assertEqual(len(factory.recipe_queue), 0)
        self.assertIsNone(factory.current_recipe)


class TestIndustryCaps(unittest.TestCase):
    """Test 3b: Throughput and storage caps."""

    def test_throughput_caps_factory_count(self):
        config = ProductionConfig()
        config.recipes = {
            "metal_alloys": {"inputs": {"ore_iron": 2}, "outputs": {"metal_alloys": 1}, "time": 1},
        }
        pm = ProductionManager(config)

        factories = [Factory(active=True) for _ in range(2)]
        for factory in factories:
            factory.queue_recipe("metal_alloys")

        inventory = empty_production_inventory()
        inventory["ore_iron"] = 10

        produced = pm.process_factories(factories, inventory, throughput_cap=1)
        self.assertEqual(produced.get("metal_alloys", 0), 1)

    def test_storage_caps_limit_output(self):
        config = ProductionConfig()
        config.resource_definitions = {"ore_iron": {"tier": "raw"}}
        config.production_storage = {
            "base_caps": {"raw": 5},
            "colony_level_mult": 0.0,
            "industry_level_mult": 0.0,
            "min_cap": 0
        }
        pm = ProductionManager(config)

        inventory = empty_production_inventory()
        inventory["ore_iron"] = 4

        mock_colony = type(
            "MockColony",
            (),
            {"level": 0, "infrastructure": {"industry": {"level": 0}}},
        )()
        caps = pm.get_storage_caps(mock_colony)

        extracted = pm.process_extraction(
            [ExtractionSite(resource_id="ore_iron", base_yield=4, level=1)],
            inventory,
            storage_caps=caps,
        )
        self.assertEqual(inventory["ore_iron"], 5)
        self.assertEqual(extracted["ore_iron"], 1)


class TestShipBuildRequiresOrbitalFacility(unittest.TestCase):
    """Test 4: Ship build consumes components and completes only in orbital yard/drydock."""

    def test_drydock_builds_small_freighter(self):
        """Small freighter can be built at a drydock, consumes components."""
        config = _load_production_config()
        config_dict = config.to_dict()

        shipyard = ShipyardManager()
        # Create a drydock at sol
        drydock = OrbitalFacility(facility_type="drydock", level=1)
        shipyard.facilities["sol"] = [drydock]

        # Prepare inventory with required components
        inventory = empty_production_inventory()
        inventory["hull_plating"] = 10
        inventory["drive_assemblies"] = 5
        inventory["avionics"] = 3
        inventory["cargo_frames"] = 10

        resources = ResourceManager()
        resources.global_resources["credits"] = 500

        # Start build
        order = shipyard.start_ship_build(
            "sol", "small_freighter", "ISS Test Freighter",
            config_dict, inventory, resources,
        )
        self.assertIsNotNone(order)
        self.assertEqual(order.blueprint_id, "small_freighter")

        # Components consumed
        self.assertEqual(inventory["hull_plating"], 6)  # 10 - 4
        self.assertEqual(inventory["drive_assemblies"], 4)  # 5 - 1
        self.assertEqual(inventory["avionics"], 2)  # 3 - 1
        self.assertEqual(inventory["cargo_frames"], 6)  # 10 - 4

        # Credits consumed
        self.assertEqual(resources.global_resources["credits"], 440)  # 500 - 60

    def test_spaceport_cannot_build_ships(self):
        """Spaceport alone cannot build ships."""
        config = _load_production_config()
        config_dict = config.to_dict()

        shipyard = ShipyardManager()
        spaceport = OrbitalFacility(facility_type="spaceport", level=1)
        shipyard.facilities["sol"] = [spaceport]

        inventory = empty_production_inventory()
        inventory.update({k: 100 for k in ALL_PRODUCTION_RESOURCES})

        resources = ResourceManager()
        resources.global_resources["credits"] = 1000

        can_build, reason = shipyard.can_build_ship("sol", "small_freighter", config_dict)
        self.assertFalse(can_build)
        self.assertIn("No facility", reason)

    def test_orbital_yard_builds_colony_ship(self):
        """Colony ship can only be built at an orbital yard."""
        config = _load_production_config()
        config_dict = config.to_dict()

        shipyard = ShipyardManager()
        # Need spaceport + drydock prerequisite chain for orbital yard
        yard = OrbitalFacility(facility_type="orbital_yard", level=1)
        shipyard.facilities["sol"] = [yard]

        inventory = empty_production_inventory()
        inventory["hull_plating"] = 50
        inventory["drive_assemblies"] = 20
        inventory["hab_modules"] = 20
        inventory["avionics"] = 10
        inventory["cargo_frames"] = 20

        resources = ResourceManager()
        resources.global_resources["credits"] = 1000

        can_build, reason = shipyard.can_build_ship("sol", "colony_ship", config_dict)
        self.assertTrue(can_build, f"Should be able to build colony ship: {reason}")

        order = shipyard.start_ship_build(
            "sol", "colony_ship", "ISS Ark",
            config_dict, inventory, resources,
        )
        self.assertIsNotNone(order)
        self.assertEqual(order.turns_remaining, 12)

    def test_drydock_rejects_colony_ship(self):
        """Drydock cannot build colony ships."""
        config = _load_production_config()
        config_dict = config.to_dict()

        shipyard = ShipyardManager()
        drydock = OrbitalFacility(facility_type="drydock", level=1)
        shipyard.facilities["sol"] = [drydock]

        can_build, reason = shipyard.can_build_ship("sol", "colony_ship", config_dict)
        self.assertFalse(can_build)
        self.assertIn("No facility", reason)

    def test_build_completes_after_turns(self):
        """Ship build order completes after specified turns."""
        config = _load_production_config()
        config_dict = config.to_dict()

        shipyard = ShipyardManager()
        drydock = OrbitalFacility(facility_type="drydock", level=1)
        shipyard.facilities["sol"] = [drydock]

        inventory = empty_production_inventory()
        inventory["hull_plating"] = 20
        inventory["drive_assemblies"] = 10
        inventory["avionics"] = 5
        inventory["cargo_frames"] = 20

        resources = ResourceManager()
        resources.global_resources["credits"] = 500

        order = shipyard.start_ship_build(
            "sol", "small_freighter", "ISS Builder",
            config_dict, inventory, resources,
        )
        self.assertIsNotNone(order)
        self.assertEqual(order.turns_remaining, 4)

        # Process ticks
        for i in range(3):
            result = shipyard.process_tick(config=config_dict)
            self.assertEqual(len(result["ships_completed"]), 0)

        # Tick 4: completes
        result = shipyard.process_tick(config=config_dict)
        self.assertEqual(len(result["ships_completed"]), 1)
        self.assertEqual(result["ships_completed"][0]["ship_name"], "ISS Builder")

    def test_queue_order_progression(self):
        """Queued builds should complete in order as capacity frees up."""
        config = _load_production_config()
        config_dict = config.to_dict()

        shipyard = ShipyardManager()
        drydock = OrbitalFacility(facility_type="drydock", level=1)
        shipyard.facilities["sol"] = [drydock]

        inventory = empty_production_inventory()
        inventory.update({k: 100 for k in ALL_PRODUCTION_RESOURCES})

        resources = ResourceManager()
        resources.global_resources["credits"] = 5000

        shipyard.start_ship_build(
            "sol", "small_freighter", "ISS First",
            config_dict, inventory, resources,
        )
        shipyard.start_ship_build(
            "sol", "small_freighter", "ISS Second",
            config_dict, inventory, resources,
        )

        # First completes after 4 ticks, second should still be queued/active
        for _ in range(4):
            shipyard.process_tick(config=config_dict)
        summary = shipyard.get_build_queue_summary()
        self.assertEqual(len([o for o in summary if o.get("name") == "ISS First"]), 0)
        self.assertEqual(len([o for o in summary if o.get("name") == "ISS Second"]), 1)

        for _ in range(4):
            result = shipyard.process_tick(config=config_dict)
        self.assertEqual(len(result["ships_completed"]), 1)
        self.assertEqual(result["ships_completed"][0]["ship_name"], "ISS Second")

    def test_concurrent_build_limit(self):
        """Drydock at level 1 allows only 1 concurrent build."""
        config = _load_production_config()
        config_dict = config.to_dict()

        shipyard = ShipyardManager()
        drydock = OrbitalFacility(facility_type="drydock", level=1)
        shipyard.facilities["sol"] = [drydock]

        inventory = empty_production_inventory()
        inventory.update({k: 100 for k in ALL_PRODUCTION_RESOURCES})

        resources = ResourceManager()
        resources.global_resources["credits"] = 5000

        # First build should succeed
        order1 = shipyard.start_ship_build(
            "sol", "small_freighter", "ISS First",
            config_dict, inventory, resources,
        )
        self.assertIsNotNone(order1)

        # Second build should queue (only 1 active slot at level 1)
        order2 = shipyard.start_ship_build(
            "sol", "small_freighter", "ISS Second",
            config_dict, inventory, resources,
        )
        self.assertIsNotNone(order2)

        summary = shipyard.get_build_queue_summary()
        active = [o for o in summary if o.get("status") == "active"]
        queued = [o for o in summary if o.get("status") == "queued"]
        self.assertEqual(len(active), 1)
        self.assertEqual(len(queued), 1)


class TestSaveLoadPreservesProductionState(unittest.TestCase):
    """Test 5: Save/load roundtrip preserves inventories, routes, and queues."""

    def test_production_inventory_survives_roundtrip(self):
        """Production inventory persists through save/load."""
        gs = GameState.new_game()
        colony = gs.colonies.colonies["sol"]

        # Set up production state
        colony.production_inventory["ore_iron"] = 42
        colony.production_inventory["metal_alloys"] = 15
        colony.extraction_sites.append(
            ExtractionSite(resource_id="rare_metals", base_yield=2, level=1)
        )
        factory = Factory(active=True)
        factory.queue_recipe("metal_alloys")
        colony.factories.append(factory)

        # Save and load
        data = gs.to_dict()
        gs2 = GameState.from_dict(data)
        colony2 = gs2.colonies.colonies["sol"]

        self.assertEqual(colony2.production_inventory["ore_iron"], 42)
        self.assertEqual(colony2.production_inventory["metal_alloys"], 15)
        self.assertGreater(len(colony2.extraction_sites), 0)
        self.assertEqual(len(colony2.factories), 1)
        self.assertEqual(colony2.factories[0].recipe_queue, ["metal_alloys"])

    def test_logistics_routes_survive_roundtrip(self):
        """Freight routes persist through save/load."""
        gs = GameState.new_game()

        route = gs.logistics.create_route(
            name="Sol Express",
            waypoints=[
                {"system_id": "sol", "cargo_rules": [
                    {"resource_id": "ore_iron", "action": "load", "amount": 10},
                ]},
            ],
        )

        data = gs.to_dict()
        gs2 = GameState.from_dict(data)

        self.assertEqual(len(gs2.logistics.routes), 1)
        loaded_route = list(gs2.logistics.routes.values())[0]
        self.assertEqual(loaded_route.name, "Sol Express")
        self.assertEqual(len(loaded_route.waypoints), 1)

    def test_shipyard_survives_roundtrip(self):
        """Orbital facilities and build orders persist through save/load."""
        gs = GameState.new_game()

        # Verify starting spaceport exists
        self.assertIn("sol", gs.shipyard.facilities)

        # Add a drydock and queue a build
        gs.shipyard.facilities["sol"].append(OrbitalFacility(facility_type="drydock", level=1))
        colony = gs.colonies.colonies["sol"]
        colony.production_inventory.update({k: 50 for k in ALL_PRODUCTION_RESOURCES})
        gs.resources.global_resources["credits"] = 500
        queued = gs.shipyard.start_ship_build(
            "sol", "small_freighter", "ISS Persist",
            gs.production.config.to_dict(), colony.production_inventory, gs.resources,
        )
        self.assertIsNotNone(queued)

        data = gs.to_dict()
        gs2 = GameState.from_dict(data)

        self.assertIn("sol", gs2.shipyard.facilities)
        self.assertEqual(
            gs2.shipyard.facilities["sol"][0].facility_type,
            "spaceport",
        )
        summary = gs2.shipyard.get_build_queue_summary()
        self.assertTrue(any(o.get("name") == "ISS Persist" for o in summary))

    def test_schema_version_bumped(self):
        """Schema version is 8 after our changes."""
        gs = GameState.new_game()
        data = gs.to_dict()
        self.assertEqual(data["schema_version"], 8)


class TestIntegrationExtractionToShipBuild(unittest.TestCase):
    """Test 6: Full integration test — extraction through factories to ship build."""

    def test_full_pipeline_10_turns(self):
        """Run 10 turns with extraction and factories producing components."""
        gs = GameState.new_game()
        colony = gs.colonies.colonies["sol"]

        # Add more extraction sites
        colony.extraction_sites.append(
            ExtractionSite(resource_id="organics", base_yield=3, level=1)
        )

        # Add a factory producing metal_alloys on repeat
        factory = Factory(active=True)
        factory.queue_recipe("metal_alloys", count=10)
        colony.factories.append(factory)

        initial_ore = colony.production_inventory["ore_iron"]
        initial_alloys = colony.production_inventory["metal_alloys"]

        # Run 10 turns
        for _ in range(10):
            report = gs.process_turn()

        # After 10 turns, extraction should have added ore_iron
        # Factory should have converted some to alloys
        # Net alloys should increase if extraction keeps up with consumption
        self.assertGreater(
            colony.production_inventory["metal_alloys"],
            0,
            "Should have metal_alloys after 10 turns of extraction + factory",
        )

        # Organics should have been extracted
        self.assertGreater(
            colony.production_inventory["organics"],
            0,
            "Should have organics from extraction",
        )


class TestBodyTypeResourceAvailability(unittest.TestCase):
    """Test 7: Body type resource availability is data-driven."""

    def test_rocky_has_iron_and_silicates(self):
        """Rocky body type should offer ore_iron and silicates."""
        config = _load_production_config()
        body_res = config.get_body_resources("rocky")
        self.assertIn("ore_iron", body_res)
        self.assertIn("silicates", body_res)
        self.assertIn("water_ice", body_res)
        self.assertIn("fissiles", body_res)

    def test_gas_giant_has_h2(self):
        """Gas giant should offer gas_h2."""
        config = _load_production_config()
        body_res = config.get_body_resources("gas_giant")
        self.assertIn("gas_h2", body_res)
        self.assertIn("gas_he3", body_res)

    def test_ice_has_water(self):
        """Ice body should offer water_ice."""
        config = _load_production_config()
        body_res = config.get_body_resources("ice")
        self.assertIn("water_ice", body_res)
        self.assertIn("volatiles", body_res)

    def test_unknown_body_defaults(self):
        """Unknown body types should map to terrestrial rules."""
        config = _load_production_config()
        body_res = config.get_body_resources("unknown_type")
        self.assertIn("ore_iron", body_res)

    def test_tech_gated_resource_requires_prereq(self):
        """Tech-gated resources are hidden until prerequisites are researched."""
        config = ProductionConfig()
        config.world_types = {
            "gas_giant": {
                "gas_d2": {"base_yield": 2, "probability": 1.0, "requires_tech": ["deuterium_extraction"]},
            }
        }
        config.planet_type_map = {"gas_giant": "gas_giant"}
        pm = ProductionManager(config)

        without_tech = pm.determine_extraction_resources("gas_giant", seed=123, researched_techs=set())
        self.assertEqual(without_tech, [])

        with_tech = pm.determine_extraction_resources(
            "gas_giant", seed=123, researched_techs={"deuterium_extraction"},
        )
        self.assertEqual(with_tech[0]["resource_id"], "gas_d2")


if __name__ == "__main__":
    unittest.main(verbosity=2)
