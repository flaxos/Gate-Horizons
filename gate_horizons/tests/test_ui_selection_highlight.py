"""UI source checks for selection highlight effects."""

import os
import unittest


class TestSelectionHighlightEffects(unittest.TestCase):
    def test_selection_highlight_pulses_are_defined(self):
        ui_path = os.path.join(
            os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
            "ui", "screens", "gravity_well_map.py",
        )
        with open(ui_path, encoding="utf-8") as handle:
            source = handle.read()

        self.assertIn("selected_body_id", source)
        self.assertIn("glow_alpha", source)
        self.assertIn("selected_ship_id", source)
        self.assertIn("ring_alpha", source)


if __name__ == "__main__":
    unittest.main(verbosity=2)
