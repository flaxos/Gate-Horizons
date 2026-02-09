import json
import os
import sqlite3
import tempfile
import unittest

from gate_horizons.game.save_load import SaveManager
from gate_horizons.game.state import GameState
from gate_horizons.sim.balance_constants import POPULATION_DEFAULT_BY_LEVEL


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

    def test_migrate_old_save_schema_and_population_defaults(self):
        temp_dir = tempfile.TemporaryDirectory()
        try:
            db_path = os.path.join(temp_dir.name, "saves", "legacy.db")
            os.makedirs(os.path.dirname(db_path), exist_ok=True)

            legacy_state = GameState.new_game()
            payload = legacy_state.to_dict()
            payload["schema_version"] = 10
            for colony in payload.get("colonies", {}).get("colonies", {}).values():
                colony.pop("population_units", None)
                colony["population"] = 50

            with sqlite3.connect(db_path) as conn:
                conn.execute(
                    """
                    CREATE TABLE saves (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        save_name TEXT NOT NULL,
                        timestamp TEXT NOT NULL,
                        turn_number INTEGER NOT NULL,
                        game_data TEXT NOT NULL,
                        thumbnail_data TEXT
                    )
                    """
                )
                conn.execute(
                    "INSERT INTO saves (save_name, timestamp, turn_number, game_data) VALUES (?, ?, ?, ?)",
                    ("legacy", "now", payload.get("turn_number", 0), json.dumps(payload)),
                )
                conn.commit()

            manager = SaveManager(db_path)
            loaded = manager.load_by_name("legacy", GameState)
            self.assertIsNotNone(loaded)
            for colony in loaded.colonies.colonies.values():
                default_pop = POPULATION_DEFAULT_BY_LEVEL.get(colony.level, 100)
                self.assertGreaterEqual(colony.population_units, default_pop)
        finally:
            temp_dir.cleanup()


if __name__ == "__main__":
    unittest.main()
