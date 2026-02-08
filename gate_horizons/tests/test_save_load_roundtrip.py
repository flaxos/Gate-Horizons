import unittest

from gate_horizons.game.state import GameState


class TestSaveLoadRoundtrip(unittest.TestCase):
    def test_save_load_roundtrip_preserves_core_state(self):
        state = GameState.new_game(galaxy_seed=7)
        state.resources.add("metals", 5, system_id="sol")
        state.rng.random()

        data = state.to_dict()
        data.pop("schema_version", None)
        data.pop("game_clock", None)
        data.pop("difficulty", None)
        data.pop("game_time", None)
        data.pop("log", None)

        loaded = GameState.from_dict(data)

        self.assertEqual(state.turn_number, loaded.turn_number)
        self.assertEqual(state.game_time, loaded.game_time)
        self.assertEqual(len(state.fleet.ships), len(loaded.fleet.ships))
        self.assertEqual(len(state.colonies.colonies), len(loaded.colonies.colonies))
        self.assertEqual(
            state.resources.global_resources,
            loaded.resources.global_resources,
        )
        self.assertEqual(state.rng.random(), loaded.rng.random())


if __name__ == "__main__":
    unittest.main()
