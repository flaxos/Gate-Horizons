"""SQLite schema migrations for saves."""

from __future__ import annotations

import json
import sqlite3


def _ensure_column(conn: sqlite3.Connection, table: str, column: str, definition: str) -> None:
    columns = {row[1] for row in conn.execute(f"PRAGMA table_info({table})").fetchall()}
    if column in columns:
        return
    conn.execute(f"ALTER TABLE {table} ADD COLUMN {column} {definition}")


def migrate_save_schema(conn: sqlite3.Connection) -> None:
    """Ensure schema_version column exists and backfill values from game_data."""
    _ensure_column(conn, "saves", "schema_version", "INTEGER NOT NULL DEFAULT 0")

    rows = conn.execute(
        "SELECT id, schema_version, game_data FROM saves WHERE schema_version = 0"
    ).fetchall()

    for save_id, schema_version, game_data in rows:
        if schema_version:
            continue
        try:
            payload = json.loads(game_data) if game_data else {}
        except (TypeError, json.JSONDecodeError):
            payload = {}
        version = int(payload.get("schema_version", 0) or 0)
        conn.execute(
            "UPDATE saves SET schema_version = ? WHERE id = ?",
            (version, save_id),
        )

    conn.commit()
