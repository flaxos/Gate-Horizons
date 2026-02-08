"""UI smoke checks for the playable loop expectations."""

import os
import unittest


class TestGalaxyMapPlayableLoop(unittest.TestCase):
    """Ensure the galaxy map keeps a colony panel in sync after turns."""

    def test_galaxy_map_auto_selects_home_colony_and_refreshes_panel(self):
        """Galaxy map should auto-select a colony and refresh side panel."""
        ui_path = os.path.join(
            os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
            "ui", "screens", "galaxy_map.py",
        )
        with open(ui_path, encoding="utf-8") as handle:
            source = handle.read()

        self.assertIn("selected_system_id", source)
        self.assertIn("_auto_select_home_colony", source)
        self.assertIn("_refresh_side_panel", source)
        self.assertIn("self._auto_select_home_colony()", source)
        self.assertIn("self._refresh_side_panel()", source)
