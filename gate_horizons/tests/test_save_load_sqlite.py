import os
import tempfile
import unittest

from gate_horizons.game.save_load import SaveManager
from gate_horizons.game.state import GameState


class TestSaveManagerSQLite(unittest.TestCase):
    def _make_manager(self):
        temp_dir = tempfile.TemporaryDirectory()
        db_path = os.path.join(temp_dir.name, "saves", "test.db")
        return temp_dir, SaveManager(db_path)

    def test_save_load_roundtrip_sqlite(self):
        temp_dir, manager = self._make_manager()
        try:
            state = GameState.new_game()
            state.resources.add("metals", 10, system_id="sol")

            save_id = manager.save_game(state, "slot-1")
            loaded = manager.load_game(save_id, GameState)

            self.assertIsNotNone(loaded)
            self.assertEqual(state.turn_number, loaded.turn_number)
            self.assertEqual(
                state.resources.global_resources,
                loaded.resources.global_resources,
            )
        finally:
            temp_dir.cleanup()

    def test_save_update_list_and_delete(self):
        temp_dir, manager = self._make_manager()
        try:
            state = GameState.new_game()
            save_id = manager.save_game(state, "slot-1")

            state.process_turn()
            save_id_updated = manager.save_game(state, "slot-1")

            self.assertEqual(save_id, save_id_updated)

            saves = manager.list_saves()
            self.assertEqual(len(saves), 1)
            self.assertEqual(saves[0]["turn_number"], state.turn_number)

            deleted = manager.delete_save(save_id)
            self.assertTrue(deleted)
            self.assertEqual(manager.list_saves(), [])
        finally:
            temp_dir.cleanup()

    def test_load_by_name_returns_latest(self):
        temp_dir, manager = self._make_manager()
        try:
            state = GameState.new_game()
            manager.save_game(state, "slot-1")

            state.process_turn()
            manager.save_game(state, "slot-1")

            loaded = manager.load_by_name("slot-1", GameState)
            self.assertIsNotNone(loaded)
            self.assertEqual(loaded.turn_number, state.turn_number)
        finally:
            temp_dir.cleanup()


if __name__ == "__main__":
    unittest.main()
