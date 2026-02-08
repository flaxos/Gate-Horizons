"""Save/Load system using SQLite for Gate Horizons."""

import json
import os
import sqlite3
from datetime import datetime
from typing import Optional


class SaveManager:
    def __init__(self, db_path: str = "saves.db"):
        self.db_path = db_path
        self._init_db()

    def _init_db(self) -> None:
        db_dir = os.path.dirname(os.path.abspath(self.db_path))
        if db_dir and not os.path.exists(db_dir):
            os.makedirs(db_dir, exist_ok=True)
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS saves (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    save_name TEXT NOT NULL,
                    timestamp TEXT NOT NULL,
                    turn_number INTEGER NOT NULL,
                    game_data TEXT NOT NULL,
                    thumbnail_data TEXT
                )
            """)
            columns = {
                row[1] for row in conn.execute("PRAGMA table_info(saves)").fetchall()
            }
            migrations = {
                "save_name": "TEXT NOT NULL DEFAULT ''",
                "timestamp": "TEXT NOT NULL DEFAULT ''",
                "turn_number": "INTEGER NOT NULL DEFAULT 0",
                "game_data": "TEXT NOT NULL DEFAULT '{}'",
                "thumbnail_data": "TEXT",
            }
            for column, definition in migrations.items():
                if column not in columns:
                    conn.execute(f"ALTER TABLE saves ADD COLUMN {column} {definition}")
            conn.commit()

    def save_game(self, game_state, save_name: str) -> int:
        """Save game state. Returns save ID."""
        game_data = json.dumps(game_state.to_dict())
        timestamp = datetime.now().isoformat()
        turn_number = game_state.turn_number

        with sqlite3.connect(self.db_path) as conn:
            # Check if save with this name exists
            existing = conn.execute(
                "SELECT id FROM saves WHERE save_name = ?",
                (save_name,)
            ).fetchone()

            if existing:
                conn.execute(
                    "UPDATE saves SET timestamp = ?, turn_number = ?, game_data = ? WHERE save_name = ?",
                    (timestamp, turn_number, game_data, save_name)
                )
                save_id = existing[0]
            else:
                cursor = conn.execute(
                    "INSERT INTO saves (save_name, timestamp, turn_number, game_data) VALUES (?, ?, ?, ?)",
                    (save_name, timestamp, turn_number, game_data)
                )
                save_id = cursor.lastrowid

            conn.commit()
            return save_id

    def load_game(self, save_id: int, game_state_class=None):
        """Load game state from save ID."""
        with sqlite3.connect(self.db_path) as conn:
            row = conn.execute(
                "SELECT game_data FROM saves WHERE id = ?",
                (save_id,)
            ).fetchone()

        if not row or not row[0]:
            return None

        try:
            data = json.loads(row[0])
        except (TypeError, json.JSONDecodeError):
            return None
        if game_state_class:
            return game_state_class.from_dict(data)
        return data

    def load_by_name(self, save_name: str, game_state_class=None):
        """Load game state by save name."""
        with sqlite3.connect(self.db_path) as conn:
            row = conn.execute(
                "SELECT game_data FROM saves WHERE save_name = ? ORDER BY timestamp DESC LIMIT 1",
                (save_name,)
            ).fetchone()

        if not row or not row[0]:
            return None

        try:
            data = json.loads(row[0])
        except (TypeError, json.JSONDecodeError):
            return None
        if game_state_class:
            return game_state_class.from_dict(data)
        return data

    def list_saves(self) -> list:
        """List all saves with metadata."""
        with sqlite3.connect(self.db_path) as conn:
            rows = conn.execute(
                "SELECT id, save_name, timestamp, turn_number FROM saves ORDER BY timestamp DESC"
            ).fetchall()

        return [
            {
                "id": row[0],
                "save_name": row[1],
                "timestamp": row[2],
                "turn_number": row[3],
            }
            for row in rows
        ]

    def delete_save(self, save_id: int) -> bool:
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("DELETE FROM saves WHERE id = ?", (save_id,))
            conn.commit()
            return conn.total_changes > 0

    def auto_save(self, game_state) -> int:
        """Save to the autosave slot."""
        return self.save_game(game_state, "autosave")
