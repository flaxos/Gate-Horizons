"""Headless test harness for Gate Horizons game engine.

Runs 10 turns without UI and prints results to verify the engine works.
"""

import os
import sys
import json
import tempfile

# Add parent to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from game.state import GameState
from game.save_load import SaveManager


def print_separator():
    print("=" * 60)


def print_resources(state):
    r = state.resources.global_resources
    net = state.resources.get_net_summary()
    print("  Resources:")
    for res in ["energy", "metals", "exotics", "credits", "intel"]:
        delta = net.get(res, 0)
        sign = "+" if delta >= 0 else ""
        print(f"    {res:>8s}: {r.get(res, 0):>5d} ({sign}{delta}/turn)")


def print_ships(state):
    print(f"  Ships ({len(state.fleet.ships)}):")
    for ship in state.fleet.ships.values():
        mission = ship.mission or "idle"
        print(f"    {ship.name} ({ship.ship_class}) @ {ship.location} "
              f"[hull:{ship.hull}/{ship.stats.max_hull} fuel:{ship.fuel}] mission:{mission}")


def print_colonies(state):
    print(f"  Colonies ({len(state.colonies.colonies)}):")
    for sid, colony in state.colonies.colonies.items():
        tier = colony.get_tier()
        print(f"    {colony.name} @ {sid} | pop:{colony.population} "
              f"happy:{colony.happiness}% tier:{tier}")
        for infra, data in colony.infrastructure.items():
            building = " (BUILDING)" if data.get("building") else ""
            print(f"      {infra}: level {data.get('level', 0)}{building}")


def print_galaxy(state):
    discovered = sum(1 for s in state.galaxy.systems.values() if s.discovered)
    surveyed = sum(1 for s in state.galaxy.systems.values() if s.surveyed)
    total = len(state.galaxy.systems)
    print(f"  Galaxy: {discovered}/{total} discovered, {surveyed}/{total} surveyed")


def print_tech(state):
    researched = state.tech.get_researched_techs()
    active = state.tech.active_research
    print(f"  Tech: {len(researched)} researched", end="")
    if active:
        tech = state.tech.techs.get(active)
        print(f", researching: {tech.name} ({tech.turns_remaining} turns left)", end="")
    print()


def run_test():
    print_separator()
    print("GATE HORIZONS — Headless Test Harness")
    print_separator()

    # Create new game
    print("\n[1] Creating new game...")
    state = GameState.new_game()
    print(f"  Turn: {state.turn_number} — {state.game_time}")
    print_galaxy(state)
    print_resources(state)
    print_ships(state)
    print_colonies(state)
    print_tech(state)

    # Issue starting orders
    print_separator()
    print("\n[2] Issuing starting orders...")

    # Find scout and send to Alpha Centauri
    scout = None
    freighter = None
    for ship in state.fleet.ships.values():
        if ship.ship_class == "scout":
            scout = ship
        elif ship.ship_class == "freighter":
            freighter = ship

    if scout:
        result = state.fleet.move_ship(scout.id, "alpha_centauri", state.galaxy)
        print(f"  Sent {scout.name} to Alpha Centauri: {'OK' if result else 'FAILED'}")
        if result:
            print(f"    Path: {scout.path}")

    # Start building a miner at Sol
    if state.resources.can_afford({"credits": 60, "metals": 35}):
        state.resources.spend_dict({"credits": 60, "metals": 35})
        miner = state.fleet.create_ship("miner", "sol", "ISS Excavator")
        print(f"  Built miner: {miner.name} (id: {miner.id})")
    else:
        print("  Can't afford miner")

    # Start researching
    available_techs = state.tech.get_available_techs()
    if available_techs:
        tech = available_techs[0]
        started = state.tech.start_research(tech.id, state.resources)
        print(f"  Started research: {tech.name} ({'OK' if started else 'FAILED'})")

    # Start building industry at Earth
    colony = state.colonies.colonies.get("sol")
    if colony:
        cost = colony.get_build_cost("industry")
        if state.resources.can_afford(cost):
            state.resources.spend_dict(cost)
            colony.start_construction("industry")
            print(f"  Started building industry at Earth (cost: {cost})")

    # Process 10 turns
    print_separator()
    print("\n[3] Processing 10 turns...")

    for i in range(10):
        report = state.process_turn()
        print(f"\n  --- Turn {report.turn_number}: {report.game_date} ---")

        for line in report.get_summary_lines()[2:]:  # Skip header
            if line:
                print(f"    {line}")

        if not report.get_summary_lines()[2:]:
            print("    (quiet turn)")

        # On turn 3, send scout somewhere else if it arrived
        if i == 2 and scout and not scout.path:
            next_dest = "sirius"
            result = state.fleet.move_ship(scout.id, next_dest, state.galaxy)
            if result:
                print(f"    >> Ordered {scout.name} to {next_dest}")

        # On turn 5, set a miner to mining if at Sol
        if i == 4:
            for ship in state.fleet.ships.values():
                if ship.ship_class == "miner" and ship.location == "sol":
                    ship.mining = True
                    print(f"    >> Set {ship.name} to mining at Sol")

    # Print final state
    print_separator()
    print("\n[4] Final state after 10 turns:")
    print(f"  Turn: {state.turn_number} — {state.game_time}")
    print_galaxy(state)
    print_resources(state)
    print_ships(state)
    print_colonies(state)
    print_tech(state)

    # Test save/load
    print_separator()
    print("\n[5] Testing save/load...")

    with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as tmp:
        db_path = tmp.name

    try:
        save_mgr = SaveManager(db_path)

        # Save
        save_id = save_mgr.save_game(state, "test_save")
        print(f"  Saved game (id: {save_id})")

        # List saves
        saves = save_mgr.list_saves()
        print(f"  Saves: {len(saves)}")
        for s in saves:
            print(f"    {s['save_name']} — Turn {s['turn_number']} ({s['timestamp']})")

        # Load
        loaded = save_mgr.load_game(save_id, GameState)
        print(f"  Loaded game: Turn {loaded.turn_number} — {loaded.game_time}")
        print(f"  Ships: {len(loaded.fleet.ships)}")
        print(f"  Colonies: {len(loaded.colonies.colonies)}")

        # Verify state matches
        orig_dict = state.to_dict()
        loaded_dict = loaded.to_dict()

        # Compare key fields
        match = True
        if orig_dict["turn_number"] != loaded_dict["turn_number"]:
            print("  MISMATCH: turn_number")
            match = False
        if orig_dict["resources"]["global_resources"] != loaded_dict["resources"]["global_resources"]:
            print("  MISMATCH: resources")
            match = False
        if len(orig_dict["fleet"]["ships"]) != len(loaded_dict["fleet"]["ships"]):
            print("  MISMATCH: ship count")
            match = False
        if len(orig_dict["colonies"]["colonies"]) != len(loaded_dict["colonies"]["colonies"]):
            print("  MISMATCH: colony count")
            match = False

        if match:
            print("  Save/Load round-trip: PASSED")
        else:
            print("  Save/Load round-trip: FAILED")

        # Auto-save test
        auto_id = save_mgr.auto_save(state)
        print(f"  Auto-save: OK (id: {auto_id})")

    finally:
        os.unlink(db_path)

    print_separator()
    print("\nAll tests completed successfully!")
    print_separator()


if __name__ == "__main__":
    run_test()
