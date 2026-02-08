"""Mission system for short-term goals in Gate Horizons."""

from __future__ import annotations

from dataclasses import dataclass
from uuid import uuid4
import random


MISSION_TEMPLATES = [
    {
        "category": "exploration",
        "title": "Chart the Frontier",
        "description": "Discover 1 new star system.",
        "requirement": {"metric": "discoveries", "target": 1},
        "reward": {"credits": 25, "intel": 2},
    },
    {
        "category": "trade",
        "title": "Open Trade Lanes",
        "description": "Execute 1 trade transfer this turn.",
        "requirement": {"metric": "trade_transfers", "target": 1},
        "reward": {"credits": 30, "energy": 10},
    },
    {
        "category": "build",
        "title": "Expand the Colonies",
        "description": "Complete 1 construction project.",
        "requirement": {"metric": "construction_completed", "target": 1},
        "reward": {"metals": 15, "credits": 20},
    },
    {
        "category": "combat",
        "title": "Secure the Lanes",
        "description": "Win 1 combat encounter.",
        "requirement": {"metric": "combat_victories", "target": 1},
        "reward": {"metals": 10, "credits": 30, "intel": 1},
    },
]


@dataclass
class Mission:
    id: str
    category: str
    title: str
    description: str
    requirement: dict
    reward: dict
    progress: int = 0
    status: str = "active"
    created_turn: int = 0

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "category": self.category,
            "title": self.title,
            "description": self.description,
            "requirement": dict(self.requirement),
            "reward": dict(self.reward),
            "progress": self.progress,
            "status": self.status,
            "created_turn": self.created_turn,
        }

    @classmethod
    def from_dict(cls, data: dict) -> "Mission":
        return cls(
            id=data.get("id", uuid4().hex[:8]),
            category=data.get("category", "unknown"),
            title=data.get("title", "Untitled Mission"),
            description=data.get("description", ""),
            requirement=dict(data.get("requirement", {})),
            reward=dict(data.get("reward", {})),
            progress=int(data.get("progress", 0)),
            status=data.get("status", "active"),
            created_turn=int(data.get("created_turn", 0)),
        )

    def progress_summary(self) -> str:
        target = int(self.requirement.get("target", 0))
        return f"{self.progress}/{target}" if target > 0 else ""


class MissionManager:
    def __init__(self):
        self.active_missions: list[Mission] = []
        self.completed_missions: list[Mission] = []
        self.max_active: int = 3

    def generate_turn_mission(self, game_state) -> list[Mission]:
        """Generate a new mission if there is capacity."""
        if len(self.active_missions) >= self.max_active:
            return []

        template = self._pick_template()
        mission = self._create_mission(template, game_state.turn_number)
        self.active_missions.append(mission)
        return [mission]

    def check_completions(self, game_state, report) -> list[Mission]:
        """Update progress and resolve completed missions."""
        completed = []
        for mission in list(self.active_missions):
            self._advance_progress(mission, report)
            if mission.progress >= int(mission.requirement.get("target", 0)):
                mission.status = "completed"
                self._apply_reward(game_state, mission)
                self.active_missions.remove(mission)
                self.completed_missions.append(mission)
                completed.append(mission)
        return completed

    def _pick_template(self) -> dict:
        active_categories = {m.category for m in self.active_missions}
        available = [t for t in MISSION_TEMPLATES if t["category"] not in active_categories]
        if not available:
            available = list(MISSION_TEMPLATES)
        return random.choice(available)

    def _create_mission(self, template: dict, created_turn: int) -> Mission:
        return Mission(
            id=uuid4().hex[:8],
            category=template["category"],
            title=template["title"],
            description=template["description"],
            requirement=dict(template["requirement"]),
            reward=dict(template["reward"]),
            created_turn=created_turn,
        )

    def _advance_progress(self, mission: Mission, report) -> None:
        metric = mission.requirement.get("metric")
        progress_gain = 0

        if metric == "discoveries":
            progress_gain = sum(
                1 for discovery in report.discoveries if str(discovery).startswith("Discovered")
            )
        elif metric == "trade_transfers":
            progress_gain = sum(
                1 for trade in report.trade_reports if trade.get("transferred")
            )
            if progress_gain == 0:
                progress_gain = sum(
                    1 for shipment in report.logistics_shipments if shipment.get("shipped")
                )
        elif metric == "construction_completed":
            progress_gain = len(report.construction_completed)
        elif metric == "combat_victories":
            for encounter in report.combat_encounters:
                if hasattr(encounter, "victory"):
                    if encounter.victory:
                        progress_gain += 1
                elif isinstance(encounter, dict):
                    if encounter.get("victory") is True or encounter.get("outcome") == "victory":
                        progress_gain += 1

        mission.progress += progress_gain

    def _apply_reward(self, game_state, mission: Mission) -> None:
        if not hasattr(game_state, "resources"):
            return
        for resource, amount in mission.reward.items():
            game_state.resources.add(resource, amount)

    def to_dict(self) -> dict:
        return {
            "active_missions": [m.to_dict() for m in self.active_missions],
            "completed_missions": [m.to_dict() for m in self.completed_missions],
            "max_active": self.max_active,
        }

    @classmethod
    def from_dict(cls, data: dict) -> "MissionManager":
        manager = cls()
        manager.active_missions = [
            Mission.from_dict(m) for m in data.get("active_missions", [])
        ]
        manager.completed_missions = [
            Mission.from_dict(m) for m in data.get("completed_missions", [])
        ]
        manager.max_active = int(data.get("max_active", manager.max_active))
        return manager
