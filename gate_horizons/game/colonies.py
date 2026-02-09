"""Colony management system for Gate Horizons.

Colonies are abstracted settlements on worlds. Each colony tracks:
- Level (0=Outpost, 1=Settlement, 2=Colony, 3=Hub City)
- Population units with health/education/pollution indices
- Local stockpiles with storage caps
- Stability (affected by shortages, overcrowding, traits)
- Infrastructure slots with per-type effects
- Growth/upgrade progress toward next level
- Production inventory (raw, processed, components)
- Extraction sites and factories

This is NOT Factorio: no belt/item micromanagement. Resources flow
as abstracted per-turn quantities through the logistics network.
"""

import random
from typing import Optional

from gate_horizons.sim.population import PopulationSimulator
from gate_horizons.sim.balance_constants import (
    POP_RETAIN_PERCENT_DEFAULT,
    POP_EXPORT_CAP_DEFAULT,
    POP_POLICY_PRIORITY_MULTIPLIERS,
    POPULATION_DEFAULT_BY_LEVEL,
)

from .production import (
    ExtractionSite,
    Factory,
    empty_production_inventory,
    ALL_PRODUCTION_RESOURCES,
)

# Infrastructure types available for construction
INFRASTRUCTURE_TYPES = [
    "housing", "industry", "defense", "research", "spaceport",
    "power", "mining", "logistics",
]

# Legacy types kept for backward compatibility during deserialization
_LEGACY_INFRA_TYPES = ["housing", "industry", "defense", "research", "spaceport"]

DEFAULT_INFRASTRUCTURE = {
    infra: {"level": 0, "building": False, "turns_remaining": 0}
    for infra in INFRASTRUCTURE_TYPES
}

# Build costs per infrastructure level
BUILD_COSTS = {
    "housing": {"credits": 30, "metals": 15},
    "industry": {"credits": 40, "metals": 25},
    "defense": {"credits": 50, "metals": 30},
    "research": {"credits": 45, "metals": 20},
    "spaceport": {"credits": 60, "metals": 40},
    "power": {"credits": 35, "metals": 20},
    "mining": {"credits": 45, "metals": 30},
    "logistics": {"credits": 55, "metals": 35},
}

BUILD_TURNS = {
    "housing": 2,
    "industry": 3,
    "defense": 3,
    "research": 3,
    "spaceport": 4,
    "power": 2,
    "mining": 3,
    "logistics": 4,
}

# Housing capacity per level (base + per-level bonus)
HOUSING_BASE_CAP = 100
HOUSING_PER_LEVEL = 200

# Colony level definitions
COLONY_LEVELS = {
    0: {"name": "Outpost", "max_infra_slots": 3, "storage_mult": 0.5, "route_cap_mult": 0.5},
    1: {"name": "Settlement", "max_infra_slots": 5, "storage_mult": 1.0, "route_cap_mult": 1.0},
    2: {"name": "Colony", "max_infra_slots": 7, "storage_mult": 1.5, "route_cap_mult": 1.5},
    3: {"name": "Hub City", "max_infra_slots": 8, "storage_mult": 2.0, "route_cap_mult": 2.0},
}

# Costs to upgrade colony level (from current level to next)
COLONY_UPGRADE_COSTS = {
    0: {"credits": 100, "metals": 60, "energy": 30},       # Outpost -> Settlement
    1: {"credits": 250, "metals": 150, "energy": 80},      # Settlement -> Colony
    2: {"credits": 500, "metals": 300, "energy": 150, "exotics": 10},  # Colony -> Hub City
}

# Tech prerequisites for colony upgrade
COLONY_UPGRADE_TECH = {
    0: [],                       # Outpost -> Settlement: no extra tech
    1: ["colonisation"],         # Settlement -> Colony: colonisation tech
    2: ["logistics_2"],          # Colony -> Hub City: logistics II
}

# Base storage caps per resource (before multipliers)
BASE_STORAGE = {
    "energy": 100,
    "metals": 100,
    "exotics": 30,
    "credits": 200,
    "intel": 50,
}

# Colony founding costs
FOUNDING_COST = {"credits": 80, "metals": 50, "energy": 20}

# Starter cargo required on the colony ship to establish a new outpost
COLONY_STARTER_CARGO = {"energy": 15, "metals": 20, "credits": 30}

# Colonist requirement for founding a new colony
COLONY_COLONIST_REQUIREMENT = 50

# World trait modifiers
WORLD_TRAIT_MODIFIERS = {
    "hub": {
        "logistics_bonus": 2,       # +2 to logistics infrastructure effect
        "storage_bonus": 50,         # +50 to all storage caps
        "research_penalty": -1,      # -1 to research output
        "stability_bonus": 5,        # +5 base stability
        "capacity_bonus": 150,       # +150 to carrying capacity
    },
    "frontier": {
        "exotics_chance": 0.3,       # 30% chance of bonus exotics per turn
        "stability_penalty": -10,    # -10 base stability
        "capacity_penalty": -20,     # -20 to all storage caps
        "exotics_bonus": 2,          # +2 exotics output when triggered
        "capacity_bonus": -80,       # -80 to carrying capacity
    },
    "mineral_rich": {
        "metals_bonus": 3,           # +3 metals per turn
    },
    "volatile": {
        "energy_bonus": 2,           # +2 energy per turn
        "stability_penalty": -5,     # -5 base stability
    },
}


class Colony:
    HOUSING_BASE_CAP = HOUSING_BASE_CAP
    HOUSING_PER_LEVEL = HOUSING_PER_LEVEL
    WORLD_TRAIT_MODIFIERS = WORLD_TRAIT_MODIFIERS

    def __init__(
        self,
        system_id: str,
        planet_id: str,
        name: str = "New Colony",
        population: int = 100,
        population_units: Optional[int] = None,
        happiness: int = 70,
        infrastructure: dict = None,
        build_queue: list = None,
        shipyard_queue: list = None,
        level: int = 0,
        stability: int = 60,
        health_index: int = 60,
        education_index: int = 50,
        pollution_index: int = 15,
        population_policy: dict = None,
        stockpiles: dict = None,
        owner_faction: str = "player",
        upgrade_progress: int = 0,
        world_traits: list = None,
        shortage_turns: int = 0,
        # Production system fields
        production_inventory: dict = None,
        extraction_sites: list = None,
        factories: list = None,
        resource_ledger: list = None,
        last_bottlenecks: list = None,
        trait_stability_applied: int | None = None,
    ):
        self.system_id = system_id
        self.planet_id = planet_id
        self.name = name
        self._population_units = int(
            population_units if population_units is not None else population
        )
        self.happiness = happiness
        self.infrastructure = infrastructure or {
            k: dict(v) for k, v in DEFAULT_INFRASTRUCTURE.items()
        }
        self.build_queue = build_queue or []
        self.shipyard_queue = shipyard_queue or []
        self.level = level
        self.stability = stability
        self.health_index = int(health_index)
        self.education_index = int(education_index)
        self.pollution_index = int(pollution_index)
        self.population_policy = population_policy or {
            "retain_percent": POP_RETAIN_PERCENT_DEFAULT,
            "export_cap_per_turn": POP_EXPORT_CAP_DEFAULT,
            "priority": "balanced",
        }
        self.stockpiles = stockpiles or {
            "energy": 0, "metals": 0, "exotics": 0, "credits": 0, "intel": 0,
        }
        self.owner_faction = owner_faction
        self.upgrade_progress = upgrade_progress
        self.world_traits = world_traits or []
        self.shortage_turns = shortage_turns
        # Production system
        self.production_inventory = production_inventory or empty_production_inventory()
        self.extraction_sites = extraction_sites or []
        self.factories = factories or []
        self.resource_ledger = list(resource_ledger or [])
        self.last_bottlenecks = list(last_bottlenecks or [])
        self.last_population_report = {
            "births": 0,
            "deaths": 0,
            "net_change": 0,
            "net_migration": 0,
        }
        self.pending_population_migration = 0
        self._trait_stability_applied = (
            int(trait_stability_applied)
            if trait_stability_applied is not None
            else 0
        )
        self.last_trait_effects: dict = {}

    @property
    def population(self) -> int:
        return self._population_units

    @population.setter
    def population(self, value: int) -> None:
        self._population_units = max(0, int(value))

    @property
    def population_units(self) -> int:
        return self._population_units

    def get_carrying_capacity(self, tech_effects: dict | None = None) -> int:
        return PopulationSimulator.compute_carrying_capacity(self, tech_effects=tech_effects)

    def get_population_policy(self) -> dict:
        policy = dict(self.population_policy or {})
        policy.setdefault("retain_percent", POP_RETAIN_PERCENT_DEFAULT)
        policy.setdefault("export_cap_per_turn", POP_EXPORT_CAP_DEFAULT)
        policy.setdefault("priority", "balanced")
        return policy

    def get_population_export_available(self, requested: int) -> int:
        policy = self.get_population_policy()
        retain_percent = max(0.0, min(1.0, float(policy.get("retain_percent", 0.0))))
        retain_floor = int(self.population_units * retain_percent)
        exportable = max(0, self.population_units - retain_floor)

        cap = int(policy.get("export_cap_per_turn", 0) or 0)
        priority = str(policy.get("priority", "balanced")).lower()
        multiplier = POP_POLICY_PRIORITY_MULTIPLIERS.get(priority, 1.0)
        if cap > 0:
            cap = int(cap * multiplier)
            exportable = min(exportable, cap)

        if requested <= 0:
            return exportable
        return min(exportable, requested)

    def add_population_units(self, amount: int, tech_effects: dict | None = None) -> int:
        if amount <= 0:
            return 0
        capacity = self.get_carrying_capacity(tech_effects=tech_effects)
        available = max(0, capacity - self.population_units)
        added = min(amount, available) if capacity else amount
        self.population = self.population_units + added
        return added

    def apply_population_transfer(
        self,
        amount: int,
        tech_effects: dict | None = None,
    ) -> int:
        """Apply a population transfer immediately without using pending migration."""
        if amount == 0:
            return 0
        if amount > 0:
            return self.add_population_units(amount, tech_effects=tech_effects)
        removal = min(-amount, self.population_units)
        if removal <= 0:
            return 0
        self.population = self.population_units - removal
        return -removal

    def get_tier(self) -> int:
        """Map colony level to world tier for backward compatibility."""
        levels = [
            self.infrastructure.get(k, {}).get("level", 0)
            for k in INFRASTRUCTURE_TYPES
        ]
        if all(l >= 3 for l in levels):
            return 1  # Core world
        if any(l >= 1 for l in levels) and self.population >= 200:
            return 2  # Developing
        return 3  # Frontier outpost

    def get_level_info(self) -> dict:
        return COLONY_LEVELS.get(self.level, COLONY_LEVELS[0])

    def get_storage_caps(self) -> dict:
        """Calculate storage caps based on level, infrastructure, and traits."""
        level_info = self.get_level_info()
        storage_mult = level_info["storage_mult"]

        # Base storage scaled by level
        caps = {r: int(v * storage_mult) for r, v in BASE_STORAGE.items()}

        # Logistics infrastructure bonus: +25% per level
        logistics_level = self.infrastructure.get("logistics", {}).get("level", 0)
        for r in caps:
            caps[r] += int(caps[r] * logistics_level * 0.25)

        # World trait modifiers
        for trait in self.world_traits:
            mods = WORLD_TRAIT_MODIFIERS.get(trait, {})
            storage_bonus = mods.get("storage_bonus", 0)
            capacity_penalty = mods.get("capacity_penalty", 0)
            for r in caps:
                caps[r] += storage_bonus + capacity_penalty

        # Ensure minimum storage of 20
        for r in caps:
            caps[r] = max(20, caps[r])

        return caps

    def get_active_infra_count(self) -> int:
        """Count infrastructure types with level >= 1."""
        return sum(
            1 for k in INFRASTRUCTURE_TYPES
            if self.infrastructure.get(k, {}).get("level", 0) >= 1
        )

    def get_trait_stability_modifier(self) -> int:
        total = 0
        for trait in self.world_traits:
            mods = WORLD_TRAIT_MODIFIERS.get(trait, {})
            total += int(mods.get("stability_bonus", 0))
            total += int(mods.get("stability_penalty", 0))
        return total

    def apply_world_trait_stability(self, report: dict | None = None) -> int:
        target = self.get_trait_stability_modifier()
        delta = target - self._trait_stability_applied
        if delta:
            self.stability = max(0, min(100, self.stability + delta))
            self._trait_stability_applied = target
            if report is not None:
                report["stability_trait_adjustment"] = delta
                report["stability"] = self.stability
        return delta

    def calculate_production(self, rng: random.Random | None = None) -> dict:
        """Calculate per-turn production based on infrastructure and traits."""
        self.apply_world_trait_stability()
        production = {}
        industry_level = self.infrastructure.get("industry", {}).get("level", 0)
        research_level = self.infrastructure.get("research", {}).get("level", 0)
        spaceport_level = self.infrastructure.get("spaceport", {}).get("level", 0)
        power_level = self.infrastructure.get("power", {}).get("level", 0)
        mining_level = self.infrastructure.get("mining", {}).get("level", 0)

        pop_factor = self.population / 100.0
        stability_factor = max(0.1, self.stability / 100.0)

        # Power generates energy
        production["energy"] = int((power_level + 1) * 2 * pop_factor)

        # Mining generates metals (requires power)
        effective_mining = min(mining_level, power_level + 1)
        production["metals"] = int(effective_mining * 3 * pop_factor * stability_factor)

        # Industry also contributes metals and energy
        production["metals"] += int(industry_level * 2 * pop_factor * stability_factor)
        production["energy"] += int(industry_level * 1 * pop_factor)

        # Research produces intel
        production["intel"] = int(research_level * 2 * pop_factor * stability_factor)

        # Spaceport generates credits
        production["credits"] = int((spaceport_level + 1) * 3 * pop_factor)

        self.last_trait_effects = {}

        # World trait bonuses
        for trait in self.world_traits:
            mods = WORLD_TRAIT_MODIFIERS.get(trait, {})
            if "metals_bonus" in mods:
                production["metals"] += mods["metals_bonus"]
            if "energy_bonus" in mods:
                production["energy"] += mods["energy_bonus"]
            if "research_penalty" in mods:
                production["intel"] = max(0, production["intel"] + mods["research_penalty"])
            chance = mods.get("exotics_chance", 0)
            bonus = mods.get("exotics_bonus", 0)
            if chance and bonus:
                local_rng = rng
                if local_rng is None:
                    seed_source = f"{self.system_id}:{self.population_units}:{self.stability}"
                    local_rng = random.Random(
                        int.from_bytes(seed_source.encode("utf-8"), "little")
                    )
                triggered = local_rng.random() < float(chance)
                self.last_trait_effects.setdefault("exotics_rolls", []).append({
                    "trait": trait,
                    "chance": float(chance),
                    "bonus": int(bonus),
                    "triggered": triggered,
                })
                if triggered:
                    production["exotics"] = production.get("exotics", 0) + int(bonus)
                    self.last_trait_effects["exotics_bonus"] = (
                        self.last_trait_effects.get("exotics_bonus", 0) + int(bonus)
                    )

        return production

    def calculate_consumption(self) -> dict:
        """Calculate per-turn consumption/upkeep.

        Upkeep scales with colony level + infrastructure count to prevent
        runaway growth.
        """
        consumption = {}
        pop_factor = self.population / 100.0

        # Population consumes energy and credits
        consumption["energy"] = int(2 * pop_factor)
        consumption["credits"] = int(1 * pop_factor)

        # Infrastructure maintenance scales with level and count
        infra_count = self.get_active_infra_count()
        level_mult = 1 + self.level * 0.5  # Higher level = more upkeep

        for infra_type in INFRASTRUCTURE_TYPES:
            level = self.infrastructure.get(infra_type, {}).get("level", 0)
            consumption["credits"] = consumption.get("credits", 0) + int(level * level_mult)

        # Additional energy upkeep for infrastructure density
        consumption["energy"] += int(infra_count * self.level * 0.5)

        return consumption

    def apply_shortage_penalties(self, shortages: dict) -> dict:
        """Apply penalties when stockpile can't cover consumption.

        Returns dict of penalties applied.
        """
        penalties = {}
        total_shortage = sum(shortages.values())

        if total_shortage > 0:
            self.shortage_turns += 1

            # Stability drops based on shortage severity
            stability_hit = min(20, total_shortage * 2 + self.shortage_turns)
            self.stability = max(0, self.stability - stability_hit)
            penalties["stability_loss"] = stability_hit

            # Growth halted during shortages
            penalties["growth_halted"] = True

            # Production penalty: 50% reduction if prolonged shortage
            if self.shortage_turns >= 3:
                penalties["production_penalty"] = 0.5
        else:
            # Recovery: stability slowly increases when no shortages
            if self.shortage_turns > 0:
                self.shortage_turns = max(0, self.shortage_turns - 1)
            recovery = 2 if self.shortage_turns == 0 else 1
            self.stability = min(100, self.stability + recovery)
            penalties["stability_recovery"] = recovery

        return penalties

    def start_construction(self, infra_type: str, build_time_reduction: int = 0) -> bool:
        """Start building/upgrading an infrastructure type."""
        if infra_type not in INFRASTRUCTURE_TYPES:
            return False

        infra = self.infrastructure.get(infra_type, {})
        if infra.get("building", False):
            return False  # Already building

        # Check infrastructure slot limit based on colony level
        level_info = self.get_level_info()
        if self.get_active_infra_count() >= level_info["max_infra_slots"]:
            # Allow upgrades to existing infrastructure, but not new types
            if infra.get("level", 0) == 0:
                return False

        turns = max(1, BUILD_TURNS.get(infra_type, 3) - build_time_reduction)
        self.infrastructure[infra_type] = {
            "level": infra.get("level", 0),
            "building": True,
            "turns_remaining": turns,
        }
        return True

    def get_build_cost(self, infra_type: str) -> dict:
        """Get cost to build next level of infrastructure."""
        base_cost = BUILD_COSTS.get(infra_type, {})
        level = self.infrastructure.get(infra_type, {}).get("level", 0)
        return {r: int(amount * (1 + level * 0.5)) for r, amount in base_cost.items()}

    def queue_construction(self, infra_type: str) -> None:
        self.build_queue.append({"type": infra_type})

    def get_upgrade_cost(self) -> dict:
        """Get cost to upgrade colony to next level."""
        return dict(COLONY_UPGRADE_COSTS.get(self.level, {}))

    def get_upgrade_tech_requirements(self) -> list:
        """Get tech prerequisites for upgrading to next level."""
        return list(COLONY_UPGRADE_TECH.get(self.level, []))

    def can_upgrade(self, researched_techs: set = None) -> bool:
        """Check if colony can be upgraded to next level."""
        if self.level >= 3:
            return False

        # Check tech prerequisites
        required_techs = self.get_upgrade_tech_requirements()
        if required_techs and researched_techs:
            for tech_id in required_techs:
                if tech_id not in researched_techs:
                    return False
        elif required_techs:
            return False

        return True

    def upgrade(self) -> bool:
        """Upgrade colony to next level. Caller must check costs and tech."""
        if self.level >= 3:
            return False
        self.level += 1
        self.upgrade_progress = 0
        return True

    # ---- Ship construction (shipyard) ----

    def can_build_ship(self, ship_class: str, templates: dict) -> bool:
        """Check if colony can queue a ship build (spaceport exists, slot open)."""
        spaceport_level = self.infrastructure.get("spaceport", {}).get("level", 0)
        if spaceport_level < 1:
            return False
        if len(self.shipyard_queue) >= spaceport_level:
            return False
        if ship_class not in templates:
            return False
        return True

    def get_ship_build_cost(self, ship_class: str, templates: dict) -> dict:
        """Return the resource cost to build a ship class."""
        template = templates.get(ship_class, {})
        return dict(template.get("build_cost", {}))

    def start_ship_build(
        self,
        ship_class: str,
        name: str,
        build_turns: int,
        build_time_reduction: int = 0,
    ) -> bool:
        spaceport_level = self.infrastructure.get("spaceport", {}).get("level", 0)
        if spaceport_level < 1:
            return False
        if len(self.shipyard_queue) >= spaceport_level:
            return False
        turns = max(1, build_turns - build_time_reduction)
        self.shipyard_queue.append({
            "ship_class": ship_class,
            "name": name,
            "turns_remaining": turns,
        })
        return True

    def get_logistics_capacity(self) -> int:
        """Get outgoing logistics route capacity based on infrastructure and level.

        This determines how many resources per turn can be shipped out.
        """
        logistics_level = self.infrastructure.get("logistics", {}).get("level", 0)
        level_info = self.get_level_info()
        base_cap = 10 + logistics_level * 8
        cap = int(base_cap * level_info["route_cap_mult"])

        # Hub trait bonus
        for trait in self.world_traits:
            mods = WORLD_TRAIT_MODIFIERS.get(trait, {})
            cap += mods.get("logistics_bonus", 0) * 5

        return cap

    def process_turn(self, build_time_reduction: int = 0, tech_effects: dict | None = None) -> dict:
        """Process one turn for this colony. Returns summary of changes.

        Note: This handles construction, shipyard, population, and happiness.
        Stockpile production/consumption is handled by the turn processor
        to follow the correct resolution order.
        """
        report = {
            "construction_completed": [],
            "ships_completed": [],
            "population_growth": 0,
            "population_births": 0,
            "population_deaths": 0,
            "population_migration": 0,
            "population_net": 0,
            "happiness_change": 0,
            "tier_change": None,
            "stability": self.stability,
            "health_index": self.health_index,
            "education_index": self.education_index,
            "pollution_index": self.pollution_index,
        }

        old_tier = self.get_tier()
        self.apply_world_trait_stability(report)

        # Advance construction
        for infra_type in INFRASTRUCTURE_TYPES:
            infra = self.infrastructure.get(infra_type, {})
            if infra.get("building", False):
                infra["turns_remaining"] = infra.get("turns_remaining", 0) - 1
                if infra["turns_remaining"] <= 0:
                    infra["level"] = infra.get("level", 0) + 1
                    infra["building"] = False
                    infra["turns_remaining"] = 0
                    report["construction_completed"].append(infra_type)

        # Process build queue
        if self.build_queue:
            for infra_type in INFRASTRUCTURE_TYPES:
                if not self.infrastructure.get(infra_type, {}).get("building", False):
                    for i, item in enumerate(self.build_queue):
                        if item["type"] == infra_type:
                            self.start_construction(infra_type, build_time_reduction)
                            self.build_queue.pop(i)
                            break

        # Advance shipyard queue
        for item in list(self.shipyard_queue):
            item["turns_remaining"] -= 1
            if item["turns_remaining"] <= 0:
                report["ships_completed"].append({
                    "ship_class": item["ship_class"],
                    "name": item["name"],
                })
                self.shipyard_queue.remove(item)

        # Population dynamics
        PopulationSimulator.update_indices(self, tech_effects=tech_effects)
        result = PopulationSimulator.simulate_turn(self, tech_effects=tech_effects)
        net_migration = self.pending_population_migration
        net_growth = result.net_change + net_migration
        if net_growth != 0:
            self.population = max(0, self.population_units + net_growth)

        report["population_births"] = result.births
        report["population_deaths"] = result.deaths
        report["population_migration"] = net_migration
        report["population_net"] = net_growth
        report["population_growth"] = net_growth
        self.last_population_report = {
            "births": result.births,
            "deaths": result.deaths,
            "net_change": result.net_change,
            "net_migration": net_migration,
        }
        self.pending_population_migration = 0

        # Happiness adjustments (now tracks stability more closely)
        housing_level = self.infrastructure.get("housing", {}).get("level", 0)
        housing_cap = HOUSING_BASE_CAP + housing_level * HOUSING_PER_LEVEL

        if self.population > housing_cap * 0.9:
            self.happiness = max(0, self.happiness - 5)
            report["happiness_change"] -= 5
        elif self.population < housing_cap * 0.5:
            self.happiness = min(100, self.happiness + 2)
            report["happiness_change"] += 2

        # Stability influences happiness
        if self.stability < 30:
            self.happiness = max(0, self.happiness - 3)
            report["happiness_change"] -= 3
        elif self.stability > 80:
            self.happiness = min(100, self.happiness + 1)
            report["happiness_change"] += 1

        report["stability"] = self.stability

        # Tier check
        new_tier = self.get_tier()
        if new_tier != old_tier:
            report["tier_change"] = (old_tier, new_tier)

        return report

    def to_dict(self) -> dict:
        return {
            "system_id": self.system_id,
            "planet_id": self.planet_id,
            "name": self.name,
            "population": self.population,
            "population_units": self.population_units,
            "happiness": self.happiness,
            "infrastructure": {
                k: dict(v) for k, v in self.infrastructure.items()
            },
            "build_queue": list(self.build_queue),
            "shipyard_queue": [dict(item) for item in self.shipyard_queue],
            "level": self.level,
            "stability": self.stability,
            "health_index": self.health_index,
            "education_index": self.education_index,
            "pollution_index": self.pollution_index,
            "population_policy": dict(self.population_policy),
            "stockpiles": dict(self.stockpiles),
            "owner_faction": self.owner_faction,
            "upgrade_progress": self.upgrade_progress,
            "world_traits": list(self.world_traits),
            "shortage_turns": self.shortage_turns,
            "production_inventory": dict(self.production_inventory),
            "extraction_sites": [s.to_dict() for s in self.extraction_sites],
            "factories": [f.to_dict() for f in self.factories],
            "resource_ledger": list(self.resource_ledger),
            "last_bottlenecks": list(self.last_bottlenecks),
            "trait_stability_applied": self._trait_stability_applied,
        }

    @classmethod
    def from_dict(cls, data: dict) -> "Colony":
        infrastructure = {
            k: dict(v) for k, v in DEFAULT_INFRASTRUCTURE.items()
        }
        incoming_infra = data.get("infrastructure") or {}
        for infra_type, infra_data in incoming_infra.items():
            if infra_type not in INFRASTRUCTURE_TYPES or not isinstance(infra_data, dict):
                continue
            merged = dict(infrastructure.get(infra_type, DEFAULT_INFRASTRUCTURE.get(infra_type, {})))
            merged.update(infra_data)
            infrastructure[infra_type] = merged
        # Production system fields (default to empty for old saves)
        prod_inv = data.get("production_inventory")
        if prod_inv:
            # Ensure all keys present
            full_inv = empty_production_inventory()
            full_inv.update(prod_inv)
            prod_inv = full_inv
        else:
            prod_inv = empty_production_inventory()

        extraction_sites = [
            ExtractionSite.from_dict(s) for s in data.get("extraction_sites", [])
        ]
        factories = [
            Factory.from_dict(f) for f in data.get("factories", [])
        ]

        population_value = data.get("population_units")
        if population_value is None:
            population_value = data.get("population")
        if population_value is None:
            level = int(data.get("level", 0))
            population_value = POPULATION_DEFAULT_BY_LEVEL.get(level, 100)

        return cls(
            system_id=data.get("system_id", ""),
            planet_id=data.get("planet_id", ""),
            name=data.get("name", "New Colony"),
            population=int(population_value),
            population_units=int(population_value),
            happiness=data.get("happiness", 70),
            infrastructure=infrastructure,
            build_queue=list(data.get("build_queue", [])),
            shipyard_queue=[dict(item) for item in data.get("shipyard_queue", [])],
            level=data.get("level", 0),
            stability=data.get("stability", 60),
            health_index=data.get("health_index", 60),
            education_index=data.get("education_index", 50),
            pollution_index=data.get("pollution_index", 15),
            population_policy=data.get("population_policy"),
            stockpiles=data.get("stockpiles", {
                "energy": 0, "metals": 0, "exotics": 0, "credits": 0, "intel": 0,
            }),
            owner_faction=data.get("owner_faction", "player"),
            upgrade_progress=data.get("upgrade_progress", 0),
            world_traits=list(data.get("world_traits", [])),
            shortage_turns=data.get("shortage_turns", 0),
            production_inventory=prod_inv,
            extraction_sites=extraction_sites,
            factories=factories,
            resource_ledger=list(data.get("resource_ledger", [])),
            last_bottlenecks=list(data.get("last_bottlenecks", [])),
            trait_stability_applied=data.get("trait_stability_applied"),
        )


class ColonyManager:
    def __init__(self):
        self.colonies: dict[str, Colony] = {}

    def establish_colony(
        self,
        system_id: str,
        planet_id: str,
        name: str,
        initial_pop: int = 100,
        level: int = 0,
        world_traits: list = None,
    ) -> Colony:
        colony = Colony(
            system_id=system_id,
            planet_id=planet_id,
            name=name,
            population=initial_pop,
            level=level,
            world_traits=world_traits or [],
        )
        self.colonies[system_id] = colony
        return colony

    def get_player_influence_markers(self, galaxy=None) -> list[dict]:
        """Return deterministic influence markers for player-owned colonies."""
        if galaxy is None:
            return []
        markers = []
        for system_id in sorted(self.colonies):
            colony = self.colonies[system_id]
            if colony.owner_faction != "player":
                continue
            if system_id not in galaxy.systems:
                continue
            markers.append({"system_id": system_id, "level": colony.level})
        return markers

    def can_found_colony(
        self,
        system_id: str,
        planet_id: str,
        galaxy=None,
        tech_effects: dict = None,
        researched_techs: set = None,
        fleet=None,
        ship_id: str = None,
        resources=None,
    ) -> tuple:
        """Check if a new colony can be founded. Returns (can_found, reason)."""
        if system_id in self.colonies:
            return False, "System already has a colony"

        if not fleet:
            return False, "Colony ship required in system"

        colony_ship = None
        if ship_id:
            colony_ship = fleet.ships.get(ship_id)
            if not colony_ship:
                return False, "Colony ship not found"
        else:
            colony_ship = next(
                (ship for ship in fleet.ships.values()
                 if ship.location == system_id and "establish_colony" in ship.stats.abilities),
                None,
            )
        if not colony_ship:
            return False, "Colony ship required in system"
        if colony_ship.location != system_id:
            return False, "Colony ship must be in target system"
        if "establish_colony" not in colony_ship.stats.abilities:
            return False, "Ship lacks establish_colony capability"

        # Check colonisation tech
        if researched_techs is None or "colonisation" not in researched_techs:
            return False, "Colonisation technology required"

        colonists_required = self.get_colonist_requirement()
        if colony_ship.cargo.get("pop", 0) < colonists_required:
            return False, f"Requires {colonists_required} POP in colony ship cargo"

        # Check planet exists and is colonizable
        if galaxy:
            system = galaxy.systems.get(system_id)
            if not system:
                return False, "System not found"
            planet = None
            for p in system.planets:
                if p.id == planet_id:
                    planet = p
                    break
            if not planet:
                return False, "Planet not found"
            if not planet.colonizable:
                return False, "Planet is not colonizable"

        if resources:
            cost = self.get_founding_cost()
            if not resources.can_afford(cost):
                return False, f"Cannot afford founding cost: {cost}"

        return True, "OK"

    def get_founding_cost(self) -> dict:
        """Get the resource cost to found a new colony."""
        return dict(FOUNDING_COST)

    def get_starter_cargo_requirement(self) -> dict:
        """Get the starter cargo required to establish a colony."""
        return dict(COLONY_STARTER_CARGO)

    def get_colonist_requirement(self) -> int:
        """Get the POP units required to establish a colony."""
        return int(COLONY_COLONIST_REQUIREMENT)

    def abandon_colony(self, system_id: str) -> bool:
        if system_id in self.colonies:
            del self.colonies[system_id]
            return True
        return False

    def get_total_production(self) -> dict:
        total = {}
        for colony in self.colonies.values():
            prod = colony.calculate_production()
            for r, amount in prod.items():
                total[r] = total.get(r, 0) + amount
        return total

    def get_total_consumption(self) -> dict:
        total = {}
        for colony in self.colonies.values():
            cons = colony.calculate_consumption()
            for r, amount in cons.items():
                total[r] = total.get(r, 0) + amount
        return total

    def process_all_turns(self, build_time_reduction: int = 0, tech_effects: dict | None = None) -> list:
        reports = []
        for system_id, colony in self.colonies.items():
            report = colony.process_turn(
                build_time_reduction=build_time_reduction,
                tech_effects=tech_effects,
            )
            report["system_id"] = system_id
            report["colony_name"] = colony.name
            reports.append(report)
        return reports

    def to_dict(self) -> dict:
        return {
            "colonies": {
                sid: c.to_dict() for sid, c in self.colonies.items()
            }
        }

    @classmethod
    def from_dict(cls, data: dict) -> "ColonyManager":
        cm = cls()
        for sid, cdata in data.get("colonies", {}).items():
            cm.colonies[sid] = Colony.from_dict(cdata)
        return cm
