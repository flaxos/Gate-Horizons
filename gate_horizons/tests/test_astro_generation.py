"""Tests for astronomy system generation."""

import random

from gate_horizons.astro.known_systems import KnownSystemRegistry
from gate_horizons.astro.system_generator import SystemGenerator


def test_sol_fixture_contains_planets_and_moons():
    registry = KnownSystemRegistry()
    sol = registry.get_system_data("sol")

    assert sol is not None
    planets = sol["planets"]

    major_planets = [
        body for body in planets
        if body.get("body_type") in {"terrestrial", "gas_giant"}
    ]
    names = {body["name"] for body in major_planets}
    assert {
        "Mercury",
        "Venus",
        "Earth",
        "Mars",
        "Jupiter",
        "Saturn",
        "Uranus",
        "Neptune",
    } <= names

    moon_names = {body["name"] for body in planets if body.get("body_type") == "moon"}
    assert {"Moon", "Europa", "Titan"} <= moon_names


def test_generator_rules_and_colonizable_body():
    rng = random.Random(123)
    generator = SystemGenerator()
    generated = generator.generate_system("sys_test", "Test", rng, use_known=False)

    orbit_indices = [body.get("orbit_index") for body in generated.planets]
    assert len(set(orbit_indices)) == len(orbit_indices)

    inner_orbits = [body for body in generated.planets if body.get("orbit_index") <= 2]
    assert all(body.get("type") != "gas_giant" for body in inner_orbits)

    assert any(body.get("colonizable") for body in generated.planets)
