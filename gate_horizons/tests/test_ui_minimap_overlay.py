"""UI source checks for the gravity well mini-map overlay."""

import os
import unittest


class TestMiniMapOverlay(unittest.TestCase):
    def test_minimap_widget_is_defined_and_used(self):
        ui_path = os.path.join(
            os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
            "ui", "screens", "gravity_well_map.py",
        )
        with open(ui_path, encoding="utf-8") as handle:
            source = handle.read()

        self.assertIn("class MiniMapWidget", source)
        self.assertIn("self.mini_map", source)


if __name__ == "__main__":
    unittest.main(verbosity=2)
