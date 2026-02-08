"""UI source checks for fog of war visuals."""

import os
import unittest


class TestFogOfWarSystemMap(unittest.TestCase):
    def test_system_map_uses_survey_flags(self):
        ui_path = os.path.join(
            os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
            "ui", "screens", "gravity_well_map.py",
        )
        with open(ui_path, encoding="utf-8") as handle:
            source = handle.read()

        self.assertIn("system.surveyed", source)
        self.assertIn("Survey required to reveal body details.", source)


if __name__ == "__main__":
    unittest.main(verbosity=2)
