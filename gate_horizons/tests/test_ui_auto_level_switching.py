"""UI source checks for gravity well auto-level switching."""

import os
import unittest


class TestGravityWellAutoSwitching(unittest.TestCase):
    def test_auto_level_switch_constants_present(self):
        ui_path = os.path.join(
            os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
            "ui", "screens", "gravity_well_map.py",
        )
        with open(ui_path, encoding="utf-8") as handle:
            source = handle.read()

        self.assertIn("AUTO_SWITCH_ZOOM_IN", source)
        self.assertIn("AUTO_SWITCH_ZOOM_OUT", source)
        self.assertIn("AUTO_SWITCH_DEBOUNCE_S", source)


if __name__ == "__main__":
    unittest.main(verbosity=2)
