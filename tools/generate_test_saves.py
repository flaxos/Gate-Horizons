#!/usr/bin/env python3
"""Generate deterministic test save files for Gate Horizons.

Usage:
    python tools/generate_test_saves.py

Outputs:
    saves/test_midgame_50pct_tech.json
    saves/test_lategame_100pct_tech.json
    saves/test_sandbox_small.json

All saves are deterministically seeded for reproducibility.
"""

import json
import os
import sys
import random
from pathlib import Path

# Add project root to path
_project_root = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(_project_root))

from gate_horizons.game.state import GameState, CURRENT_SCHEMA_VERSION
from gate_horizons.game.production import ExtractionSite, Factory
from gate_horizons.game.shipyard import OrbitalFacility


SAVE_DIR = _project_root / "saves"
SAVE_DIR.mkdir(exist_ok=True)


def _set_seed(seed: int):
    """Set deterministic RNG."""
    random.seed(seed)


def _discover_systems(state, system_ids):
    """Discover and survey the given systems."""
    for sid in system_ids:
        system = state.galaxy.systems.get(sid)
        if system:
            system.discovered = True
            system.surveyed = True
            system.tier = max(1, system.tier)
            if not system.gate_active:
                system.gate_active = True


def _create_colony(state, system_id, planet_id, name, level=1, pop=200):
    """Create a colony with reasonable infrastructure."""
    colony = state.colonies.establish_colony(
        system_id=system_id,
        planet_id=planet_id,
        name=name,
        initial_pop=pop,
        level=level,
        world_traits=["frontier"],
    )
    if not colony:
        return None

    colony.happiness = 60 + random.randint(0, 25)
    colony.stability = 55 + random.randint(0, 35)

    # Scale infrastructure by level
    infra_levels = {
        0: {"housing": 1, "industry": 1, "power": 1},
        1: {"housing": 2, "industry": 2, "defense": 1, "power": 2, "mining": 1},
        2: {"housing": 3, "industry": 2, "defense": 1, "research": 1, "spaceport": 1, "power": 2, "mining": 1, "logistics": 1},
        3: {"housing": 4, "industry": 3, "defense": 2, "research": 2, "spaceport": 2, "power": 3, "mining": 2, "logistics": 2},
    }
    levels = infra_levels.get(min(level, 3), infra_levels[1])
    for infra_type, infra_level in levels.items():
        colony.infrastructure[infra_type]["level"] = infra_level

    # Stockpiles
    colony.stockpiles = {
        "energy": 10 + level * 15 + random.randint(0, 20),
        "metals": 8 + level * 10 + random.randint(0, 15),
        "exotics": level * 3 + random.randint(0, 5),
        "credits": 20 + level * 20 + random.randint(0, 30),
        "intel": level * 2 + random.randint(0, 3),
    }

    # Extraction sites
    colony.extraction_sites = [
        ExtractionSite(resource_id="ore_iron", base_yield=2 + level, level=min(level + 1, 3)),
        ExtractionSite(resource_id="silicates", base_yield=1 + level, level=min(level, 2)),
    ]

    # Production inventory
    colony.production_inventory["ore_iron"] = 5 + level * 5
    colony.production_inventory["metal_alloys"] = 3 + level * 4

    # Factories at higher levels
    if level >= 2:
        colony.factories.append(Factory(active=True, current_recipe="alloy_smelting"))

    return colony


def _create_ships(state, system_id, specs):
    """Create ships at a system. specs is list of (class, name)."""
    for ship_class, name in specs:
        state.fleet.create_ship(ship_class, system_id, name)


def _research_techs(state, tech_ids):
    """Force-research specific techs (bypasses cost/time)."""
    for tid in tech_ids:
        tech = state.tech.techs.get(tid)
        if tech:
            tech.researched = True
            tech.researching = False
            tech.turns_remaining = 0
    state.tech.active_research = None


def _add_resources(state, resources_dict):
    """Add global resources."""
    for res, amount in resources_dict.items():
        state.resources.add(res, amount)


def _add_shipyard(state, system_id, level=1):
    """Add orbital shipyard to a system."""
    state.shipyard.facilities[system_id] = [
        OrbitalFacility(facility_type="spaceport", level=level),
    ]


# ======================================================================
# Midgame save: ~50% tech, 6 colonies, moderate fleet
# ======================================================================

def generate_midgame(seed=42):
    """Generate a midgame save (~turn 30, 50% tech, 6 colonies)."""
    _set_seed(seed)

    state = GameState.new_game()

    # Advance to turn 30
    state.turn_number = 30
    state.game_time = "July 2159"
    state.game_clock.turn_number = 30

    # Discover roughly half the galaxy
    discovered = [
        "sol", "alpha_centauri", "sirius", "tau_ceti",
        "barnards_star", "epsilon_eridani",
    ]
    _discover_systems(state, discovered)

    # Research ~50% of techs (10 of ~20)
    midgame_techs = [
        "efficient_drives", "gate_resonance", "reinforced_hulls",
        "rapid_construction", "deep_scan", "colonisation", "logistics_1",
        "advanced_mining", "burst_drives", "predictive_analysis",
    ]
    _research_techs(state, midgame_techs)

    # Set one currently researching
    tech = state.tech.techs.get("industrial_processing")
    if tech:
        tech.researching = True
        tech.turns_remaining = 2
        state.tech.active_research = "industrial_processing"

    # Resources (accumulated over 30 turns)
    state.resources.global_resources = {
        "energy": 180,
        "metals": 120,
        "exotics": 35,
        "credits": 350,
        "intel": 45,
    }

    # Upgrade Earth colony to level 3
    earth_colony = state.colonies.colonies.get("sol")
    if earth_colony:
        earth_colony.level = 3
        earth_colony.population = 850
        earth_colony.happiness = 78
        earth_colony.stability = 82
        earth_colony.infrastructure["housing"]["level"] = 4
        earth_colony.infrastructure["industry"]["level"] = 3
        earth_colony.infrastructure["defense"]["level"] = 2
        earth_colony.infrastructure["research"]["level"] = 2
        earth_colony.infrastructure["spaceport"]["level"] = 2
        earth_colony.infrastructure["power"]["level"] = 3
        earth_colony.infrastructure["mining"]["level"] = 2
        earth_colony.infrastructure["logistics"]["level"] = 2
        earth_colony.factories.append(Factory(active=True, current_recipe="alloy_smelting"))
        earth_colony.factories.append(Factory(active=True, current_recipe="electronics_assembly"))

    # Additional colonies
    _create_colony(state, "alpha_centauri", "ac_haven", "Haven Colony", level=2, pop=350)
    _add_shipyard(state, "alpha_centauri", level=1)

    _create_colony(state, "tau_ceti", "tc_pelagius", "Pelagius Station", level=1, pop=150)
    _create_colony(state, "epsilon_eridani", "ee_arcadia", "Arcadia Outpost", level=1, pop=120)
    _create_colony(state, "sirius", "si_inferno", "Inferno Mining Post", level=0, pop=60)

    # Fleet: more ships than starting
    _create_ships(state, "alpha_centauri", [
        ("scout", "ISS Discovery"),
        ("corvette", "ISS Guardian"),
        ("freighter", "ISS Prospector"),
    ])
    _create_ships(state, "tau_ceti", [
        ("scout", "ISS Voyager"),
        ("miner", "ISS Driller"),
    ])
    _create_ships(state, "sirius", [
        ("corvette", "ISS Defender"),
    ])

    # Game log
    state.log = [
        "Game started - January 2157",
        "Alpha Centauri discovered and surveyed",
        "Colonisation technology researched",
        "Haven Colony founded",
        "Tau Ceti explored",
        "Pelagius Station established",
        "Epsilon Eridani explored",
        "Arcadia Outpost founded",
    ]

    return state


# ======================================================================
# Lategame save: 100% tech, 10+ colonies, large fleet, active logistics
# ======================================================================

def generate_lategame(seed=1337):
    """Generate a lategame save (~turn 80, all tech, 10 colonies, big fleet)."""
    _set_seed(seed)

    state = GameState.new_game()

    # Advance to turn 80
    state.turn_number = 80
    state.game_time = "September 2163"
    state.game_clock.turn_number = 80

    # Discover everything
    all_systems = list(state.galaxy.systems.keys())
    _discover_systems(state, all_systems)

    # Research ALL techs
    all_tech_ids = list(state.tech.techs.keys())
    _research_techs(state, all_tech_ids)

    # Massive resources
    state.resources.global_resources = {
        "energy": 800,
        "metals": 600,
        "exotics": 200,
        "credits": 1500,
        "intel": 120,
    }

    # Upgrade Earth to max
    earth_colony = state.colonies.colonies.get("sol")
    if earth_colony:
        earth_colony.level = 3
        earth_colony.population = 1200
        earth_colony.happiness = 85
        earth_colony.stability = 90
        for infra_type in earth_colony.infrastructure:
            earth_colony.infrastructure[infra_type]["level"] = 4
        earth_colony.factories = [
            Factory(active=True, current_recipe="alloy_smelting"),
            Factory(active=True, current_recipe="electronics_assembly"),
            Factory(active=True, current_recipe="composite_fabrication"),
        ]
        earth_colony.stockpiles = {
            "energy": 200, "metals": 150, "exotics": 60,
            "credits": 300, "intel": 40,
        }

    # Create colonies across the galaxy
    colony_specs = [
        ("alpha_centauri", "ac_haven", "Haven", 3, 600),
        ("tau_ceti", "tc_pelagius", "Pelagius Prime", 2, 400),
        ("epsilon_eridani", "ee_arcadia", "Arcadia", 2, 350),
        ("epsilon_eridani", "ee_ferros", "Ferros Industrial", 1, 200),
        ("sirius", "si_inferno", "Inferno Station", 1, 180),
        ("sixty_one_cygni", "sc_geminus_a", "Geminus Colony", 2, 300),
        ("procyon", "pr_anchorage", "Anchorage Depot", 1, 150),
        ("luytens_star", "ls_frostholme", "Frostholme Research", 0, 80),
        ("ross_128", "r128_whisper", "Whisper Outpost", 1, 120),
        ("kapteyns_star", "ks_remnant", "Remnant Excavation", 0, 50),
    ]
    for sys_id, planet_id, name, level, pop in colony_specs:
        # Make colonizable if needed
        system = state.galaxy.systems.get(sys_id)
        if system:
            for p in system.planets:
                if p.id == planet_id:
                    p.colonizable = True
        _create_colony(state, sys_id, planet_id, name, level, pop)

    # Shipyards at major colonies
    for sys_id in ["sol", "alpha_centauri", "tau_ceti", "sixty_one_cygni", "procyon"]:
        _add_shipyard(state, sys_id, level=2)

    # Large fleet spread across systems
    fleet_specs = [
        ("sol", [
            ("corvette", "ISS Sentinel"),
            ("corvette", "ISS Vanguard"),
            ("freighter", "ISS Atlas"),
            ("scout", "ISS Pathfinder"),
        ]),
        ("alpha_centauri", [
            ("corvette", "ISS Guardian"),
            ("corvette", "ISS Warden"),
            ("scout", "ISS Discovery"),
            ("freighter", "ISS Prospector"),
            ("miner", "ISS Excavator"),
        ]),
        ("tau_ceti", [
            ("corvette", "ISS Triton"),
            ("freighter", "ISS Merchant"),
            ("miner", "ISS Deepcore"),
        ]),
        ("sirius", [
            ("corvette", "ISS Firebrand"),
            ("scout", "ISS Beacon"),
        ]),
        ("epsilon_eridani", [
            ("freighter", "ISS Caravan"),
            ("miner", "ISS Ironclad"),
        ]),
        ("sixty_one_cygni", [
            ("corvette", "ISS Geminus Guard"),
            ("freighter", "ISS Tradewind"),
        ]),
        ("procyon", [
            ("scout", "ISS Farseeker"),
            ("freighter", "ISS Goliath Runner"),
        ]),
        ("ross_128", [
            ("scout", "ISS Whisper Scout"),
        ]),
    ]
    for sys_id, ships in fleet_specs:
        _create_ships(state, sys_id, ships)

    # Game log (abbreviated)
    state.log = [
        "Game started - January 2157",
        "Rapid expansion phase complete",
        "All technologies researched",
        f"Turn {state.turn_number}: {len(state.colonies.colonies)} colonies active",
        f"Fleet size: {len(state.fleet.ships)} ships",
    ]

    return state


# ======================================================================
# Sandbox small save: quick-load testing
# ======================================================================

def generate_sandbox(seed=99):
    """Generate a small sandbox save for quick loading tests."""
    _set_seed(seed)

    state = GameState.new_game(
        use_procedural_galaxy=True,
        galaxy_seed=seed,
        system_count=6,
    )

    state.turn_number = 5
    state.game_time = "June 2157"
    state.game_clock.turn_number = 5

    # Discover first few systems
    all_sys = list(state.galaxy.systems.keys())
    _discover_systems(state, all_sys[:3])

    # Basic research
    _research_techs(state, ["efficient_drives", "colonisation"])

    _add_resources(state, {"energy": 30, "metals": 20, "credits": 50})

    state.log = ["Sandbox save generated for testing"]

    return state


# ======================================================================
# Main
# ======================================================================

def validate_save(state, label):
    """Validate a save by round-tripping through to_dict/from_dict."""
    data = state.to_dict()
    assert data["schema_version"] == CURRENT_SCHEMA_VERSION, \
        f"{label}: schema version mismatch"

    restored = GameState.from_dict(data)
    assert restored.turn_number == state.turn_number, \
        f"{label}: turn_number mismatch after round-trip"
    assert len(restored.galaxy.systems) == len(state.galaxy.systems), \
        f"{label}: galaxy systems count mismatch"
    assert len(restored.fleet.ships) == len(state.fleet.ships), \
        f"{label}: fleet ships count mismatch"
    assert len(restored.colonies.colonies) == len(state.colonies.colonies), \
        f"{label}: colonies count mismatch"

    print(f"  [PASS] {label}: round-trip validation OK")
    print(f"         Turn {restored.turn_number}, "
          f"{len(restored.galaxy.systems)} systems, "
          f"{len(restored.fleet.ships)} ships, "
          f"{len(restored.colonies.colonies)} colonies, "
          f"{sum(1 for t in restored.tech.techs.values() if t.researched)} techs researched")
    return data


def main():
    print("Gate Horizons — Test Save Generator")
    print("=" * 50)

    saves = {
        "test_midgame_50pct_tech": (generate_midgame, "Midgame (~50% tech)"),
        "test_lategame_100pct_tech": (generate_lategame, "Lategame (100% tech)"),
        "test_sandbox_small": (generate_sandbox, "Sandbox (small)"),
    }

    for filename, (generator, label) in saves.items():
        print(f"\nGenerating: {label}")
        state = generator()
        data = validate_save(state, label)

        filepath = SAVE_DIR / f"{filename}.json"
        filepath.write_text(json.dumps(data, indent=2), encoding="utf-8")
        print(f"  Saved to: {filepath}")

    print(f"\nAll {len(saves)} saves generated and validated successfully.")


if __name__ == "__main__":
    main()
