"""Tests for EncounterSpec export and ResultSpec import."""

import json
import tempfile
import unittest

from gate_horizons.game.state import GameState


class TestEncounterContract(unittest.TestCase):
    def test_export_encounter_spec(self):
        state = GameState.new_game()
        with tempfile.TemporaryDirectory() as tmpdir:
            success, message = state.export_encounter_spec(
                system_id="sol",
                encounter_type="pirates",
                exports_dir=tmpdir,
            )
            self.assertTrue(success, message)
            spec_path = f"{tmpdir}/EncounterSpec.json"
            with open(spec_path, "r", encoding="utf-8") as handle:
                data = json.load(handle)
            self.assertIn("encounterId", data)
            self.assertEqual(data.get("contractVersion"), "1.0")

    def test_import_result_spec_applies_consequences(self):
        state = GameState.new_game()
        with tempfile.TemporaryDirectory() as tmpdir:
            success, _ = state.export_encounter_spec(
                system_id="sol",
                encounter_type="pirates",
                exports_dir=tmpdir,
            )
            self.assertTrue(success)

            encounter_id = state.pending_encounters[-1]["encounter_id"]
            ship_id = state.pending_encounters[-1]["attacker_ship_ids"][0]
            ship = state.fleet.ships[ship_id]
            colony = state.colonies.colonies["sol"]

            starting_credits = state.resources.global_resources.get("credits", 0)
            starting_metals = state.resources.global_resources.get("metals", 0)
            starting_intel = state.resources.global_resources.get("intel", 0)
            starting_hull = ship.hull
            starting_stability = colony.stability

            result_spec = {
                "contractVersion": "1.0",
                "encounterId": encounter_id,
                "outcome": "failure",
                "missionTime": "1h",
                "assetStatus": {ship_id: "damaged"},
                "loot": {
                    "intel": 1,
                    "resources": {"credits": -5, "metals": 3},
                },
                "notes": "Test outcome",
            }

            with open(f"{tmpdir}/ResultSpec.json", "w", encoding="utf-8") as handle:
                json.dump(result_spec, handle)

            success, message = state.import_result_spec(imports_dir=tmpdir)
            self.assertTrue(success, message)

            expected_damage = max(1, int(ship.stats.max_hull * 0.25))
            self.assertEqual(ship.hull, starting_hull - expected_damage)
            self.assertEqual(
                state.resources.global_resources.get("credits", 0),
                starting_credits - 5,
            )
            self.assertEqual(
                state.resources.global_resources.get("metals", 0),
                starting_metals + 3,
            )
            self.assertEqual(
                state.resources.global_resources.get("intel", 0),
                starting_intel + 1,
            )
            self.assertEqual(colony.stability, starting_stability - 2)

    def test_import_result_spec_rejects_invalid_payload(self):
        state = GameState.new_game()
        with tempfile.TemporaryDirectory() as tmpdir:
            success, _ = state.export_encounter_spec(
                system_id="sol",
                encounter_type="pirates",
                exports_dir=tmpdir,
            )
            self.assertTrue(success)

            invalid_result = {
                "contractVersion": "1.0",
                "outcome": "success",
            }
            with open(f"{tmpdir}/ResultSpec.json", "w", encoding="utf-8") as handle:
                json.dump(invalid_result, handle)

            success, message = state.import_result_spec(imports_dir=tmpdir)
            self.assertFalse(success)
            self.assertIn("encounterId", message)


if __name__ == "__main__":
    unittest.main(verbosity=2)
