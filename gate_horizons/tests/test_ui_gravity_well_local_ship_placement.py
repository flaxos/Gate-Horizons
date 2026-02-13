"""UI source checks for body-anchor local ship placement."""

import os
import unittest


class TestGravityWellLocalShipPlacement(unittest.TestCase):
    def test_ship_placement_uses_body_anchor_and_local_transit(self):
        ui_path = os.path.join(
            os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
            "ui", "screens", "gravity_well_map.py",
        )
        with open(ui_path, encoding="utf-8") as handle:
            source = handle.read()

        self.assertIn("ship.body_id", source)
        self.assertIn("ship.local_destination_body_id", source)
        self.assertIn("ship.local_transit_remaining_ticks", source)


if __name__ == "__main__":
    unittest.main(verbosity=2)
