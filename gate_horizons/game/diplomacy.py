"""Diplomacy model for faction relations and encounter outcomes."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict, List


@dataclass
class DiplomacyOutcome:
    action: str
    faction_id: str
    relation_delta: int
    resource_delta: Dict[str, int] = field(default_factory=dict)
    summary: str = ""


class DiplomacyManager:
    def __init__(self):
        self.relations: Dict[str, int] = {
            "pirates": -40,
            "alien_patrol": 0,
            "rogue_ai": -20,
        }
        self.faction_names = {
            "pirates": "Pirate Clans",
            "alien_patrol": "Alien Patrol",
            "rogue_ai": "Rogue AI",
        }

    def get_score(self, faction_id: str) -> int:
        return int(self.relations.get(faction_id, 0))

    def set_score(self, faction_id: str, score: int) -> None:
        self.relations[faction_id] = self._clamp(score)

    def adjust_score(self, faction_id: str, delta: int) -> int:
        new_score = self._clamp(self.get_score(faction_id) + delta)
        self.relations[faction_id] = new_score
        return new_score

    def get_tier(self, faction_id: str) -> str:
        score = self.get_score(faction_id)
        if score <= -25:
            return "hostile"
        if score >= 25:
            return "friendly"
        return "neutral"

    def available_actions(self, faction_id: str) -> List[str]:
        tier = self.get_tier(faction_id)
        if tier == "hostile":
            return ["threaten"]
        if tier == "friendly":
            return ["aid", "negotiate"]
        return ["negotiate", "aid", "threaten"]

    def resolve_action(self, faction_id: str, action: str) -> DiplomacyOutcome:
        action = (action or "").lower()
        if action == "aid":
            return DiplomacyOutcome(
                action=action,
                faction_id=faction_id,
                relation_delta=10,
                resource_delta={"credits": -10},
                summary="Aid sent. Relations improve, but it costs credits.",
            )
        if action == "threaten":
            return DiplomacyOutcome(
                action=action,
                faction_id=faction_id,
                relation_delta=-15,
                resource_delta={"credits": 5},
                summary="Threat issued. Relations sour, but the faction backs down and pays.",
            )
        return DiplomacyOutcome(
            action="negotiate",
            faction_id=faction_id,
            relation_delta=5,
            resource_delta={"intel": 1},
            summary="Negotiations conclude with a modest diplomatic gain.",
        )

    def to_dict(self) -> dict:
        return {
            "relations": dict(self.relations),
            "faction_names": dict(self.faction_names),
        }

    @classmethod
    def from_dict(cls, data: dict) -> "DiplomacyManager":
        manager = cls()
        manager.relations = dict(data.get("relations", manager.relations))
        manager.faction_names = dict(data.get("faction_names", manager.faction_names))
        return manager

    @staticmethod
    def _clamp(value: int) -> int:
        return max(-100, min(100, int(value)))
