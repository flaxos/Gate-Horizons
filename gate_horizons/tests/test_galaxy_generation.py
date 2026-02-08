"""Tests for procedural galaxy generation."""

from gate_horizons.game.galaxy import GalaxyMap


def _serialize_map(galaxy: GalaxyMap) -> dict:
    return {
        sys_id: {
            "x": system.x,
            "y": system.y,
            "tier": system.tier,
            "connections": sorted(system.gate_connections),
        }
        for sys_id, system in sorted(galaxy.systems.items())
    }


def test_procedural_generation_is_deterministic():
    galaxy_a = GalaxyMap()
    galaxy_b = GalaxyMap()

    galaxy_a.generate_procedural(seed=42, system_count=12)
    galaxy_b.generate_procedural(seed=42, system_count=12)

    assert _serialize_map(galaxy_a) == _serialize_map(galaxy_b)


def test_procedural_generation_is_connected():
    galaxy = GalaxyMap()
    galaxy.generate_procedural(seed=7, system_count=12)

    systems = list(galaxy.systems.keys())
    assert systems

    visited = set()
    stack = [systems[0]]
    while stack:
        current = stack.pop()
        if current in visited:
            continue
        visited.add(current)
        stack.extend(galaxy.systems[current].gate_connections)

    assert len(visited) == len(systems)
