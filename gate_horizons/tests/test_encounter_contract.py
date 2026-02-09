"""Tests for EncounterSpec export and ResultSpec import."""

import json
import tempfile
import unittest
from unittest import mock

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

            state.resources.sync_from_colonies(state.colonies)
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

    def test_import_result_spec_rejects_unaffordable_costs(self):
        state = GameState.new_game()
        with tempfile.TemporaryDirectory() as tmpdir:
            success, _ = state.export_encounter_spec(
                system_id="sol",
                encounter_type="pirates",
                exports_dir=tmpdir,
            )
            self.assertTrue(success)

            encounter_id = state.pending_encounters[-1]["encounter_id"]
            starting_credits = state.resources.global_resources.get("credits", 0)
            result_spec = {
                "contractVersion": "1.0",
                "encounterId": encounter_id,
                "outcome": "failure",
                "missionTime": "1h",
                "assetStatus": {},
                "loot": {"resources": {"credits": -(starting_credits + 1)}},
                "notes": "Unaffordable costs",
            }

            with open(f"{tmpdir}/ResultSpec.json", "w", encoding="utf-8") as handle:
                json.dump(result_spec, handle)

            success, message = state.import_result_spec(imports_dir=tmpdir)
            self.assertFalse(success)
            self.assertIn("Insufficient resources", message)

    def test_import_result_spec_rejects_negative_resource_shortfall(self):
        state = GameState.new_game()
        with tempfile.TemporaryDirectory() as tmpdir:
            success, _ = state.export_encounter_spec(
                system_id="sol",
                encounter_type="pirates",
                exports_dir=tmpdir,
            )
            self.assertTrue(success)

            encounter_id = state.pending_encounters[-1]["encounter_id"]
            state.resources.sync_from_colonies(state.colonies)
            starting_metals = state.resources.global_resources.get("metals", 0)
            result_spec = {
                "contractVersion": "1.0",
                "encounterId": encounter_id,
                "outcome": "failure",
                "missionTime": "1h",
                "assetStatus": {},
                "loot": {"resources": {"metals": -(starting_metals + 2)}},
                "notes": "Unaffordable metals cost",
            }

            with open(f"{tmpdir}/ResultSpec.json", "w", encoding="utf-8") as handle:
                json.dump(result_spec, handle)

            success, message = state.import_result_spec(imports_dir=tmpdir)
            self.assertFalse(success)
            self.assertIn("Insufficient resources for encounter result", message)
            self.assertIn("metals", message)

    def test_export_encounter_spec_does_not_queue_on_invalid_payload(self):
        state = GameState.new_game()
        with tempfile.TemporaryDirectory() as tmpdir:
            pending_before = len(state.pending_encounters)
            with mock.patch.object(state.combat, "validate_encounter_spec", return_value=(False, "bad")):
                success, message = state.export_encounter_spec(
                    system_id="sol",
                    encounter_type="pirates",
                    exports_dir=tmpdir,
                )
            self.assertFalse(success)
            self.assertEqual(message, "bad")
            self.assertEqual(len(state.pending_encounters), pending_before)

    def test_submit_encounter_result_normalizes_loot_and_relations(self):
        state = GameState.new_game()
        with tempfile.TemporaryDirectory() as tmpdir:
            success, _ = state.export_encounter_spec(
                system_id="sol",
                encounter_type="pirates",
                exports_dir=tmpdir,
            )
            self.assertTrue(success)

            encounter_id = state.pending_encounters[-1]["encounter_id"]
            state.resources.sync_from_colonies(state.colonies)
            starting_credits = state.resources.global_resources.get("credits", 0)
            starting_metals = state.resources.global_resources.get("metals", 0)
            starting_intel = state.resources.global_resources.get("intel", 0)
            starting_relation = state.diplomacy.get_score("pirates")

            result_spec = {
                "contractVersion": "1.0",
                "encounterId": encounter_id,
                "outcome": "success",
                "loot": {
                    "intel": "3",
                    "resources": {"credits": "5", "metals": "bad", "exotics": None},
                },
                "relations": {"pirates": "2", "": "4"},
                "notes": "Normalization coverage",
            }

            success, message = state.submit_encounter_result(result_spec)
            self.assertTrue(success, message)
            self.assertEqual(
                state.resources.global_resources.get("credits", 0),
                starting_credits + 5,
            )
            self.assertEqual(
                state.resources.global_resources.get("metals", 0),
                starting_metals,
            )
            self.assertEqual(
                state.resources.global_resources.get("intel", 0),
                starting_intel + 3,
            )
            self.assertEqual(
                state.diplomacy.get_score("pirates"),
                starting_relation + 2,
            )

    def test_load_filters_invalid_pending_encounters(self):
        state = GameState.new_game()
        data = state.to_dict()
        data["pending_encounters"] = [
            "invalid",
            {"encounter_id": ""},
            {"encounter_id": "enc-valid", "spec": {}},
            {"encounter_id": None},
        ]
        loaded = GameState.from_dict(data)
        self.assertEqual(len(loaded.pending_encounters), 1)
        self.assertEqual(loaded.pending_encounters[0]["encounter_id"], "enc-valid")


if __name__ == "__main__":
    unittest.main(verbosity=2)
