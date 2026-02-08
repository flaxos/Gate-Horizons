"""Tests for freighter logistics route creation."""

import unittest

from gate_horizons.game.state import GameState


class TestFreighterRouteCreation(unittest.TestCase):
    def test_create_freighter_route_loads_cargo(self):
        state = GameState.new_game()

        # Establish a second colony to route to.
        state.colonies.establish_colony(
            system_id="alpha_centauri",
            planet_id="ac_haven",
            name="Haven",
            initial_pop=60,
            level=0,
            world_traits=[],
        )

        sol_colony = state.colonies.colonies["sol"]
        sol_colony.production_inventory["ore_iron"] = 10

        freighter = next(
            ship for ship in state.fleet.ships.values() if ship.ship_class == "freighter"
        )

        success, _ = state.create_freighter_route(
            source_system_id="sol",
            dest_system_id="alpha_centauri",
            ship_id=freighter.id,
            resource_id="ore_iron",
            amount=4,
            name="Ore Shuttle",
        )

        self.assertTrue(success)
        route = state.logistics.get_route_for_ship(freighter.id)
        self.assertIsNotNone(route)
        self.assertEqual(route.waypoints[0].system_id, "sol")
        self.assertEqual(route.waypoints[1].system_id, "alpha_centauri")
        self.assertEqual(route.waypoints[0].cargo_rules[0].action, "load")
        self.assertEqual(route.waypoints[1].cargo_rules[0].action, "unload")

        prod_inventories = {
            system_id: colony.production_inventory
            for system_id, colony in state.colonies.colonies.items()
        }
        state.logistics.process_routes(
            fleet=state.fleet,
            colonies=state.colonies,
            galaxy=state.galaxy,
            production_inventories=prod_inventories,
        )

        self.assertEqual(freighter.cargo.get("ore_iron", 0), 4)
        self.assertEqual(sol_colony.production_inventory["ore_iron"], 6)
        self.assertTrue(freighter.path)


if __name__ == "__main__":
    unittest.main()
