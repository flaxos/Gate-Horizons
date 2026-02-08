"""UI source checks for ship movement line rendering."""

import os
import unittest


class TestShipMovementLines(unittest.TestCase):
    def test_ship_paths_render_with_dash_lines(self):
        ui_path = os.path.join(
            os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
            "ui", "screens", "gravity_well_map.py",
        )
        with open(ui_path, encoding="utf-8") as handle:
            source = handle.read()

        self.assertIn("ship.path", source)
        self.assertIn("dash_length", source)
        self.assertIn("dash_offset", source)


if __name__ == "__main__":
    unittest.main(verbosity=2)
