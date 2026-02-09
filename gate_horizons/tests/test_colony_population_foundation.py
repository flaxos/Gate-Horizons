"""Tests for colonization requiring POP units."""

from gate_horizons.game.state import GameState


def test_found_colony_requires_pop_and_consumes():
    state = GameState.new_game()
    target_system = "alpha_centauri"
    system = state.galaxy.systems[target_system]
    target_planet = next(p for p in system.planets if p.colonizable)

    colony_ship = state.fleet.create_ship("colony_ship", target_system, "ISS Colonizer")

    # Enable colonisation tech
    state.tech.techs["colonisation"].researched = True
    state.resources.global_resources.update({
        "credits": 200,
        "metals": 200,
        "energy": 200,
    })

    starter = state.colonies.get_starter_cargo_requirement()
    for resource, amount in starter.items():
        colony_ship.add_cargo(resource, amount)

    success, message = state.found_colony(target_system, target_planet.id, ship_id=colony_ship.id)
    assert not success
    assert "POP" in message

    colonists_required = state.colonies.get_colonist_requirement()
    colony_ship.add_cargo("pop", colonists_required)

    success, message = state.found_colony(target_system, target_planet.id, ship_id=colony_ship.id)
    assert success, message

    colony = state.colonies.colonies.get(target_system)
    assert colony is not None
    assert colony.population_units == colonists_required
    assert colony_ship.cargo.get("pop", 0) == 0
