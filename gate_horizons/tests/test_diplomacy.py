import unittest

from gate_horizons.game.diplomacy import DiplomacyManager
from gate_horizons.game.state import GameState


class TestDiplomacy(unittest.TestCase):
    def test_relation_score_changes(self):
        diplomacy = DiplomacyManager()
        start = diplomacy.get_score("alien_patrol")
        diplomacy.adjust_score("alien_patrol", 10)
        self.assertEqual(diplomacy.get_score("alien_patrol"), start + 10)

    def test_persistence_roundtrip(self):
        state = GameState.new_game()
        state.diplomacy.adjust_score("pirates", 20)
        snapshot = state.to_dict()
        loaded = GameState.from_dict(snapshot)
        self.assertEqual(
            loaded.diplomacy.get_score("pirates"),
            state.diplomacy.get_score("pirates"),
        )

    def test_diplomacy_outcome_modifies_options(self):
        diplomacy = DiplomacyManager()
        diplomacy.set_score("alien_patrol", -40)
        self.assertEqual(diplomacy.available_actions("alien_patrol"), ["threaten"])
        diplomacy.adjust_score("alien_patrol", 80)
        self.assertIn("aid", diplomacy.available_actions("alien_patrol"))


if __name__ == "__main__":
    unittest.main()
