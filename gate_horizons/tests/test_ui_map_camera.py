"""UI source checks for map camera shortcuts."""

import os
import unittest


class TestMapCameraShortcuts(unittest.TestCase):
    def test_map_camera_supports_escape_back(self):
        ui_path = os.path.join(
            os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
            "ui", "widgets", "map_camera.py",
        )
        with open(ui_path, encoding="utf-8") as handle:
            source = handle.read()

        self.assertIn("Escape", source)
        self.assertIn("on_back", source)


if __name__ == "__main__":
    unittest.main(verbosity=2)
