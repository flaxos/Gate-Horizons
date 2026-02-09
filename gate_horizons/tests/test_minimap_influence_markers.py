"""Tests for mini-map sphere-of-influence data."""

import unittest

from gate_horizons.game.state import GameState


class TestMiniMapInfluenceMarkers(unittest.TestCase):
    def test_player_colonies_generate_influence_markers(self):
        state = GameState.new_game()

        systems = list(state.galaxy.systems.values())
        target_system = next(system for system in systems if system.id != "sol")
        neutral_system = next(
            system for system in systems if system.id not in {"sol", target_system.id}
        )

        target_colony = state.colonies.establish_colony(
            system_id=target_system.id,
            planet_id=target_system.planets[0].id,
            name="Outpost",
            level=2,
        )

        neutral_colony = state.colonies.establish_colony(
            system_id=neutral_system.id,
            planet_id=neutral_system.planets[0].id,
            name="Neutral",
            level=1,
        )
        neutral_colony.owner_faction = "neutral"

        markers = state.colonies.get_player_influence_markers(state.galaxy)
        markers_by_system = {marker["system_id"]: marker["level"] for marker in markers}

        self.assertIn("sol", markers_by_system)
        self.assertIn(target_system.id, markers_by_system)
        self.assertNotIn(neutral_system.id, markers_by_system)
        self.assertEqual(markers_by_system[target_system.id], target_colony.level)


if __name__ == "__main__":
    unittest.main(verbosity=2)
