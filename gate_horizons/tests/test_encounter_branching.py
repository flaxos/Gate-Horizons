import unittest

from gate_horizons.game.combat import EncounterData
from gate_horizons.game.state import GameState
from gate_horizons.game.turn import TurnReport


class TestEncounterBranching(unittest.TestCase):
    def test_encounter_spec_serializes(self):
        state = GameState.new_game()
        system = state.galaxy.systems["sol"]
        ship = next(iter(state.fleet.ships.values()))
        encounter = EncounterData(
            type="alien_patrol",
            strength=10,
            description="Test encounter",
            loot_table={"intel": [1, 2]},
            faction_id="alien_patrol",
        )
        spec = state.combat.create_encounter_spec(
            attacker_ships=[ship],
            defender=encounter,
            system=system,
            encounter_id="enc-test",
        )
        data = spec.to_dict()
        self.assertEqual(data["contractVersion"], "1.0")
        self.assertEqual(data["encounterId"], "enc-test")
        self.assertIn("strategicContext", data)
        self.assertIn("factionContext", data["strategicContext"])

    def test_branch_options_include_diplomacy(self):
        state = GameState.new_game()
        system = state.galaxy.systems["sol"]
        ship = next(iter(state.fleet.ships.values()))
        encounter = EncounterData(
            type="alien_patrol",
            strength=10,
            description="Test encounter",
            loot_table={"intel": [1, 2]},
            faction_id="alien_patrol",
        )
        report = TurnReport(turn_number=1, game_date="January 2157")
        state.resolve_encounter([ship], encounter, system, report)
        pending = state.pending_encounters[-1]
        self.assertIn("diplomacy", pending.get("branch_options", []))
        self.assertIn("tactical", pending.get("branch_options", []))
        self.assertIn("evasion", pending.get("branch_options", []))

    def test_evasion_branch_resolves(self):
        state = GameState.new_game()
        system = state.galaxy.systems["sol"]
        ship = next(iter(state.fleet.ships.values()))
        encounter = EncounterData(
            type="pirates",
            strength=12,
            description="Test encounter",
            loot_table={"credits": [1, 2]},
            faction_id="pirates",
        )
        report = TurnReport(turn_number=1, game_date="January 2157")
        state.resolve_encounter([ship], encounter, system, report)
        encounter_id = state.pending_encounters[-1]["encounter_id"]
        success, message = state.resolve_evasion(encounter_id)
        self.assertTrue(success, message)
        self.assertFalse(state.pending_encounters)

    def test_relation_changes_from_result_spec(self):
        state = GameState.new_game()
        encounter_id = "enc-rel"
        state.pending_encounters.append(
            {
                "encounter_id": encounter_id,
                "spec": {},
                "attacker_ship_ids": [],
                "defender": {"faction_id": "alien_patrol"},
                "system_id": "sol",
            }
        )
        starting = state.diplomacy.get_score("alien_patrol")
        result_spec = {
            "contractVersion": "1.0",
            "encounterId": encounter_id,
            "outcome": "success",
            "loot": {"resources": {}},
            "relations": {"alien_patrol": 5},
        }
        success, _ = state.submit_encounter_result(result_spec)
        self.assertTrue(success)
        self.assertEqual(state.diplomacy.get_score("alien_patrol"), starting + 5)


if __name__ == "__main__":
    unittest.main()
