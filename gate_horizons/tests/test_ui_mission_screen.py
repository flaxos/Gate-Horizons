"""UI source checks for the mission screen layout."""

import os
import unittest


class TestMissionScreenLayout(unittest.TestCase):
    """Ensure the Mission screen includes active/completed sections."""

    def test_mission_screen_sections_present(self):
        ui_path = os.path.join(
            os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
            "ui", "screens", "mission_screen.py",
        )
        with open(ui_path, encoding="utf-8") as handle:
            source = handle.read()

        self.assertIn("Active Missions", source)
        self.assertIn("Completed Missions", source)
        self.assertIn("mission_screen", source)
