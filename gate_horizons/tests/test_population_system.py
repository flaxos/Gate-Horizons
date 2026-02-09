"""Tests for population system mechanics."""

from gate_horizons.game.colonies import Colony, DEFAULT_INFRASTRUCTURE
from gate_horizons.sim.population import PopulationSimulator


def _infra_with_levels(overrides=None):
    infra = {k: dict(v) for k, v in DEFAULT_INFRASTRUCTURE.items()}
    for key, level in (overrides or {}).items():
        infra[key]["level"] = level
    return infra


def test_population_deterministic_turns():
    colony = Colony(
        system_id="test",
        planet_id="p1",
        name="Test",
        population=500,
        health_index=60,
        education_index=40,
        pollution_index=10,
        infrastructure=_infra_with_levels({
            "housing": 2,
            "industry": 1,
            "research": 1,
            "power": 1,
        }),
    )

    for _ in range(5):
        colony.process_turn()

    assert colony.population_units == 521


def test_high_education_health_slows_growth():
    base_infra = _infra_with_levels({"housing": 2, "research": 1, "power": 1})
    low = Colony(
        system_id="low",
        planet_id="p1",
        population=400,
        health_index=30,
        education_index=20,
        pollution_index=10,
        infrastructure=base_infra,
    )
    high = Colony(
        system_id="high",
        planet_id="p2",
        population=400,
        health_index=80,
        education_index=80,
        pollution_index=10,
        infrastructure=base_infra,
    )

    low_result = PopulationSimulator.simulate_turn(low)
    high_result = PopulationSimulator.simulate_turn(high)

    assert high_result.net_change < low_result.net_change


def test_pollution_can_trigger_population_decline():
    colony = Colony(
        system_id="polluted",
        planet_id="p3",
        population=600,
        health_index=20,
        education_index=10,
        pollution_index=50,
        infrastructure=_infra_with_levels({
            "housing": 2,
            "industry": 4,
            "mining": 3,
            "power": 0,
            "research": 0,
        }),
    )

    start_pop = colony.population_units
    for _ in range(6):
        colony.process_turn()

    assert colony.population_units < start_pop


def test_population_export_policy_retains_floor():
    colony = Colony(
        system_id="export",
        planet_id="p4",
        population=1000,
        infrastructure=_infra_with_levels({"housing": 3}),
        population_policy={
            "retain_percent": 0.8,
            "export_cap_per_turn": 500,
            "priority": "balanced",
        },
    )

    exportable = colony.get_population_export_available(500)
    assert exportable == 200

    colony.population = colony.population_units - exportable
    assert colony.population_units == 800
