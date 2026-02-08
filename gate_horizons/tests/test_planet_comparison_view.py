"""Tests for planet comparison data extraction."""

import unittest

from gate_horizons.game.planet_comparison import build_comparison_data
from gate_horizons.game.state import GameState


class TestPlanetComparisonView(unittest.TestCase):
    def test_build_comparison_data_multiple_bodies(self):
        state = GameState.new_game()
        system = state.galaxy.systems.get("sol")
        if not system:
            system = next(iter(state.galaxy.systems.values()))
        body_ids = [p.id for p in system.planets[:2]]
        self.assertGreaterEqual(len(body_ids), 2)

        data = build_comparison_data(system, body_ids)
        self.assertEqual(len(data), len(body_ids))
        self.assertEqual({item["id"] for item in data}, set(body_ids))
        for item in data:
            self.assertIn("name", item)
            self.assertIn("type", item)
            self.assertIn("habitability", item)
            self.assertIn("gravity", item)
            self.assertIn("traits", item)
            self.assertIn("resources", item)

    def test_build_comparison_data_redacts_when_unsurveyed(self):
        state = GameState.new_game()
        system = state.galaxy.systems.get("sol")
        if not system:
            system = next(iter(state.galaxy.systems.values()))
        system.surveyed = False
        body_ids = [p.id for p in system.planets[:2]]
        data = build_comparison_data(system, body_ids)
        self.assertEqual(len(data), len(body_ids))
        for item in data:
            self.assertEqual(item["name"], "Unknown Body")
            self.assertFalse(item["surveyed"])


if __name__ == "__main__":
    unittest.main(verbosity=2)
