"""Procedural system generation with known-system overrides."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable

from .known_systems import KnownSystemRegistry


STAR_CLASS_WEIGHTS = [
    ("M", 0.35),
    ("K", 0.25),
    ("G", 0.2),
    ("F", 0.1),
    ("A", 0.07),
    ("B", 0.02),
    ("O", 0.01),
]

PLANET_TYPES_BY_ZONE = {
    "inner": ["rocky", "rocky", "volcanic", "barren"],
    "habitable": ["rocky", "oceanic", "garden", "desert"],
    "outer": ["gas_giant", "ice", "barren", "gas_giant"],
}

RESOURCE_BASELINES = {
    "rocky": {"metals": 6, "energy": 2},
    "volcanic": {"metals": 4, "energy": 6},
    "barren": {"metals": 3},
    "desert": {"metals": 4, "energy": 2},
    "oceanic": {"energy": 4, "exotics": 2},
    "garden": {"energy": 5, "exotics": 3},
    "ice": {"energy": 2, "exotics": 2},
    "gas_giant": {"energy": 8},
    "moon": {"metals": 2, "energy": 1},
    "asteroid_belt": {"metals": 8, "exotics": 2},
}

INNER_ORBIT_AU_RANGE = (0.25, 1.8)
HABITABLE_ORBIT_AU_RANGE = (0.8, 4.5)
OUTER_ORBIT_AU_RANGE = (3.0, 30.0)


@dataclass
class GeneratedSystem:
    stars: list
    planets: list


class SystemGenerator:
    def __init__(self, known_registry: KnownSystemRegistry | None = None):
        self.known_registry = known_registry or KnownSystemRegistry()

    @staticmethod
    def _weighted_choice(rng, options: Iterable[tuple[str, float]]) -> str:
        roll = rng.random()
        cumulative = 0.0
        for value, weight in options:
            cumulative += weight
            if roll <= cumulative:
                return value
        return options[-1][0]

    @staticmethod
    def _orbit_zone(index: int, total: int) -> str:
        if index <= 2:
            return "inner"
        if index <= max(3, total // 2):
            return "habitable"
        return "outer"

    @staticmethod
    def _orbit_distance_au(index: int, total: int, zone: str, rng) -> float:
        if total <= 1:
            return 1.0

        if zone == "inner":
            min_au, max_au = INNER_ORBIT_AU_RANGE
        elif zone == "habitable":
            min_au, max_au = HABITABLE_ORBIT_AU_RANGE
        else:
            min_au, max_au = OUTER_ORBIT_AU_RANGE

        # Blend deterministic orbit index progression with small variance.
        t = max(0.0, min(1.0, (index - 1) / max(1, total - 1)))
        base = min_au + (max_au - min_au) * t
        jitter = 1.0 + rng.uniform(-0.08, 0.08)
        return round(max(0.05, base * jitter), 3)

    @staticmethod
    def _moon_orbit_distance_au(parent_au: float, moon_index: int) -> float:
        # Keep moons close to host orbit while preserving ordering.
        return round(parent_au + 0.001 * moon_index, 3)

    def generate_system(self, system_id: str, name: str, rng, use_known: bool = True) -> GeneratedSystem:
        known = self.known_registry.get_system_data(system_id) if use_known else None
        if known:
            return GeneratedSystem(
                stars=list(known.get("stars", [])),
                planets=list(known.get("planets", [])),
            )

        star_class = self._weighted_choice(rng, STAR_CLASS_WEIGHTS)
        stars = [{"name": name, "spectral": star_class}]

        planet_count = rng.randint(3, 12)
        planets = []
        colonizable_exists = False

        for idx in range(1, planet_count + 1):
            zone = self._orbit_zone(idx, planet_count)
            p_type = rng.choice(PLANET_TYPES_BY_ZONE[zone])
            if zone == "inner" and p_type == "gas_giant":
                p_type = "rocky"

            body_type = "gas_giant" if p_type == "gas_giant" else "terrestrial"
            habitability = rng.uniform(0.1, 0.9)
            if zone == "habitable" and p_type in {"rocky", "oceanic", "garden", "desert"}:
                habitability = rng.uniform(0.4, 0.9)
            elif zone == "inner":
                habitability = rng.uniform(0.05, 0.4)
            elif zone == "outer":
                habitability = rng.uniform(0.05, 0.3)

            colonizable = p_type in {"rocky", "oceanic", "garden", "desert"} and habitability >= 0.35
            traits = []
            if p_type in {"volcanic"}:
                traits.append("volatile")
            if p_type in {"rocky", "barren"} and rng.random() < 0.3:
                traits.append("mineral_rich")
            if colonizable and rng.random() < 0.15:
                traits.append("frontier")

            resources = dict(RESOURCE_BASELINES.get(p_type, {}))
            baseline_output = dict(resources)

            planets.append({
                "id": f"{system_id}_p{idx}",
                "name": f"{name} {idx}",
                "type": p_type,
                "body_type": body_type,
                "orbit_index": idx,
                "semi_major_axis_au": self._orbit_distance_au(idx, planet_count, zone, rng),
                "resources": resources,
                "baseline_output": baseline_output,
                "colonizable": colonizable,
                "habitability": round(habitability, 2),
                "gravity": round(rng.uniform(0.6, 1.4), 2),
                "traits": traits,
            })
            colonizable_exists = colonizable_exists or colonizable

            moon_count = 0
            if p_type == "gas_giant":
                moon_count = rng.randint(1, 3)
            elif p_type in {"rocky", "oceanic", "garden", "desert"}:
                moon_count = rng.randint(0, 2)

            parent_au = planets[-1]["semi_major_axis_au"]

            for midx in range(1, moon_count + 1):
                moon_habitability = rng.uniform(0.1, 0.6)
                moon_colonizable = moon_habitability >= 0.35
                moon_traits = []
                if rng.random() < 0.2:
                    moon_traits.append("mineral_rich")
                planets.append({
                    "id": f"{system_id}_p{idx}_m{midx}",
                    "name": f"{name} {idx}-{midx}",
                    "type": "moon",
                    "body_type": "moon",
                    "orbit_index": idx + midx / 10,
                    "semi_major_axis_au": self._moon_orbit_distance_au(parent_au, midx),
                    "resources": dict(RESOURCE_BASELINES.get("moon", {})),
                    "baseline_output": dict(RESOURCE_BASELINES.get("moon", {})),
                    "colonizable": moon_colonizable,
                    "habitability": round(moon_habitability, 2),
                    "gravity": round(rng.uniform(0.2, 0.9), 2),
                    "traits": moon_traits,
                })
                colonizable_exists = colonizable_exists or moon_colonizable

        if not colonizable_exists:
            for planet in planets:
                if planet["type"] in {"rocky", "desert"}:
                    planet["type"] = "garden"
                    planet["body_type"] = "terrestrial"
                    planet["colonizable"] = True
                    planet["habitability"] = max(0.4, planet["habitability"])
                    colonizable_exists = True
                    break

        return GeneratedSystem(stars=stars, planets=planets)
