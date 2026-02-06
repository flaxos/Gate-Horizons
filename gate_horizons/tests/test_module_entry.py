import importlib
import unittest

from gate_horizons.game.state import GameState


class TestModuleEntry(unittest.TestCase):
    def test_module_entry_importable(self):
        module = importlib.import_module("gate_horizons.__main__")
        self.assertTrue(hasattr(module, "main"))
        state = GameState.new_game()
        self.assertIsNotNone(state)


if __name__ == "__main__":
    unittest.main()
