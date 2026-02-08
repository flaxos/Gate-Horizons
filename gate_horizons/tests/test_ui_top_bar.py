"""UI source checks for the top resource bar layout."""

import os
import unittest


class TestTopBarLayout(unittest.TestCase):
    """Ensure the TopBar uses a fixed height to avoid stretching."""

    def test_top_bar_sets_fixed_height(self):
        ui_path = os.path.join(
            os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
            "ui", "widgets", "resource_bar.py",
        )
        with open(ui_path, encoding="utf-8") as handle:
            source = handle.read()

        self.assertIn("self.size_hint_y = None", source)
        self.assertIn("self.height = dp(36)", source)
