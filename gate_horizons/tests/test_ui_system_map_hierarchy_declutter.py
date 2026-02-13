"""Targeted UI source checks for hierarchy + declutter interactions."""

import os
import unittest


class TestSystemMapHierarchyDeclutter(unittest.TestCase):
    def _load_source(self):
        ui_path = os.path.join(
            os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
            "ui", "screens", "gravity_well_map.py",
        )
        with open(ui_path, encoding="utf-8") as handle:
            return handle.read()

    def test_system_map_builds_planet_moon_hierarchy(self):
        source = self._load_source()
        self.assertIn("def _prepare_body_hierarchy", source)
        self.assertIn('getattr(body, "body_type", "") == "moon"', source)
        self.assertIn("parent_idx = int(math.floor(orbit_index))", source)
        self.assertIn("moons_by_parent.setdefault(parent.id, []).append(body)", source)

    def test_declutter_and_hitboxes_keep_child_body_selection(self):
        source = self._load_source()
        self.assertIn("show_moons = detail_level in", source)
        self.assertIn("show_labels = detail_level == \"near\"", source)
        self.assertIn("show_moon_icon = self._claim_bounds", source)
        self.assertIn("self._interactive_body_positions[moon.id]", source)
        self.assertIn("for body_id, (bx, by, hit_radius) in self._interactive_body_positions.items()", source)


if __name__ == "__main__":
    unittest.main(verbosity=2)
