"""Game clock utilities for turn processing."""

from __future__ import annotations


GLOBAL_ENTITY_KEY = "__global__"


class GameClock:
    def __init__(self, current_tick: int = 0, turn_number: int = 0):
        self.current_tick = current_tick
        self.turn_number = turn_number
        self.last_processed_tick: dict[str, dict[str, int]] = {}

    def advance_turn(self) -> int:
        """Advance the clock by one tick/turn and return the new tick."""
        self.current_tick += 1
        self.turn_number += 1
        return self.current_tick

    def _entity_key(self, entity_id: str | None) -> str:
        return entity_id or GLOBAL_ENTITY_KEY

    def get_last_processed(self, subsystem: str, entity_id: str | None = None) -> int | None:
        subsystem_map = self.last_processed_tick.get(subsystem, {})
        return subsystem_map.get(self._entity_key(entity_id))

    def is_processed(self, subsystem: str, entity_id: str | None = None) -> bool:
        last_tick = self.get_last_processed(subsystem, entity_id)
        return last_tick == self.current_tick

    def mark_processed(self, subsystem: str, entity_id: str | None = None) -> bool:
        """Mark subsystem/entity processed for current tick.

        Returns True if marking succeeded, False if already processed.
        """
        if self.is_processed(subsystem, entity_id):
            return False
        subsystem_map = self.last_processed_tick.setdefault(subsystem, {})
        subsystem_map[self._entity_key(entity_id)] = self.current_tick
        return True

    def to_dict(self) -> dict:
        return {
            "current_tick": self.current_tick,
            "turn_number": self.turn_number,
            "last_processed_tick": {
                subsystem: dict(entries)
                for subsystem, entries in self.last_processed_tick.items()
            },
        }

    @classmethod
    def from_dict(cls, data: dict) -> "GameClock":
        clock = cls(
            current_tick=data.get("current_tick", 0),
            turn_number=data.get("turn_number", 0),
        )
        clock.last_processed_tick = {
            subsystem: dict(entries)
            for subsystem, entries in data.get("last_processed_tick", {}).items()
        }
        return clock
