"""UI smoke checks for settings popup wiring."""

import os
import unittest


class TestSettingsPopupWiring(unittest.TestCase):
    def test_main_menu_opens_settings_popup(self):
        ui_path = os.path.join(
            os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
            "ui", "screens", "main_menu.py",
        )
        with open(ui_path, encoding="utf-8") as handle:
            source = handle.read()

        self.assertIn("SettingsPopup", source)
        self.assertIn("apply_settings", source)
