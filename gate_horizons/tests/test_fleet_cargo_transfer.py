import unittest

from gate_horizons.game.resources import RESOURCE_TYPES
from gate_horizons.game.state import GameState


class TestFleetCargoTransfer(unittest.TestCase):
    def setUp(self):
        self.state = GameState.new_game()
        self.freighter = next(
            ship for ship in self.state.fleet.ships.values()
            if ship.ship_class == "freighter"
        )
        self.state.resources.global_resources = {r: 0 for r in RESOURCE_TYPES}
        self.state.resources.per_system_resources["sol"] = {r: 0 for r in RESOURCE_TYPES}

    def test_load_cargo_from_colony_manifest(self):
        self.state.resources.global_resources.update({
            "energy": 40,
            "metals": 25,
            "exotics": 5,
            "credits": 10,
            "intel": 8,
        })
        self.state.resources.per_system_resources["sol"].update({
            "energy": 40,
            "metals": 25,
            "exotics": 5,
            "credits": 10,
            "intel": 8,
        })

        loaded = self.state.load_ship_cargo_from_colony(
            self.freighter.id,
            {"energy": 30, "metals": 20},
        )

        self.assertEqual({"energy": 30, "metals": 20}, loaded)
        self.assertEqual(30, self.freighter.cargo.get("energy"))
        self.assertEqual(20, self.freighter.cargo.get("metals"))
        self.assertEqual(10, self.state.resources.global_resources["energy"])
        self.assertEqual(5, self.state.resources.global_resources["metals"])
        self.assertEqual(10, self.state.resources.per_system_resources["sol"]["energy"])
        self.assertEqual(5, self.state.resources.per_system_resources["sol"]["metals"])

    def test_load_cargo_from_colony_defaults_to_most_abundant(self):
        self.state.resources.global_resources.update({
            "energy": 10,
            "metals": 50,
            "exotics": 0,
            "credits": 0,
            "intel": 0,
        })
        self.state.resources.per_system_resources["sol"].update({
            "energy": 10,
            "metals": 50,
            "exotics": 0,
            "credits": 0,
            "intel": 0,
        })
        self.freighter.stats.cargo_capacity = 30

        loaded = self.state.load_ship_cargo_from_colony(self.freighter.id)

        self.assertEqual({"metals": 30}, loaded)
        self.assertEqual(30, self.freighter.cargo.get("metals"))
        self.assertEqual(20, self.state.resources.global_resources["metals"])
        self.assertEqual(20, self.state.resources.per_system_resources["sol"]["metals"])

    def test_unload_cargo_to_colony_resources_only(self):
        self.freighter.cargo = {"metals": 12, "exotics": 2, "fuel": 5}
        self.state.resources.global_resources = {r: 0 for r in RESOURCE_TYPES}
        self.state.resources.per_system_resources["sol"] = {r: 0 for r in RESOURCE_TYPES}

        unloaded = self.state.unload_ship_cargo_to_colony(self.freighter.id)

        self.assertEqual({"metals": 12, "exotics": 2}, unloaded)
        self.assertEqual(12, self.state.resources.global_resources["metals"])
        self.assertEqual(2, self.state.resources.global_resources["exotics"])
        self.assertEqual(12, self.state.resources.per_system_resources["sol"]["metals"])
        self.assertEqual(2, self.state.resources.per_system_resources["sol"]["exotics"])
        self.assertEqual({"fuel": 5}, self.freighter.cargo)


if __name__ == "__main__":
    unittest.main()
