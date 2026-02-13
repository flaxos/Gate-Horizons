"""UI source checks for AU-based orbit layout logic."""

import os
import unittest


class TestSystemMapAuOrbits(unittest.TestCase):
    def test_system_map_uses_au_orbit_layout_helpers(self):
        ui_path = os.path.join(
            os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
            "ui", "screens", "gravity_well_map.py",
        )
        with open(ui_path, encoding="utf-8") as handle:
            source = handle.read()

        self.assertIn("semi_major_axis_au", source)
        self.assertIn("_build_orbit_layout", source)
        self.assertIn("ORBIT_COMPRESSION_MODE", source)
        self.assertIn("ORBIT_MIN_VISUAL_SEPARATION_FRAC", source)


if __name__ == "__main__":
    unittest.main(verbosity=2)
