"""Production system for Gate Horizons.

Manages resource extraction, factory processing, and component manufacturing.

Resource tiers:
  Tier 0 (raw): ore_iron, silicates, water_ice, gas_h2, gas_he3, organics, rare_metals
  Tier 1 (processed): metal_alloys, polymers, fuel, electronics
  Tier 2 (components): hull_plating, drive_assemblies, avionics, hab_modules, cargo_frames

Extraction sites produce raw resources per tick based on body type.
Factories consume inputs and produce outputs per recipe.
"""

from __future__ import annotations

import hashlib
import json
import uuid
from typing import Optional, Union

from .types import Traversable


# All production resource IDs — these extend the legacy resource set
RAW_RESOURCES = [
    "ore_iron", "silicates", "water_ice", "fissiles",
    "gas_h2", "gas_he3", "gas_d2", "volatiles",
    "organics", "rare_metals", "exotics",
]
PROCESSED_RESOURCES = ["metal_alloys", "polymers", "fuel", "electronics"]
COMPONENT_RESOURCES = [
    "hull_plating", "drive_assemblies", "avionics", "hab_modules", "cargo_frames",
]
ALL_PRODUCTION_RESOURCES = RAW_RESOURCES + PROCESSED_RESOURCES + COMPONENT_RESOURCES


class ProductionConfig:
    """Loads and holds all production configuration data."""

    def __init__(self):
        self.resource_definitions: dict = {}
        self.body_type_resources: dict = {}
        self.world_types: dict = {}
        self.planet_type_map: dict = {}
        self.classic_resource_aliases: dict = {}
        self.production_storage: dict = {}
        self.recipes: dict = {}
        self.orbital_facility_types: dict = {}
        self.ship_blueprints: dict = {}
        self.extraction_balance: dict = {}
        self.factory_balance: dict = {}
        self.shipyard_balance: dict = {}
        self.fleet_ops_balance: dict = {}

    def load_from_json(self, filepath: Union[str, Traversable]) -> None:
        if hasattr(filepath, "read_text"):
            data = json.loads(filepath.read_text(encoding="utf-8"))
        else:
            with open(filepath, "r", encoding="utf-8") as f:
                data = json.load(f)

        self.resource_definitions = data.get("resource_definitions", {})
        self.body_type_resources = data.get("body_type_resources", {})
        self.world_types = data.get("world_types", {})
        self.planet_type_map = data.get("planet_type_map", {})
        self.classic_resource_aliases = data.get("classic_resource_aliases", {})
        self.production_storage = data.get("production_storage", {})
        self.recipes = data.get("recipes", {})
        self.orbital_facility_types = data.get("orbital_facility_types", {})
        self.ship_blueprints = data.get("ship_blueprints", {})
        self.extraction_balance = data.get("extraction_balance", {})
        self.factory_balance = data.get("factory_balance", {})
        self.shipyard_balance = data.get("shipyard_balance", {})
        self.fleet_ops_balance = data.get("fleet_ops_balance", {})

    def get_world_type(self, body_type: str) -> str:
        """Resolve planet body type to a production world type."""
        if body_type in self.world_types:
            return body_type
        if body_type in self.planet_type_map:
            return self.planet_type_map[body_type]
        return "terrestrial"

    def get_body_resources(self, body_type: str) -> dict:
        """Return resource availability for a body type.

        Returns dict of {resource_id: {base_yield, probability}}.
        """
        if self.world_types:
            world_type = self.get_world_type(body_type)
            return dict(self.world_types.get(world_type, {}))
        return dict(self.body_type_resources.get(body_type, {}))

    def get_recipe(self, recipe_id: str) -> Optional[dict]:
        return self.recipes.get(recipe_id)

    def get_all_recipes(self) -> dict:
        return dict(self.recipes)

    def get_blueprint(self, blueprint_id: str) -> Optional[dict]:
        return self.ship_blueprints.get(blueprint_id)

    def get_resource_tier(self, resource_id: str) -> str:
        definition = self.resource_definitions.get(resource_id)
        if definition and definition.get("tier"):
            return definition["tier"]
        if resource_id in RAW_RESOURCES:
            return "raw"
        if resource_id in PROCESSED_RESOURCES:
            return "processed"
        if resource_id in COMPONENT_RESOURCES:
            return "components"
        return "raw"

    def to_dict(self) -> dict:
        return {
            "resource_definitions": self.resource_definitions,
            "body_type_resources": self.body_type_resources,
            "world_types": self.world_types,
            "planet_type_map": self.planet_type_map,
            "classic_resource_aliases": self.classic_resource_aliases,
            "production_storage": self.production_storage,
            "recipes": self.recipes,
            "orbital_facility_types": self.orbital_facility_types,
            "ship_blueprints": self.ship_blueprints,
            "extraction_balance": self.extraction_balance,
            "factory_balance": self.factory_balance,
            "shipyard_balance": self.shipyard_balance,
            "fleet_ops_balance": self.fleet_ops_balance,
        }

    @classmethod
    def from_dict(cls, data: dict) -> "ProductionConfig":
        pc = cls()
        pc.resource_definitions = data.get("resource_definitions", {})
        pc.body_type_resources = data.get("body_type_resources", {})
        pc.world_types = data.get("world_types", {})
        pc.planet_type_map = data.get("planet_type_map", {})
        pc.classic_resource_aliases = data.get("classic_resource_aliases", {})
        pc.production_storage = data.get("production_storage", {})
        pc.recipes = data.get("recipes", {})
        pc.orbital_facility_types = data.get("orbital_facility_types", {})
        pc.ship_blueprints = data.get("ship_blueprints", {})
        pc.extraction_balance = data.get("extraction_balance", {})
        pc.factory_balance = data.get("factory_balance", {})
        pc.shipyard_balance = data.get("shipyard_balance", {})
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

    def process_tick(
        self,
        inventory: dict,
        config: ProductionConfig,
        industry_level: int = 0,
        colony_level: int = 0,
    ) -> dict:
        """Process one tick of factory production.

        Returns dict of {resource_id: amount_produced}.

        Args:
            inventory: The local production inventory (modified in place for inputs).
            config: ProductionConfig for recipe lookup.
            industry_level: Colony industry infrastructure level.
            colony_level: Colony level for recipe prerequisites.
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

        min_industry = recipe.get("min_industry_level", 0)
        min_colony = recipe.get("min_colony_level", 0)
        if industry_level < min_industry or colony_level < min_colony:
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
        storage_caps: Optional[dict] = None,
    ) -> dict:
        """Process all extraction sites for one tick.

        Returns dict of {resource_id: total_amount_extracted}.
        """
        totals = {}
        for site in extraction_sites:
            resource_id, amount = site.process_tick(mining_level, tech_mult)
            if resource_id and amount > 0:
                amount = self._apply_storage_caps(inventory, resource_id, amount, storage_caps)
                if amount <= 0:
                    continue
                inventory[resource_id] = inventory.get(resource_id, 0) + amount
                totals[resource_id] = totals.get(resource_id, 0) + amount
        return totals

    def process_factories(
        self,
        factories: list,
        inventory: dict,
        throughput_cap: Optional[int] = None,
        industry_level: int = 0,
        colony_level: int = 0,
        storage_caps: Optional[dict] = None,
    ) -> dict:
        """Process all factories for one tick.

        Returns dict of {resource_id: total_amount_produced}.
        """
        totals = {}
        processed = 0
        for factory in factories:
            if throughput_cap is not None and processed >= throughput_cap:
                break
            has_work = factory.current_recipe is not None or bool(factory.recipe_queue)
            eligible = factory.active and not factory.building and has_work
            produced = factory.process_tick(
                inventory, self.config, industry_level=industry_level, colony_level=colony_level,
            )
            if eligible:
                processed += 1
            for res, amount in produced.items():
                amount = self._apply_storage_caps(inventory, res, amount, storage_caps)
                if amount <= 0:
                    continue
                inventory[res] = inventory.get(res, 0) + amount
                totals[res] = totals.get(res, 0) + amount
        return totals

    def _apply_storage_caps(
        self,
        inventory: dict,
        resource_id: str,
        amount: int,
        storage_caps: Optional[dict],
    ) -> int:
        if not storage_caps:
            return amount
        cap = storage_caps.get(resource_id)
        if cap is None:
            return amount
        available = max(0, cap - inventory.get(resource_id, 0))
        return min(amount, available)

    def get_factory_throughput(self, colony) -> int:
        balance = self.config.factory_balance
        base = balance.get("base_throughput", 1)
        per_colony = balance.get("throughput_per_colony_level", 1)
        per_industry = balance.get("throughput_per_industry_level", 1)
        industry_level = colony.infrastructure.get("industry", {}).get("level", 0)
        return max(0, int(base + colony.level * per_colony + industry_level * per_industry))

    def get_storage_caps(self, colony) -> dict:
        storage = self.config.production_storage
        base_caps = storage.get("base_caps", {"raw": 120, "processed": 80, "components": 40})
        colony_mult = storage.get("colony_level_mult", 0.25)
        industry_mult = storage.get("industry_level_mult", 0.2)
        min_cap = storage.get("min_cap", 20)

        level_factor = 1 + colony.level * colony_mult
        industry_level = colony.infrastructure.get("industry", {}).get("level", 0)
        industry_factor = 1 + industry_level * industry_mult

        caps = {}
        for resource_id in ALL_PRODUCTION_RESOURCES:
            tier = self.config.get_resource_tier(resource_id)
            base = base_caps.get(tier, 60)
            caps[resource_id] = max(min_cap, int(base * level_factor * industry_factor))
        return caps

    def determine_extraction_resources(
        self,
        body_type: str,
        seed: Union[int, str] = 0,
        researched_techs: Optional[set] = None,
    ) -> list:
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
            requires = info.get("requires_tech", [])
            if requires:
                if not researched_techs or not set(requires).issubset(researched_techs):
                    continue
            # Deterministic: use hash to decide availability
            resource_hash = int(
                hashlib.sha256(f"{seed}:{resource_id}".encode("utf-8")).hexdigest(),
                16,
            ) % 1000
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
