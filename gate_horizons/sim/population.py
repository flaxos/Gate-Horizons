"""Population simulation helpers."""

from __future__ import annotations

from dataclasses import dataclass

from .balance_constants import (
    POPULATION_BASE_BIRTHS,
    POPULATION_BASE_DEATHS,
    EDU_FERTILITY_REDUCTION,
    HEALTH_MORTALITY_REDUCTION,
    POLLUTION_MORTALITY_PENALTY,
    HOUSING_GROWTH_BONUS,
    MIN_OVER_CAPACITY_FACTOR,
    HEALTH_TARGET_BASE,
    HEALTH_PER_HOUSING_LEVEL,
    HEALTH_PER_POWER_LEVEL,
    HEALTH_PER_RESEARCH_LEVEL,
    HEALTH_POLLUTION_PENALTY,
    HEALTH_SHORTAGE_PENALTY,
    EDU_TARGET_BASE,
    EDU_PER_RESEARCH_LEVEL,
    EDU_STABILITY_FACTOR,
    EDU_SHORTAGE_PENALTY,
    POLLUTION_TARGET_BASE,
    POLLUTION_PER_INDUSTRY_LEVEL,
    POLLUTION_PER_MINING_LEVEL,
    POLLUTION_MITIGATION_PER_POWER_LEVEL,
    POLLUTION_MITIGATION_PER_RESEARCH_LEVEL,
    POLLUTION_SHORTAGE_SPIKE,
    INDEX_ADJUST_RATE,
)


@dataclass
class PopulationTurnResult:
    births: int
    deaths: int
    net_change: int
    births_rate: float
    deaths_rate: float


class PopulationSimulator:
    @staticmethod
    def compute_carrying_capacity(colony, tech_effects: dict | None = None) -> int:
        housing_level = colony.infrastructure.get("housing", {}).get("level", 0)
        base_capacity = colony.HOUSING_BASE_CAP + housing_level * colony.HOUSING_PER_LEVEL

        capacity = base_capacity
        tech_bonus = 0.0
        if tech_effects:
            tech_bonus = float(tech_effects.get("carrying_capacity_bonus", 0.0))
        if tech_bonus:
            capacity += int(capacity * tech_bonus)

        for trait in colony.world_traits:
            mods = colony.WORLD_TRAIT_MODIFIERS.get(trait, {})
            capacity += mods.get("capacity_bonus", 0)
            capacity += mods.get("capacity_penalty", 0)

        return max(10, int(capacity))

    @staticmethod
    def _adjust_index(current: int, target: float) -> int:
        delta = (target - current) * INDEX_ADJUST_RATE
        updated = current + delta
        return max(0, min(100, int(round(updated))))

    @classmethod
    def update_indices(cls, colony, tech_effects: dict | None = None) -> dict:
        housing_level = colony.infrastructure.get("housing", {}).get("level", 0)
        power_level = colony.infrastructure.get("power", {}).get("level", 0)
        research_level = colony.infrastructure.get("research", {}).get("level", 0)
        industry_level = colony.infrastructure.get("industry", {}).get("level", 0)
        mining_level = colony.infrastructure.get("mining", {}).get("level", 0)

        health_target = (
            HEALTH_TARGET_BASE
            + housing_level * HEALTH_PER_HOUSING_LEVEL
            + power_level * HEALTH_PER_POWER_LEVEL
            + research_level * HEALTH_PER_RESEARCH_LEVEL
        )
        health_target -= colony.pollution_index * HEALTH_POLLUTION_PENALTY
        if colony.shortage_turns > 0:
            health_target -= HEALTH_SHORTAGE_PENALTY

        edu_target = (
            EDU_TARGET_BASE
            + research_level * EDU_PER_RESEARCH_LEVEL
            + (colony.stability - 50) * EDU_STABILITY_FACTOR
        )
        if colony.shortage_turns > 0:
            edu_target -= EDU_SHORTAGE_PENALTY

        pollution_target = (
            POLLUTION_TARGET_BASE
            + industry_level * POLLUTION_PER_INDUSTRY_LEVEL
            + mining_level * POLLUTION_PER_MINING_LEVEL
            - power_level * POLLUTION_MITIGATION_PER_POWER_LEVEL
            - research_level * POLLUTION_MITIGATION_PER_RESEARCH_LEVEL
        )
        if colony.shortage_turns > 0:
            pollution_target += POLLUTION_SHORTAGE_SPIKE

        if tech_effects:
            health_target += float(tech_effects.get("health_index_bonus", 0))
            edu_target += float(tech_effects.get("education_index_bonus", 0))
            pollution_target += float(tech_effects.get("pollution_index_bonus", 0))

        health_target = max(0, min(100, health_target))
        edu_target = max(0, min(100, edu_target))
        pollution_target = max(0, min(100, pollution_target))

        new_health = cls._adjust_index(colony.health_index, health_target)
        new_edu = cls._adjust_index(colony.education_index, edu_target)
        new_pollution = cls._adjust_index(colony.pollution_index, pollution_target)

        deltas = {
            "health_index": new_health - colony.health_index,
            "education_index": new_edu - colony.education_index,
            "pollution_index": new_pollution - colony.pollution_index,
        }

        colony.health_index = new_health
        colony.education_index = new_edu
        colony.pollution_index = new_pollution

        return deltas

    @classmethod
    def simulate_turn(cls, colony, tech_effects: dict | None = None) -> PopulationTurnResult:
        population = max(0, colony.population_units)
        carrying_capacity = colony.get_carrying_capacity(tech_effects=tech_effects)

        if population == 0:
            return PopulationTurnResult(0, 0, 0, 0.0, 0.0)

        if population <= carrying_capacity:
            surplus_factor = (carrying_capacity - population) / max(1, carrying_capacity)
            housing_factor = 1.0 + min(HOUSING_GROWTH_BONUS, surplus_factor * HOUSING_GROWTH_BONUS)
        else:
            housing_factor = max(MIN_OVER_CAPACITY_FACTOR, carrying_capacity / population)

        edu_factor = colony.education_index / 100.0
        health_factor = colony.health_index / 100.0
        pollution_factor = colony.pollution_index / 100.0

        births_rate = POPULATION_BASE_BIRTHS * housing_factor * (1 - EDU_FERTILITY_REDUCTION * edu_factor)
        deaths_rate = POPULATION_BASE_DEATHS * (1 - HEALTH_MORTALITY_REDUCTION * health_factor)
        deaths_rate *= (1 + POLLUTION_MORTALITY_PENALTY * pollution_factor)

        births = max(0, int(population * births_rate))
        deaths = max(0, int(population * deaths_rate))

        net_change = births - deaths
        return PopulationTurnResult(
            births=births,
            deaths=deaths,
            net_change=net_change,
            births_rate=births_rate,
            deaths_rate=deaths_rate,
        )
