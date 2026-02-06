import importlib
import unittest

from gate_horizons.game.state import GameState


class TestModuleEntry(unittest.TestCase):
    def test_module_entry_importable(self):
        try:
            module = importlib.import_module("gate_horizons.__main__")
        except ImportError:
            self.skipTest("Kivy not installed — skipping __main__ import test")
        self.assertTrue(hasattr(module, "main"))

    def test_game_state_new_game(self):
        state = GameState.new_game()
        self.assertIsNotNone(state)
        self.assertEqual(state.turn_number, 0)
        self.assertGreater(len(state.fleet.ships), 0)
        self.assertGreater(len(state.colonies.colonies), 0)


if __name__ == "__main__":
    unittest.main()
