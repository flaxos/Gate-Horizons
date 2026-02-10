import os
import unittest

from gate_horizons.game.combat import EncounterData
from gate_horizons.game.state import GameState


class TestDiplomacyUnlockGate(unittest.TestCase):
    def test_encounter_branches_skip_diplomacy_when_locked(self):
        state = GameState.new_game()
        tech = state.tech.techs.get("signal_decryption")
        if tech:
            tech.researched = False
        encounter = EncounterData(
            type="alien_patrol",
            strength=10,
            description="Test encounter",
            loot_table={"intel": [1, 2]},
            faction_id="alien_patrol",
        )
        branches = state._get_encounter_branches(encounter)
        self.assertIn("tactical", branches)
        self.assertIn("evasion", branches)
        self.assertNotIn("diplomacy", branches)

    def test_relations_screen_shows_lock_message_when_locked(self):
        lock_message = "Diplomacy locked. Research Signal Decryption to unlock."
        ui_path = os.path.join(
            os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
            "ui", "screens", "relations_screen.py",
        )
        with open(ui_path, encoding="utf-8") as handle:
            source = handle.read()
        self.assertIn(lock_message, source)
        self.assertIn("unlock_diplomacy", source)

    def test_relation_action_is_blocked_when_locked(self):
        state = GameState.new_game()
        tech = state.tech.techs.get("signal_decryption")
        if tech:
            tech.researched = False
        success, message = state.resolve_relation_action("alien_patrol", "aid")
        self.assertFalse(success)
        self.assertIn("Signal Decryption", message)


if __name__ == "__main__":
    unittest.main()
