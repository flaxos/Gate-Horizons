"""Tech tree system for Gate Horizons."""

import json
from typing import Optional


class TechNode:
    def __init__(
        self,
        id: str,
        name: str,
        description: str = "",
        cost: dict = None,
        effect: dict = None,
        prerequisites: list = None,
        branch: str = "",
        tier: str = "",
        researched: bool = False,
        researching: bool = False,
        turns_remaining: int = 0,
    ):
        self.id = id
        self.name = name
        self.description = description
        self.cost = cost or {}
        self.effect = effect or {}
        self.prerequisites = prerequisites or []
        self.branch = branch
        self.tier = tier
        self.researched = researched
        self.researching = researching
        self.turns_remaining = turns_remaining

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "name": self.name,
            "description": self.description,
            "cost": dict(self.cost),
            "effect": dict(self.effect),
            "prerequisites": list(self.prerequisites),
            "branch": self.branch,
            "tier": self.tier,
            "researched": self.researched,
            "researching": self.researching,
            "turns_remaining": self.turns_remaining,
        }

    @classmethod
    def from_dict(cls, data: dict) -> "TechNode":
        return cls(**data)


class TechTree:
    def __init__(self):
        self.techs: dict[str, TechNode] = {}
        self.active_research: str = None  # Currently researching tech ID

    def load_from_json(self, filepath: str) -> None:
        with open(filepath, "r") as f:
            data = json.load(f)

        self.techs.clear()
        for branch_name, tiers in data.items():
            for tier_name, techs in tiers.items():
                for tech_id, tech_data in techs.items():
                    node = TechNode(
                        id=tech_id,
                        name=tech_data["name"],
                        description=tech_data.get("description", ""),
                        cost=tech_data.get("cost", {}),
                        effect=tech_data.get("effect", {}),
                        prerequisites=tech_data.get("prerequisites", []),
                        branch=branch_name,
                        tier=tier_name,
                    )
                    self.techs[tech_id] = node

    def can_research(self, tech_id: str) -> bool:
        """Check if a tech can be researched (prerequisites met, not already done)."""
        tech = self.techs.get(tech_id)
        if not tech or tech.researched or tech.researching:
            return False

        # Check prerequisites
        for prereq_id in tech.prerequisites:
            prereq = self.techs.get(prereq_id)
            if not prereq or not prereq.researched:
                return False

        return True

    def start_research(self, tech_id: str, resources=None) -> bool:
        """Begin researching a tech. Costs intel upfront."""
        if not self.can_research(tech_id):
            return False

        tech = self.techs[tech_id]

        # Check and spend intel cost
        intel_cost = tech.cost.get("intel", 0)
        if resources:
            resource_cost = {k: v for k, v in tech.cost.items() if k != "turns"}
            if not resources.can_afford(resource_cost):
                return False
            resources.spend_dict(resource_cost)

        # Cancel any current research
        if self.active_research:
            current = self.techs.get(self.active_research)
            if current:
                current.researching = False
                current.turns_remaining = 0

        tech.researching = True
        tech.turns_remaining = tech.cost.get("turns", 3)
        self.active_research = tech_id
        return True

    def process_turn(self) -> Optional[str]:
        """Advance research by one turn. Returns completed tech ID or None."""
        if not self.active_research:
            return None

        tech = self.techs.get(self.active_research)
        if not tech or not tech.researching:
            self.active_research = None
            return None

        tech.turns_remaining -= 1
        if tech.turns_remaining <= 0:
            tech.researched = True
            tech.researching = False
            tech.turns_remaining = 0
            completed = self.active_research
            self.active_research = None
            return completed

        return None

    def get_available_techs(self) -> list:
        """Get all techs that can currently be researched."""
        return [t for t in self.techs.values() if self.can_research(t.id)]

    def get_researched_techs(self) -> list:
        """Get all completed techs."""
        return [t for t in self.techs.values() if t.researched]

    def get_effects(self) -> dict:
        """Get combined effects of all researched techs."""
        effects = {}
        for tech in self.techs.values():
            if tech.researched:
                for key, value in tech.effect.items():
                    if isinstance(value, (int, float)):
                        effects[key] = effects.get(key, 0) + value
                    elif isinstance(value, bool):
                        effects[key] = value
                    elif isinstance(value, dict):
                        if key not in effects:
                            effects[key] = {}
                        effects[key].update(value)
        return effects

    def get_branch_techs(self, branch: str) -> list:
        """Get all techs in a branch, ordered by tier."""
        branch_techs = [t for t in self.techs.values() if t.branch == branch]
        return sorted(branch_techs, key=lambda t: t.tier)

    def to_dict(self) -> dict:
        return {
            "techs": {tid: t.to_dict() for tid, t in self.techs.items()},
            "active_research": self.active_research,
        }

    @classmethod
    def from_dict(cls, data: dict) -> "TechTree":
        tt = cls()
        for tid, tdata in data.get("techs", {}).items():
            tt.techs[tid] = TechNode.from_dict(tdata)
        tt.active_research = data.get("active_research")
        return tt
