"""Production system for Gate Horizons.

Manages resource extraction, factory processing, and component manufacturing.

Resource tiers:
  Tier 0 (raw): ore_iron, silicates, water_ice, gas_h2, gas_he3, organics, rare_metals
  Tier 1 (processed): metal_alloys, polymers, fuel, electronics
  Tier 2 (components): hull_segments, reactor_parts, habitat_modules, cargo_frames

Extraction sites produce raw resources per tick based on body type.
Factories consume inputs and produce outputs per recipe.
"""

from __future__ import annotations

import json
import uuid
from importlib.resources.abc import Traversable
from typing import Optional, Union


# All production resource IDs — these extend the legacy resource set
RAW_RESOURCES = [
    "ore_iron", "silicates", "water_ice", "gas_h2", "gas_he3",
    "organics", "rare_metals",
]
PROCESSED_RESOURCES = ["metal_alloys", "polymers", "fuel", "electronics"]
COMPONENT_RESOURCES = [
    "hull_segments", "reactor_parts", "habitat_modules", "cargo_frames",
]
ALL_PRODUCTION_RESOURCES = RAW_RESOURCES + PROCESSED_RESOURCES + COMPONENT_RESOURCES


class ProductionConfig:
    """Loads and holds all production configuration data."""

    def __init__(self):
        self.body_type_resources: dict = {}
        self.recipes: dict = {}
        self.orbital_facility_types: dict = {}
        self.ship_blueprints: dict = {}
        self.extraction_balance: dict = {}
        self.factory_balance: dict = {}
        self.fleet_ops_balance: dict = {}

    def load_from_json(self, filepath: Union[str, Traversable]) -> None:
        if hasattr(filepath, "read_text"):
            data = json.loads(filepath.read_text(encoding="utf-8"))
        else:
            with open(filepath, "r", encoding="utf-8") as f:
                data = json.load(f)

        self.body_type_resources = data.get("body_type_resources", {})
        self.recipes = data.get("recipes", {})
        self.orbital_facility_types = data.get("orbital_facility_types", {})
        self.ship_blueprints = data.get("ship_blueprints", {})
        self.extraction_balance = data.get("extraction_balance", {})
        self.factory_balance = data.get("factory_balance", {})
        self.fleet_ops_balance = data.get("fleet_ops_balance", {})

    def get_body_resources(self, body_type: str) -> dict:
        """Return resource availability for a body type.

        Returns dict of {resource_id: {base_yield, probability}}.
        """
        return dict(self.body_type_resources.get(body_type, {}))

    def get_recipe(self, recipe_id: str) -> Optional[dict]:
        return self.recipes.get(recipe_id)

    def get_all_recipes(self) -> dict:
        return dict(self.recipes)

    def get_blueprint(self, blueprint_id: str) -> Optional[dict]:
        return self.ship_blueprints.get(blueprint_id)

    def to_dict(self) -> dict:
        return {
            "body_type_resources": self.body_type_resources,
            "recipes": self.recipes,
            "orbital_facility_types": self.orbital_facility_types,
            "ship_blueprints": self.ship_blueprints,
            "extraction_balance": self.extraction_balance,
            "factory_balance": self.factory_balance,
            "fleet_ops_balance": self.fleet_ops_balance,
        }

    @classmethod
    def from_dict(cls, data: dict) -> "ProductionConfig":
        pc = cls()
        pc.body_type_resources = data.get("body_type_resources", {})
        pc.recipes = data.get("recipes", {})
        pc.orbital_facility_types = data.get("orbital_facility_types", {})
        pc.ship_blueprints = data.get("ship_blueprints", {})
        pc.extraction_balance = data.get("extraction_balance", {})
        pc.factory_balance = data.get("factory_balance", {})
        pc.fleet_ops_balance = data.get("fleet_ops_balance", {})
        return pc


def empty_production_inventory() -> dict:
    """Return a zeroed inventory for all production resources."""
    return {r: 0 for r in ALL_PRODUCTION_RESOURCES}


class ExtractionSite:
    """A mining/harvesting site that produces raw resources each tick."""

    def __init__(
        self,
        id: str = None,
        resource_id: str = "",
        base_yield: int = 1,
        level: int = 1,
        active: bool = True,
        building: bool = False,
        turns_remaining: int = 0,
    ):
        self.id = id or str(uuid.uuid4())[:8]
        self.resource_id = resource_id
        self.base_yield = base_yield
        self.level = level
        self.active = active
        self.building = building
        self.turns_remaining = turns_remaining

    def get_output_per_tick(self, mining_level: int = 0, tech_mult: float = 1.0) -> int:
        """Calculate extraction output per tick.

        Args:
            mining_level: Colony mining infrastructure level (adds 0.5 per level).
            tech_mult: Tech multiplier (e.g. advanced_mining = 1.5).
        """
        if not self.active or self.building:
            return 0
        bonus = 1.0 + mining_level * 0.5
        return max(1, int(self.base_yield * self.level * bonus * tech_mult))

    def process_tick(self, mining_level: int = 0, tech_mult: float = 1.0) -> tuple:
        """Process one tick. Returns (resource_id, amount) or (None, 0) if building."""
        if self.building:
            self.turns_remaining -= 1
            if self.turns_remaining <= 0:
                self.building = False
                self.turns_remaining = 0
            return None, 0

        if not self.active:
            return None, 0

        amount = self.get_output_per_tick(mining_level, tech_mult)
        return self.resource_id, amount

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "resource_id": self.resource_id,
            "base_yield": self.base_yield,
            "level": self.level,
            "active": self.active,
            "building": self.building,
            "turns_remaining": self.turns_remaining,
        }

    @classmethod
    def from_dict(cls, data: dict) -> "ExtractionSite":
        return cls(
            id=data.get("id"),
            resource_id=data.get("resource_id", ""),
            base_yield=data.get("base_yield", 1),
            level=data.get("level", 1),
            active=data.get("active", True),
            building=data.get("building", False),
            turns_remaining=data.get("turns_remaining", 0),
        )


class Factory:
    """A factory that runs recipes from a queue, consuming inputs and producing outputs."""

    def __init__(
        self,
        id: str = None,
        active: bool = True,
        building: bool = False,
        build_turns_remaining: int = 0,
        current_recipe: str = None,
        recipe_progress: int = 0,
        recipe_queue: list = None,
    ):
        self.id = id or str(uuid.uuid4())[:8]
        self.active = active
        self.building = building
        self.build_turns_remaining = build_turns_remaining
        self.current_recipe = current_recipe
        self.recipe_progress = recipe_progress
        self.recipe_queue = recipe_queue or []

    def queue_recipe(self, recipe_id: str, count: int = 1) -> None:
        """Add a recipe to the production queue."""
        for _ in range(count):
            self.recipe_queue.append(recipe_id)

    def clear_queue(self) -> None:
        self.recipe_queue.clear()
        self.current_recipe = None
        self.recipe_progress = 0

    def process_tick(self, inventory: dict, config: ProductionConfig) -> dict:
        """Process one tick of factory production.

        Returns dict of {resource_id: amount_produced}.

        Args:
            inventory: The local production inventory (modified in place for inputs).
            config: ProductionConfig for recipe lookup.
        """
        produced = {}

        if self.building:
            self.build_turns_remaining -= 1
            if self.build_turns_remaining <= 0:
                self.building = False
                self.build_turns_remaining = 0
            return produced

        if not self.active:
            return produced

        # Start next recipe from queue if idle
        if self.current_recipe is None and self.recipe_queue:
            self.current_recipe = self.recipe_queue.pop(0)
            self.recipe_progress = 0

        if self.current_recipe is None:
            return produced

        recipe = config.get_recipe(self.current_recipe)
        if not recipe:
            self.current_recipe = None
            self.recipe_progress = 0
            return produced

        # Check if we can start/continue (inputs consumed on first tick only)
        if self.recipe_progress == 0:
            # Try to consume inputs
            inputs = recipe.get("inputs", {})
            can_consume = all(
                inventory.get(res, 0) >= amount
                for res, amount in inputs.items()
            )
            if not can_consume:
                return produced  # Wait for inputs

            # Consume inputs
            for res, amount in inputs.items():
                inventory[res] = max(0, inventory.get(res, 0) - amount)

        self.recipe_progress += 1
        recipe_time = recipe.get("time", 1)

        if self.recipe_progress >= recipe_time:
            # Recipe complete — produce outputs
            for res, amount in recipe.get("outputs", {}).items():
                produced[res] = produced.get(res, 0) + amount

            self.current_recipe = None
            self.recipe_progress = 0

        return produced

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "active": self.active,
            "building": self.building,
            "build_turns_remaining": self.build_turns_remaining,
            "current_recipe": self.current_recipe,
            "recipe_progress": self.recipe_progress,
            "recipe_queue": list(self.recipe_queue),
        }

    @classmethod
    def from_dict(cls, data: dict) -> "Factory":
        return cls(
            id=data.get("id"),
            active=data.get("active", True),
            building=data.get("building", False),
            build_turns_remaining=data.get("build_turns_remaining", 0),
            current_recipe=data.get("current_recipe"),
            recipe_progress=data.get("recipe_progress", 0),
            recipe_queue=list(data.get("recipe_queue", [])),
        )


class ProductionManager:
    """Manages extraction and factory operations across all colonies."""

    def __init__(self, config: ProductionConfig = None):
        self.config = config or ProductionConfig()

    def process_extraction(
        self,
        extraction_sites: list,
        inventory: dict,
        mining_level: int = 0,
        tech_mult: float = 1.0,
    ) -> dict:
        """Process all extraction sites for one tick.

        Returns dict of {resource_id: total_amount_extracted}.
        """
        totals = {}
        for site in extraction_sites:
            resource_id, amount = site.process_tick(mining_level, tech_mult)
            if resource_id and amount > 0:
                inventory[resource_id] = inventory.get(resource_id, 0) + amount
                totals[resource_id] = totals.get(resource_id, 0) + amount
        return totals

    def process_factories(
        self,
        factories: list,
        inventory: dict,
    ) -> dict:
        """Process all factories for one tick.

        Returns dict of {resource_id: total_amount_produced}.
        """
        totals = {}
        for factory in factories:
            produced = factory.process_tick(inventory, self.config)
            for res, amount in produced.items():
                inventory[res] = inventory.get(res, 0) + amount
                totals[res] = totals.get(res, 0) + amount
        return totals

    def determine_extraction_resources(self, body_type: str, seed: int = 0) -> list:
        """Determine which resources a body can extract based on type.

        Uses deterministic selection based on seed (e.g. hash of planet_id).
        Returns list of {resource_id, base_yield}.
        """
        body_resources = self.config.get_body_resources(body_type)
        if not body_resources:
            return []

        available = []
        for resource_id, info in body_resources.items():
            # Use probability as deterministic threshold based on seed
            prob = info.get("probability", 0.5)
            base_yield = info.get("base_yield", 1)
            # Deterministic: use hash to decide availability
            resource_hash = hash((seed, resource_id)) % 1000
            if resource_hash < prob * 1000:
                available.append({
                    "resource_id": resource_id,
                    "base_yield": base_yield,
                })

        return available

    def to_dict(self) -> dict:
        return {"config": self.config.to_dict()}

    @classmethod
    def from_dict(cls, data: dict) -> "ProductionManager":
        config = ProductionConfig.from_dict(data.get("config", {}))
        return cls(config=config)
