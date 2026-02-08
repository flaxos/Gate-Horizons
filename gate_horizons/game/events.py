"""Event engine for Gate Horizons."""

from __future__ import annotations

import json
import os
import random
from dataclasses import dataclass, field
from typing import Optional, Union

from .types import Traversable


@dataclass
class EventOutcome:
    event_id: str = ""
    choice_made: str = ""
    result: str = ""  # success, partial, failure
    description: str = ""
    rewards_applied: dict = field(default_factory=dict)
    costs_applied: dict = field(default_factory=dict)

    def to_dict(self) -> dict:
        return {
            "event_id": self.event_id,
            "choice_made": self.choice_made,
            "result": self.result,
            "description": self.description,
            "rewards_applied": dict(self.rewards_applied),
            "costs_applied": dict(self.costs_applied),
        }


class Event:
    def __init__(
        self,
        id: str,
        title: str,
        description: str = "",
        requirements: dict = None,
        choices: list = None,
        tags: list = None,
        tier_requirement: int = 0,
        one_time: bool = True,
    ):
        self.id = id
        self.title = title
        self.description = description
        self.requirements = requirements or {}
        self.choices = choices or []
        self.tags = tags or []
        self.tier_requirement = tier_requirement
        self.one_time = one_time

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "title": self.title,
            "description": self.description,
            "requirements": dict(self.requirements),
            "choices": list(self.choices),
            "tags": list(self.tags),
            "tier_requirement": self.tier_requirement,
            "one_time": self.one_time,
        }

    @classmethod
    def from_dict(cls, data: dict) -> "Event":
        return cls(**{k: v for k, v in data.items() if k in (
            "id", "title", "description", "requirements", "choices",
            "tags", "tier_requirement", "one_time"
        )})


class EventEngine:
    def __init__(self):
        self.available_events: list[Event] = []
        self.triggered_events: list[str] = []  # IDs of one-time events already triggered
        self.event_queue: list[Event] = []  # Events waiting for player resolution

    def load_events(self, directory: Union[str, Traversable]) -> None:
        """Load all event JSON files from a directory."""
        if directory is None:
            return

        if hasattr(directory, "iterdir"):
            entries = [entry for entry in directory.iterdir() if entry.name.endswith(".json")]
        else:
            if not os.path.exists(directory):
                return
            entries = [
                os.path.join(directory, filename)
                for filename in os.listdir(directory)
                if filename.endswith(".json")
            ]

        for entry in entries:
            try:
                if hasattr(entry, "open"):
                    with entry.open("r", encoding="utf-8") as f:
                        data = json.load(f)
                else:
                    with open(entry, "r", encoding="utf-8") as f:
                        data = json.load(f)

                # Handle wrapped format (e.g. {"exploration_events": [...]})
                if isinstance(data, dict):
                    for key, value in data.items():
                        if isinstance(value, list):
                            data = value
                            break

                if isinstance(data, list):
                    for event_data in data:
                        self.available_events.append(Event.from_dict(event_data))
                elif isinstance(data, dict):
                    self.available_events.append(Event.from_dict(data))
            except (json.JSONDecodeError, KeyError):
                continue

    def check_triggers(self, game_state) -> list:
        """Evaluate which events can fire this turn. Returns 0-3 events."""
        eligible = []

        for event in self.available_events:
            # Skip already triggered one-time events
            if event.one_time and event.id in self.triggered_events:
                continue

            # Check requirements
            if self._meets_requirements(event, game_state):
                eligible.append(event)

        if not eligible:
            return []

        # Select 0-3 events weighted by relevance
        num_events = min(len(eligible), random.choices([0, 1, 2, 3], weights=[0.3, 0.4, 0.2, 0.1])[0])
        if num_events == 0:
            return []

        selected = random.sample(eligible, min(num_events, len(eligible)))
        for event in selected:
            # Mark one-time events as triggered immediately so they cannot
            # re-fire on subsequent turns even if the player hasn't resolved them.
            if event.one_time:
                self.triggered_events.append(event.id)
        self.event_queue.extend(selected)
        return selected

    def _meets_requirements(self, event: Event, game_state) -> bool:
        """Check if event requirements are met."""
        reqs = event.requirements

        # Check ship class requirement
        if "ship_class" in reqs:
            required_class = reqs["ship_class"]
            has_class = any(
                s.ship_class == required_class
                for s in game_state.fleet.ships.values()
            )
            if not has_class:
                return False

        # Check system surveyed requirement
        if "system_surveyed" in reqs:
            required_surveyed = reqs["system_surveyed"]
            # Check if any ship is at an unsurveyed/surveyed system as required
            found = False
            for ship in game_state.fleet.ships.values():
                system = game_state.galaxy.systems.get(ship.location)
                if system and system.surveyed == required_surveyed:
                    found = True
                    break
            if not found:
                return False

        # Check tier requirement
        if event.tier_requirement > 0:
            # Must have ships at systems of the required tier or higher
            has_tier = False
            for ship in game_state.fleet.ships.values():
                system = game_state.galaxy.systems.get(ship.location)
                if system and system.tier >= event.tier_requirement:
                    has_tier = True
                    break
            if not has_tier:
                return False

        return True

    def resolve_event(self, event_id: str, choice_index: int, game_state=None) -> Optional[EventOutcome]:
        """Resolve an event with a player choice."""
        # Find the event
        event = None
        for e in self.event_queue:
            if e.id == event_id:
                event = e
                break

        if not event or choice_index >= len(event.choices):
            return None

        choice = event.choices[choice_index]
        outcomes = choice.get("outcomes", [])

        if not outcomes:
            return None

        # Roll against outcome probabilities
        roll = random.random()
        cumulative = 0.0
        selected_outcome = outcomes[-1]  # Default to last outcome

        for outcome in outcomes:
            cumulative += outcome.get("probability", 0)
            if roll < cumulative:
                selected_outcome = outcome
                break

        # Apply rewards and costs
        result = EventOutcome(
            event_id=event_id,
            choice_made=choice.get("text", ""),
            result=selected_outcome.get("result", "success"),
            description=selected_outcome.get("description", ""),
        )

        # Apply rewards to game state
        rewards = selected_outcome.get("rewards", {})
        if game_state and rewards:
            for resource, amount in rewards.items():
                game_state.resources.add(resource, amount)
            result.rewards_applied = dict(rewards)

        # Apply costs to game state
        costs = selected_outcome.get("costs", {})
        if game_state and costs:
            applied_costs = {}
            for cost_type, amount in costs.items():
                if cost_type == "hull_damage":
                    # Apply hull damage to a random ship
                    ships = list(game_state.fleet.ships.values())
                    if ships:
                        target = random.choice(ships)
                        actual = min(target.hull, amount)
                        target.hull = max(0, target.hull - amount)
                        if actual > 0:
                            applied_costs[cost_type] = actual
                elif cost_type == "fuel_cost":
                    ships = list(game_state.fleet.ships.values())
                    if ships:
                        target = random.choice(ships)
                        actual = min(target.fuel, amount)
                        target.fuel = max(0, target.fuel - amount)
                        if actual > 0:
                            applied_costs[cost_type] = actual
                elif cost_type in ("energy", "metals", "exotics", "credits", "intel"):
                    actual = game_state.resources.spend_and_return_actual(cost_type, amount)
                    if actual > 0:
                        applied_costs[cost_type] = actual
            result.costs_applied = applied_costs

        # Mark as triggered (may already be marked from check_triggers)
        if event.one_time and event_id not in self.triggered_events:
            self.triggered_events.append(event_id)

        # Remove from queue
        self.event_queue = [e for e in self.event_queue if e.id != event_id]

        return result

    def select_event_by_tags(self, tags: list, game_state=None) -> Optional[Event]:
        """Select a random event matching tags and requirements.

        Adds the selected event to the queue and returns it.
        """
        if not tags:
            return None

        eligible = []
        tag_set = set(tags)
        for event in self.available_events:
            if event.one_time and event.id in self.triggered_events:
                continue
            if not event.tags or not tag_set.intersection(event.tags):
                continue
            if game_state and not self._meets_requirements(event, game_state):
                continue
            eligible.append(event)

        if not eligible:
            return None

        selected = random.choice(eligible)
        if selected.one_time:
            self.triggered_events.append(selected.id)
        self.event_queue.append(selected)
        return selected

    def get_pending_events(self) -> list:
        return list(self.event_queue)

    def clear_queue(self) -> None:
        self.event_queue.clear()

    def to_dict(self) -> dict:
        return {
            "triggered_events": list(self.triggered_events),
            "event_queue": [e.to_dict() for e in self.event_queue],
        }

    @classmethod
    def from_dict(cls, data: dict, events_directory: Union[str, Traversable] = None) -> "EventEngine":
        ee = cls()
        if events_directory:
            ee.load_events(events_directory)
        ee.triggered_events = data.get("triggered_events", [])
        ee.event_queue = [Event.from_dict(e) for e in data.get("event_queue", [])]
        return ee
