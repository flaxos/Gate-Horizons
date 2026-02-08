"""UI source checks for the turn report summary screen."""

import os
import unittest


class TestTurnReportScreen(unittest.TestCase):
    def test_turn_report_screen_is_wired(self):
        base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        screen_path = os.path.join(base_dir, "ui", "screens", "turn_report_screen.py")
        main_path = os.path.join(base_dir, "main.py")
        galaxy_path = os.path.join(base_dir, "ui", "screens", "galaxy_map.py")

        with open(screen_path, encoding="utf-8") as handle:
            screen_source = handle.read()
        with open(main_path, encoding="utf-8") as handle:
            main_source = handle.read()
        with open(galaxy_path, encoding="utf-8") as handle:
            galaxy_source = handle.read()

        self.assertIn("class TurnReportScreen", screen_source)
        self.assertIn("show_turn_report", main_source)
        self.assertIn("show_turn_report", galaxy_source)


if __name__ == "__main__":
    unittest.main(verbosity=2)
