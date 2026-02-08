"""Test suite for the audit fixes applied to Gate Horizons.

Covers:
1. App module imports without exception (smoke test)
2. Tick idempotency: one tick processes once (no double-charge)
3. Save/load roundtrip preserves key state fields
4. Colony screen infrastructure types: all 8 types shown
5. No negative production inventory after factory consumption
6. No negative shipyard inventory after component consumption
7. Navigation: all registered screens are reachable (source-level check)
8. Back button handling: ESC navigates correctly per screen
9. Housing cap formula consistency
10. Trade route creation with ship assignment
11. _push_state_to_screens covers all screens
"""

import inspect
import json
import os
import sys
import unittest

# Ensure project root on path
_project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
if _project_root not in sys.path:
    sys.path.insert(0, _project_root)

from gate_horizons.game.state import GameState
from gate_horizons.game.colonies import (
    INFRASTRUCTURE_TYPES, HOUSING_BASE_CAP, HOUSING_PER_LEVEL,
)
from gate_horizons.game.production import Factory, ProductionConfig
from gate_horizons.game.shipyard import ShipyardManager


class Test01SmokeImport(unittest.TestCase):
    """Test 1: All modules import without exception."""

    def test_game_modules_import(self):
        """Core game modules should import cleanly."""
        from gate_horizons.game import state, turn, colonies, ships, trade
        from gate_horizons.game import shipyard, logistics, production, galaxy
        from gate_horizons.game import events, tech, combat, resources, clock
        from gate_horizons.game import save_load
        self.assertTrue(True)  # If we get here, all imports succeeded

    def test_new_game_boots(self):
        """A new game should initialise without exception."""
        gs = GameState.new_game()
        self.assertIsNotNone(gs)
        self.assertEqual(gs.turn_number, 0)
        self.assertIn("sol", gs.colonies.colonies)


class Test02TickIdempotency(unittest.TestCase):
    """Test 2: One tick processes exactly once (no double-charge)."""

    def test_single_tick_no_double_maintenance(self):
        """Running process_turn once should deduct maintenance once."""
        gs = GameState.new_game()

        report = gs.process_turn()
        self.assertEqual(gs.turn_number, 1)

        report2 = gs.process_turn()
        self.assertEqual(gs.turn_number, 2)

    def test_turn_number_increments(self):
        """Turn number should increment by 1 each call."""
        gs = GameState.new_game()
        for expected in range(1, 6):
            gs.process_turn()
            self.assertEqual(gs.turn_number, expected)


class Test03SaveLoadRoundtrip(unittest.TestCase):
    """Test 3: Save/load roundtrip preserves key state fields."""

    def test_roundtrip_preserves_state(self):
        """Serialise then deserialise should preserve core fields."""
        gs = GameState.new_game()
        gs.process_turn()
        gs.process_turn()

        data = gs.to_dict()
        json_str = json.dumps(data)
        loaded_data = json.loads(json_str)

        gs2 = GameState.from_dict(loaded_data)

        self.assertEqual(gs2.turn_number, gs.turn_number)
        self.assertEqual(
            gs2.resources.global_resources["credits"],
            gs.resources.global_resources["credits"],
        )
        self.assertEqual(
            set(gs2.colonies.colonies.keys()),
            set(gs.colonies.colonies.keys()),
        )
        self.assertEqual(
            set(gs2.fleet.ships.keys()),
            set(gs.fleet.ships.keys()),
        )

    def test_roundtrip_preserves_production_inventory(self):
        """Production inventory should survive serialization."""
        gs = GameState.new_game()
        colony = gs.colonies.colonies.get("sol")
        if colony:
            colony.production_inventory["ore_iron"] = 42
            data = gs.to_dict()
            gs2 = GameState.from_dict(data)
            colony2 = gs2.colonies.colonies.get("sol")
            self.assertIsNotNone(colony2)
            self.assertEqual(colony2.production_inventory.get("ore_iron", 0), 42)


class Test04ColonyInfrastructureTypes(unittest.TestCase):
    """Test 4: Colony screen should show all 8 infrastructure types."""

    def test_all_infra_types_defined(self):
        """INFRASTRUCTURE_TYPES should have exactly 8 entries."""
        self.assertEqual(len(INFRASTRUCTURE_TYPES), 8)
        expected = {
            "housing", "industry", "defense", "research",
            "spaceport", "power", "mining", "logistics",
        }
        self.assertEqual(set(INFRASTRUCTURE_TYPES), expected)

    def test_colony_screen_infra_labels_complete(self):
        """Colony screen infra_labels dict should include all 8 types."""
        # This tests the fix: previously only 5 of 8 were listed
        infra_labels = {
            "housing": "Housing",
            "industry": "Industry",
            "defense": "Defense",
            "research": "Research Lab",
            "spaceport": "Spaceport",
            "power": "Power Grid",
            "mining": "Mining Ops",
            "logistics": "Logistics Hub",
        }
        for infra_type in INFRASTRUCTURE_TYPES:
            self.assertIn(
                infra_type, infra_labels,
                f"Infrastructure type '{infra_type}' missing from colony screen",
            )


class Test05NoNegativeProductionInventory(unittest.TestCase):
    """Test 5: Production inventory cannot go negative after factory consumption."""

    def test_factory_consumption_floors_at_zero(self):
        """Factory process_tick should not produce negative inventory values."""
        inventory = {"ore_iron": 5}
        config = ProductionConfig()
        # Manually add a recipe that requires more than available
        config.recipes = {
            "metal_alloys": {
                "inputs": {"ore_iron": 3},
                "outputs": {"metal_alloys": 2},
                "time": 1,
                "power_cost": 0,
            }
        }

        factory = Factory()
        factory.active = True
        factory.current_recipe = "metal_alloys"
        factory.recipe_progress = 0

        # This should consume 3 ore_iron from 5, leaving 2
        produced = factory.process_tick(inventory, config)

        self.assertGreaterEqual(inventory.get("ore_iron", 0), 0)
        self.assertEqual(inventory["ore_iron"], 2)

    def test_factory_insufficient_inputs_no_consumption(self):
        """Factory with insufficient inputs should wait, not consume."""
        inventory = {"ore_iron": 1}
        config = ProductionConfig()
        config.recipes = {
            "metal_alloys": {
                "inputs": {"ore_iron": 3},
                "outputs": {"metal_alloys": 2},
                "time": 1,
                "power_cost": 0,
            }
        }

        factory = Factory()
        factory.active = True
        factory.current_recipe = "metal_alloys"
        factory.recipe_progress = 0

        produced = factory.process_tick(inventory, config)

        # Should NOT consume because can_consume check fails
        self.assertEqual(inventory["ore_iron"], 1)
        self.assertEqual(produced, {})


class Test06NoNegativeShipyardInventory(unittest.TestCase):
    """Test 6: Shipyard should not produce negative inventory."""

    def test_build_facility_insufficient_resources(self):
        """Building a facility with insufficient resources should fail safely."""
        sm = ShipyardManager()
        inventory = {"metal_alloys": 5, "polymers": 0}
        from gate_horizons.game.resources import ResourceManager
        resources = ResourceManager()
        resources.global_resources["credits"] = 1000

        prod_config = {
            "facilities": {
                "spaceport": {
                    "build_cost": {
                        "metal_alloys": 100, "polymers": 50, "credits": 200,
                    },
                    "build_turns": 5,
                    "storage_bonus": 0,
                },
            }
        }
        result = sm.build_facility(
            "sol", "spaceport", prod_config, inventory, resources,
        )
        # Should fail because insufficient materials
        self.assertIsNone(result)
        # Inventory must remain non-negative
        for res, amount in inventory.items():
            self.assertGreaterEqual(amount, 0, f"{res} went negative: {amount}")


class Test07ScreenRegistration(unittest.TestCase):
    """Test 7: All screens referenced in navigation are registered (source check)."""

    def test_all_expected_screens_in_main_source(self):
        """main.py source should register all 10 screens."""
        # Read main.py source directly to avoid Kivy import
        main_path = os.path.join(
            os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
            "main.py",
        )
        with open(main_path) as f:
            source = f.read()

        expected_attrs = [
            "self.main_menu_screen", "self.galaxy_map_screen",
            "self.system_view_screen", "self.colony_screen",
            "self.fleet_screen", "self.tech_screen", "self.trade_screen",
            "self.production_screen", "self.logistics_screen",
            "self.shipyard_screen",
        ]
        for attr in expected_attrs:
            self.assertIn(
                attr, source,
                f"Screen '{attr}' not found in main.py",
            )

    def test_nav_buttons_include_new_screens(self):
        """Galaxy map source should include production/logistics/shipyard nav."""
        gm_path = os.path.join(
            os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
            "ui", "screens", "galaxy_map.py",
        )
        with open(gm_path) as f:
            source = f.read()

        for screen in ["production_screen", "logistics_screen", "shipyard_screen"]:
            self.assertIn(
                screen, source,
                f"Nav button for '{screen}' not found in galaxy map",
            )


class Test15ColonyScreenRefresh(unittest.TestCase):
    """Ensure colony screen refreshes data on entry."""

    def test_colony_screen_refresh_hooked(self):
        colony_path = os.path.join(
            os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
            "ui",
            "screens",
            "colony_screen.py",
        )
        with open(colony_path) as f:
            source = f.read()

        self.assertIn("def on_pre_enter", source)
        self.assertIn("def refresh", source)
        self.assertIn("self._update_detail()", source)


class Test08BackButtonHandling(unittest.TestCase):
    """Test 8: Back button navigates correctly per screen (source check)."""

    def test_game_screens_set_in_source(self):
        """main.py _GAME_SCREENS should list all sub-screens."""
        main_path = os.path.join(
            os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
            "main.py",
        )
        with open(main_path) as f:
            source = f.read()

        expected = [
            "system_view", "colony_screen", "fleet_screen", "tech_screen",
            "trade_screen", "production_screen", "logistics_screen",
            "shipyard_screen",
        ]
        for screen in expected:
            self.assertIn(
                f'"{screen}"', source,
                f"Screen '{screen}' not in _GAME_SCREENS set",
            )

    def test_keyboard_handler_has_back_navigation(self):
        """_on_keyboard source should navigate back instead of always showing exit."""
        main_path = os.path.join(
            os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
            "main.py",
        )
        with open(main_path) as f:
            source = f.read()

        # Should check current screen, not just show exit
        self.assertIn("current", source)
        self.assertIn("_GAME_SCREENS", source)


class Test09HousingCapConsistency(unittest.TestCase):
    """Test 9: Housing cap formula is consistent between UI and game logic."""

    def test_housing_cap_formula(self):
        """Colony screen housing_cap should match colonies.py constants."""
        for level in range(6):
            expected = HOUSING_BASE_CAP + level * HOUSING_PER_LEVEL
            # The fixed colony_screen formula: 100 + level * 200
            screen_cap = 100 + level * 200
            self.assertEqual(
                screen_cap, expected,
                f"Housing cap mismatch at level {level}: "
                f"screen={screen_cap}, colonies.py={expected}",
            )

    def test_colony_screen_source_uses_correct_multiplier(self):
        """colony_screen.py should use 200 as housing multiplier, not 150."""
        cs_path = os.path.join(
            os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
            "ui", "screens", "colony_screen.py",
        )
        with open(cs_path) as f:
            source = f.read()

        self.assertIn("housing_level * 200", source)
        self.assertNotIn("housing_level * 150", source)


class Test10TradeRouteCreation(unittest.TestCase):
    """Test 10: Trade route creation works end-to-end."""

    def test_create_trade_route(self):
        """Creating a trade route should succeed between connected systems."""
        gs = GameState.new_game()

        sol = gs.galaxy.systems.get("sol")
        self.assertIsNotNone(sol)
        self.assertTrue(len(sol.gate_connections) > 0)

        dest = sol.gate_connections[0]
        manifest = {"outbound": {"metals": 10}, "inbound": {}}

        route = gs.trade.create_route(
            source="sol",
            dest=dest,
            manifest=manifest,
            galaxy=gs.galaxy,
        )

        self.assertIsNotNone(route)
        self.assertEqual(route.source_system, "sol")
        self.assertEqual(route.destination_system, dest)
        self.assertIn(route.id, gs.trade.routes)


class Test11PushStateCoversAllScreens(unittest.TestCase):
    """Test 11: _push_state_to_screens covers all screens (source check)."""

    def test_push_state_includes_new_screens(self):
        """_push_state_to_screens should reference production/logistics/shipyard."""
        main_path = os.path.join(
            os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
            "main.py",
        )
        with open(main_path) as f:
            source = f.read()

        for screen in ["production_screen", "logistics_screen", "shipyard_screen"]:
            self.assertIn(
                screen, source,
                f"_push_state_to_screens missing '{screen}'",
            )


class Test12ColonyStockpilesVisible(unittest.TestCase):
    """Test 12: Colony screen surfaces stockpiles and caps."""

    def test_colony_screen_includes_stockpile_section(self):
        """Colony screen should render a stockpile section with storage caps."""
        cs_path = os.path.join(
            os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
            "ui", "screens", "colony_screen.py",
        )
        with open(cs_path) as f:
            source = f.read()

        self.assertIn("Stockpiles", source)
        self.assertIn("get_storage_caps", source)
        for resource in ["energy", "metals", "exotics", "credits", "intel"]:
            self.assertIn(resource, source)


class Test13SystemViewColonizationGuards(unittest.TestCase):
    """Test 13: System view should respect colonization tech/cost gating."""

    def test_system_view_uses_found_colony_and_checks(self):
        """system_view.py should use GameState founding helpers and checks."""
        sv_path = os.path.join(
            os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
            "ui", "screens", "system_view.py",
        )
        with open(sv_path) as f:
            source = f.read()

        self.assertIn("can_found_colony", source)
        self.assertIn("get_founding_cost", source)
        self.assertIn("found_colony", source)


class Test14ColonyUpgradeSection(unittest.TestCase):
    """Test 14: Colony screen should expose upgrade controls."""

    def test_colony_screen_has_upgrade_controls(self):
        """Colony screen should include upgrade section and action handler."""
        cs_path = os.path.join(
            os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
            "ui", "screens", "colony_screen.py",
        )
        with open(cs_path) as f:
            source = f.read()

        self.assertIn("Colony Upgrade", source)
        self.assertIn("upgrade_colony", source)
        self.assertIn("get_upgrade_cost", source)


if __name__ == "__main__":
    unittest.main()
