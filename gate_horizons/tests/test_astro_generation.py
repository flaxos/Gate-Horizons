"""Tests for astronomy system generation."""

import json
import random
from importlib import resources as pkg_resources

from gate_horizons.astro.known_systems import KnownSystemRegistry
from gate_horizons.astro.system_generator import SystemGenerator
from gate_horizons.game.galaxy import GalaxyMap, Planet, StarSystem


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

    assert all(body.get("semi_major_axis_au", 0) > 0 for body in planets)


def test_generator_rules_and_colonizable_body():
    rng = random.Random(123)
    generator = SystemGenerator()
    generated = generator.generate_system("sys_test", "Test", rng, use_known=False)

    orbit_indices = [body.get("orbit_index") for body in generated.planets]
    assert len(set(orbit_indices)) == len(orbit_indices)

    orbit_aus = [body.get("semi_major_axis_au") for body in generated.planets]
    assert all(au is not None and au > 0 for au in orbit_aus)

    inner_orbits = [body for body in generated.planets if body.get("orbit_index") <= 2]
    assert all(body.get("type") != "gas_giant" for body in inner_orbits)

    assert any(body.get("colonizable") for body in generated.planets)


def test_planet_schema_roundtrip_preserves_semi_major_axis_au():
    planet = Planet.from_dict({
        "id": "p1",
        "name": "Test 1",
        "type": "rocky",
        "orbit_index": 1,
        "semi_major_axis_au": 1.37,
    })

    assert planet.semi_major_axis_au == 1.37
    dumped = planet.to_dict()
    assert dumped["semi_major_axis_au"] == 1.37


def test_demo_galaxy_all_planets_have_semi_major_axis_au():
    """Every planet in the demo galaxy template must have a positive AU value."""
    galaxy_path = pkg_resources.files("gate_horizons").joinpath(
        "data", "galaxy_templates", "demo_galaxy.json"
    )
    data = json.loads(galaxy_path.read_text(encoding="utf-8"))

    for system in data["systems"]:
        for planet in system.get("planets", []):
            au = planet.get("semi_major_axis_au")
            assert au is not None and au > 0, (
                f"{system['id']}/{planet['id']} missing or non-positive semi_major_axis_au"
            )


def test_demo_galaxy_all_planets_have_body_type_and_orbit_index():
    """Every planet in the demo galaxy must have body_type and orbit_index."""
    galaxy_path = pkg_resources.files("gate_horizons").joinpath(
        "data", "galaxy_templates", "demo_galaxy.json"
    )
    data = json.loads(galaxy_path.read_text(encoding="utf-8"))

    valid_body_types = {"terrestrial", "gas_giant", "moon", "asteroid_belt"}

    for system in data["systems"]:
        for planet in system.get("planets", []):
            bt = planet.get("body_type")
            oi = planet.get("orbit_index")
            assert bt in valid_body_types, (
                f"{system['id']}/{planet['id']} has invalid body_type: {bt}"
            )
            assert oi is not None and oi > 0, (
                f"{system['id']}/{planet['id']} missing or invalid orbit_index"
            )


def test_demo_galaxy_au_values_are_ordered_per_system():
    """Within each system, primary bodies' AU values should increase with orbit_index."""
    galaxy_path = pkg_resources.files("gate_horizons").joinpath(
        "data", "galaxy_templates", "demo_galaxy.json"
    )
    data = json.loads(galaxy_path.read_text(encoding="utf-8"))

    for system in data["systems"]:
        primaries = [
            p for p in system.get("planets", [])
            if p.get("body_type") not in ("moon",)
        ]
        primaries.sort(key=lambda p: p.get("orbit_index", 0))
        for i in range(1, len(primaries)):
            prev_au = primaries[i - 1]["semi_major_axis_au"]
            curr_au = primaries[i]["semi_major_axis_au"]
            assert curr_au > prev_au, (
                f"{system['id']}: {primaries[i]['id']} AU ({curr_au}) <= "
                f"previous {primaries[i-1]['id']} AU ({prev_au})"
            )


def test_demo_galaxy_loads_into_galaxy_map():
    """The demo galaxy template loads without errors and all Planet objects have AU data."""
    galaxy_path = pkg_resources.files("gate_horizons").joinpath(
        "data", "galaxy_templates", "demo_galaxy.json"
    )
    galaxy = GalaxyMap()
    galaxy.load_from_json(galaxy_path)

    assert len(galaxy.systems) >= 12
    for system in galaxy.systems.values():
        for planet in system.planets:
            assert isinstance(planet, Planet)
            assert planet.semi_major_axis_au > 0, (
                f"{system.id}/{planet.id} has semi_major_axis_au={planet.semi_major_axis_au}"
            )
            assert planet.body_type != "", (
                f"{system.id}/{planet.id} has empty body_type"
            )


def test_planet_from_dict_defaults_semi_major_axis_au():
    """Loading a planet dict without semi_major_axis_au should default to 0.0 (backward compat)."""
    planet = Planet.from_dict({
        "id": "legacy_p1",
        "name": "Legacy Planet",
        "type": "rocky",
    })
    assert planet.semi_major_axis_au == 0.0
    assert planet.body_type == ""
    assert planet.orbit_index == 0.0


def test_procedural_generation_au_increases_with_orbit_index():
    """Procedurally generated systems should have monotonically increasing AU for primaries."""
    rng = random.Random(42)
    generator = SystemGenerator()
    generated = generator.generate_system("sys_proc", "Procedural", rng, use_known=False)

    primaries = [
        p for p in generated.planets
        if p.get("body_type") != "moon"
    ]
    primaries.sort(key=lambda p: p.get("orbit_index", 0))

    for i in range(1, len(primaries)):
        prev_au = primaries[i - 1]["semi_major_axis_au"]
        curr_au = primaries[i]["semi_major_axis_au"]
        assert curr_au >= prev_au, (
            f"Primary {primaries[i]['id']} AU ({curr_au}) < "
            f"previous {primaries[i-1]['id']} AU ({prev_au})"
        )


def test_star_system_roundtrip_preserves_planet_au():
    """StarSystem to_dict/from_dict should preserve semi_major_axis_au on all planets."""
    system = StarSystem(
        id="test_sys",
        name="Test System",
        planets=[
            {"id": "p1", "name": "Inner", "type": "rocky",
             "body_type": "terrestrial", "orbit_index": 1, "semi_major_axis_au": 0.5},
            {"id": "p2", "name": "Outer", "type": "gas_giant",
             "body_type": "gas_giant", "orbit_index": 2, "semi_major_axis_au": 7.2},
        ],
    )

    data = system.to_dict()
    restored = StarSystem.from_dict(data)

    assert len(restored.planets) == 2
    assert restored.planets[0].semi_major_axis_au == 0.5
    assert restored.planets[1].semi_major_axis_au == 7.2
