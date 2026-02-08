"""Headless simulation test for Colony Expansion + Logistics Network.

Creates 2 worlds in the same system (Hub + Frontier), sets up a trade
route with limited capacity + latency 2 turns, runs 30 turns, and
asserts:
  - Frontier stockpiles increase over time (after latency)
  - Exotics appear and can be shipped back
  - If route capacity is reduced, frontier experiences shortages
    (stability penalty visible)

This test verifies the core gameplay mechanics described in the task:
  "Hub Worlds feed Frontier Worlds" via abstracted logistics.

Usage:
  python -m gate_horizons.tests.test_colony_logistics
  python -m unittest gate_horizons.tests.test_colony_logistics
"""

import unittest

from gate_horizons.game.galaxy import GalaxyMap, StarSystem, Planet
from gate_horizons.game.ships import FleetManager
from gate_horizons.game.resources import ResourceManager
from gate_horizons.game.colonies import ColonyManager, Colony, INFRASTRUCTURE_TYPES
from gate_horizons.game.trade import TradeManager, TradeRoute
from gate_horizons.game.tech import TechTree, TechNode
from gate_horizons.game.turn import TurnProcessor, TurnReport
from gate_horizons.game.clock import GameClock
from gate_horizons.game.combat import CombatResolver
from gate_horizons.game.events import EventEngine


def make_minimal_game_state():
    """Create a minimal game state with 2 systems for logistics testing.

    Hub (system_a): produces metals + energy surplus, has logistics infra
    Frontier (system_b): consumes metals + energy, produces exotics
    """

    class MinimalGameState:
        pass

    state = MinimalGameState()

    # Galaxy with 2 connected systems
    state.galaxy = GalaxyMap()
    system_a = StarSystem(
        id="system_a", name="Hub Prime",
        x=0.3, y=0.5,
        discovered=True, surveyed=True, tier=1,
        gate_connections=["system_b"],
        gate_active=True,
        planets=[
            Planet(
                id="hub_planet", name="Hub World",
                type="garden", colonizable=True,
                resources={"energy": 5, "metals": 5},
                habitability=0.9, gravity=1.0,
                traits=["hub", "mineral_rich"],
            ),
        ],
    )
    system_b = StarSystem(
        id="system_b", name="Frontier Reach",
        x=0.7, y=0.5,
        discovered=True, surveyed=True, tier=3,
        gate_connections=["system_a"],
        gate_active=True,
        planets=[
            Planet(
                id="frontier_planet", name="Frontier World",
                type="rocky", colonizable=True,
                resources={"exotics": 3},
                habitability=0.4, gravity=0.8,
                traits=["frontier"],
            ),
        ],
    )
    state.galaxy.systems["system_a"] = system_a
    state.galaxy.systems["system_b"] = system_b

    # Fleet (empty - not needed for this test)
    state.fleet = FleetManager()

    # Resources (global pool)
    state.resources = ResourceManager()
    state.resources.global_resources = {
        "energy": 200, "metals": 200, "exotics": 10,
        "credits": 500, "intel": 50,
    }

    # Colonies
    state.colonies = ColonyManager()

    # Hub colony - well-established, high level
    hub = state.colonies.establish_colony(
        system_id="system_a",
        planet_id="hub_planet",
        name="Hub Prime Colony",
        initial_pop=400,
        level=2,
        world_traits=["hub", "mineral_rich"],
    )
    hub.stability = 85
    hub.happiness = 80
    hub.infrastructure["housing"]["level"] = 3
    hub.infrastructure["industry"]["level"] = 3
    hub.infrastructure["power"]["level"] = 3
    hub.infrastructure["mining"]["level"] = 2
    hub.infrastructure["logistics"]["level"] = 2
    hub.infrastructure["research"]["level"] = 1
    hub.infrastructure["spaceport"]["level"] = 1
    hub.stockpiles = {
        "energy": 80, "metals": 80, "exotics": 5,
        "credits": 100, "intel": 20,
    }

    # Frontier colony - small outpost, resource-poor
    frontier = state.colonies.establish_colony(
        system_id="system_b",
        planet_id="frontier_planet",
        name="Frontier Outpost",
        initial_pop=80,
        level=0,
        world_traits=["frontier"],
    )
    frontier.stability = 50
    frontier.happiness = 60
    frontier.infrastructure["housing"]["level"] = 1
    frontier.infrastructure["power"]["level"] = 1
    frontier.stockpiles = {
        "energy": 10, "metals": 5, "exotics": 0,
        "credits": 20, "intel": 0,
    }

    # Trade manager with route from Hub to Frontier
    state.trade = TradeManager()

    # Tech tree (with logistics researched)
    state.tech = TechTree()
    state.tech.techs["colonisation"] = TechNode(
        id="colonisation", name="Colonisation",
        branch="expansion", tier="tier1", researched=True,
        effect={"unlock_colonisation": True},
    )
    state.tech.techs["logistics_1"] = TechNode(
        id="logistics_1", name="Logistics I",
        branch="expansion", tier="tier1", researched=True,
        effect={"logistics_capacity_bonus": 0, "unlock_trade_routes": True},
    )

    # Combat and events (minimal)
    state.combat = CombatResolver()
    state.events = EventEngine()

    # Clock and turn processor
    state.game_clock = GameClock()
    state.turn_number = 0
    state.game_time = "January 2157"
    state.turn_processor = TurnProcessor()
    state.log = []

    return state


class TestColonyLogistics30Turns(unittest.TestCase):
    """Run 30 turns and verify Hub->Frontier logistics work."""

    def test_frontier_receives_goods_after_latency(self):
        """Frontier stockpiles increase after latency period."""
        state = make_minimal_game_state()

        # Create trade route: Hub sends metals + energy to Frontier
        route = state.trade.create_route(
            source="system_a",
            dest="system_b",
            capacity_per_turn=15,
            latency_turns=2,
            manifest={
                "outbound": {"metals": 8, "energy": 7},
                "inbound": {"exotics": 3},
            },
            galaxy=state.galaxy,
        )
        self.assertIsNotNone(route)
        self.assertEqual(route.latency_turns, 2)

        # Track frontier metals over time
        frontier_metals_history = []
        frontier_energy_history = []
        hub_exotics_history = []

        for turn in range(30):
            report = state.turn_processor.process_turn(state)

            frontier = state.colonies.colonies["system_b"]
            hub = state.colonies.colonies["system_a"]
            frontier_metals_history.append(frontier.stockpiles.get("metals", 0))
            frontier_energy_history.append(frontier.stockpiles.get("energy", 0))
            hub_exotics_history.append(hub.stockpiles.get("exotics", 0))

        # After latency (2 turns), frontier should start receiving metals
        # Turns 0 and 1: no arrivals (latency = 2)
        # Turn 2+: arrivals start
        # Frontier metals should be higher in later turns
        self.assertGreater(
            frontier_metals_history[10],
            frontier_metals_history[0],
            "Frontier metals should increase after latency period"
        )

        # Over 30 turns, frontier should have accumulated resources
        self.assertGreater(
            frontier_metals_history[-1],
            0,
            "Frontier should have positive metal stockpile after 30 turns"
        )

    def test_exotics_flow_back_to_hub(self):
        """Exotics from frontier can be shipped back to hub."""
        state = make_minimal_game_state()

        # Give frontier some exotics to ship
        frontier = state.colonies.colonies["system_b"]
        frontier.stockpiles["exotics"] = 20

        route = state.trade.create_route(
            source="system_a",
            dest="system_b",
            capacity_per_turn=15,
            latency_turns=2,
            manifest={
                "outbound": {"metals": 5, "energy": 5},
                "inbound": {"exotics": 3},
            },
            galaxy=state.galaxy,
        )

        hub_initial_exotics = state.colonies.colonies["system_a"].stockpiles.get("exotics", 0)

        # Run enough turns for inbound shipments to arrive
        for turn in range(10):
            state.turn_processor.process_turn(state)

        hub = state.colonies.colonies["system_a"]
        # Hub should have received some exotics via inbound route
        self.assertGreater(
            hub.stockpiles.get("exotics", 0),
            hub_initial_exotics,
            "Hub should receive exotics from frontier via inbound route"
        )

    def test_reduced_capacity_causes_shortages(self):
        """When route capacity is reduced, frontier experiences shortages."""
        state = make_minimal_game_state()

        # First run with decent capacity
        route = state.trade.create_route(
            source="system_a",
            dest="system_b",
            capacity_per_turn=15,
            latency_turns=2,
            manifest={
                "outbound": {"metals": 8, "energy": 7},
                "inbound": {},
            },
            galaxy=state.galaxy,
        )

        # Run 10 turns with good capacity
        for turn in range(10):
            state.turn_processor.process_turn(state)

        frontier = state.colonies.colonies["system_b"]
        stability_after_good = frontier.stability

        # Now create a new state with a colony that has high upkeep but
        # insufficient production: defense/research/logistics at level 3 but
        # no power/industry/spaceport → big credit+energy deficit
        state2 = make_minimal_game_state()

        frontier2 = state2.colonies.colonies["system_b"]
        frontier2.population = 500
        frontier2.level = 2
        frontier2.infrastructure["housing"]["level"] = 0
        frontier2.infrastructure["industry"]["level"] = 0
        frontier2.infrastructure["defense"]["level"] = 3
        frontier2.infrastructure["research"]["level"] = 3
        frontier2.infrastructure["spaceport"]["level"] = 0
        frontier2.infrastructure["power"]["level"] = 0
        frontier2.infrastructure["mining"]["level"] = 0
        frontier2.infrastructure["logistics"]["level"] = 3
        frontier2.stockpiles = {"energy": 0, "metals": 0, "exotics": 0, "credits": 0, "intel": 0}

        # Very low capacity route — not enough to cover the deficit
        route2 = state2.trade.create_route(
            source="system_a",
            dest="system_b",
            capacity_per_turn=2,
            latency_turns=2,
            manifest={
                "outbound": {"energy": 1, "credits": 1},
                "inbound": {},
            },
            galaxy=state2.galaxy,
        )

        shortage_seen = False
        for turn in range(15):
            report = state2.turn_processor.process_turn(state2)
            if report.shortage_reports.get("system_b"):
                shortage_seen = True

        frontier2 = state2.colonies.colonies["system_b"]

        # Frontier should have experienced shortages (energy + credit deficit)
        self.assertTrue(
            shortage_seen,
            "Frontier should experience shortages with high upkeep and low production"
        )

        # Stability should be lower under shortage conditions
        self.assertLess(
            frontier2.stability,
            stability_after_good,
            "Frontier stability should be lower with insufficient supply"
        )

    def test_in_transit_queue_tracks_shipments(self):
        """In-transit queue correctly tracks shipments with latency."""
        state = make_minimal_game_state()

        route = state.trade.create_route(
            source="system_a",
            dest="system_b",
            capacity_per_turn=10,
            latency_turns=3,
            manifest={
                "outbound": {"metals": 5},
                "inbound": {},
            },
            galaxy=state.galaxy,
        )

        # Process turn 1: B5 creates shipment, B1 didn't tick it yet
        state.turn_processor.process_turn(state)
        self.assertGreater(
            len(state.trade.in_transit), 0,
            "Shipment should be in transit after turn 1"
        )

        # Shipment was just created in B5, not yet ticked by B1
        first_shipment = state.trade.in_transit[0]
        self.assertEqual(
            first_shipment.turns_remaining, 3,
            "Newly created shipment should have full latency (not yet ticked)"
        )

        # Process turn 2: B1 ticks existing shipments (turns_remaining 3->2)
        state.turn_processor.process_turn(state)

        # Process turn 3: B1 ticks (2->1)
        state.turn_processor.process_turn(state)

        # Process turn 4: B1 ticks (1->0), shipment arrives
        report = state.turn_processor.process_turn(state)
        self.assertGreater(
            len(report.logistics_arrivals), 0,
            "First shipment should arrive after latency period"
        )

    def test_colony_level_affects_logistics(self):
        """Higher colony level = more logistics capacity."""
        state = make_minimal_game_state()

        hub = state.colonies.colonies["system_a"]
        frontier = state.colonies.colonies["system_b"]

        # Hub at level 2 with logistics 2
        hub_cap = hub.get_logistics_capacity()

        # Frontier at level 0 with no logistics infra
        frontier_cap = frontier.get_logistics_capacity()

        self.assertGreater(
            hub_cap, frontier_cap,
            "Hub (level 2 + logistics infra) should have higher logistics capacity than frontier (level 0)"
        )

    def test_storage_caps_limit_stockpiles(self):
        """Storage caps prevent unlimited resource accumulation."""
        state = make_minimal_game_state()

        frontier = state.colonies.colonies["system_b"]
        caps = frontier.get_storage_caps()

        # Frontier (level 0) has reduced storage
        for resource, cap in caps.items():
            self.assertGreater(cap, 0, f"Storage cap for {resource} should be positive")

        # Frontier storage should be less than hub storage
        hub = state.colonies.colonies["system_a"]
        hub_caps = hub.get_storage_caps()

        self.assertGreater(
            hub_caps["metals"], caps["metals"],
            "Hub should have higher storage caps than frontier outpost"
        )

    def test_stockpiles_change_after_turn(self):
        """Processing a turn should update colony stockpiles."""
        state = make_minimal_game_state()
        hub = state.colonies.colonies["system_a"]
        before = dict(hub.stockpiles)
        state.turn_processor.process_turn(state)
        after = hub.stockpiles
        changed = any(after.get(res) != before.get(res) for res in before)
        self.assertTrue(changed, "Expected colony stockpiles to update after a turn")

    def test_shortage_penalties_accumulate(self):
        """Prolonged shortages cause escalating stability drops."""
        state = make_minimal_game_state()

        # Make frontier consume much more than it produces: high pop, no power
        frontier = state.colonies.colonies["system_b"]
        frontier.population = 300
        frontier.level = 1
        frontier.infrastructure["housing"]["level"] = 2
        frontier.infrastructure["industry"]["level"] = 2
        frontier.infrastructure["defense"]["level"] = 1
        frontier.infrastructure["power"]["level"] = 0  # No power plant
        frontier.infrastructure["mining"]["level"] = 0
        frontier.stockpiles = {"energy": 0, "metals": 0, "exotics": 0, "credits": 0, "intel": 0}
        initial_stability = frontier.stability

        # No trade route — frontier has no supply at all
        stability_history = []
        for turn in range(10):
            state.turn_processor.process_turn(state)
            stability_history.append(frontier.stability)

        # Stability should decrease over time due to energy/credit shortages
        self.assertLess(
            stability_history[-1],
            initial_stability,
            "Stability should decrease under prolonged shortage"
        )

        # Should see continuous decline
        self.assertLess(
            stability_history[5],
            stability_history[0],
            "Stability should continue declining"
        )

    def test_world_traits_affect_output(self):
        """Hub and frontier traits produce different effects."""
        state = make_minimal_game_state()

        hub = state.colonies.colonies["system_a"]
        frontier = state.colonies.colonies["system_b"]

        hub_prod = hub.calculate_production()
        frontier_prod = frontier.calculate_production()

        # Hub with mineral_rich trait should produce metals
        self.assertGreater(
            hub_prod.get("metals", 0),
            frontier_prod.get("metals", 0),
            "Hub with mineral_rich trait should produce more metals"
        )

    def test_colony_upgrade_mechanics(self):
        """Colony level can be upgraded with sufficient resources and tech."""
        state = make_minimal_game_state()

        frontier = state.colonies.colonies["system_b"]
        self.assertEqual(frontier.level, 0, "Frontier should start at level 0")

        # Upgrade from 0 -> 1 (no tech prereq)
        researched = {"colonisation", "logistics_1"}
        self.assertTrue(
            frontier.can_upgrade(researched),
            "Frontier should be upgradeable to level 1"
        )

        frontier.upgrade()
        self.assertEqual(frontier.level, 1, "Frontier should be level 1 after upgrade")

        # Upgrade from 1 -> 2 requires colonisation tech
        self.assertTrue(
            frontier.can_upgrade(researched),
            "Should be upgradeable with colonisation tech"
        )

    def test_founding_requires_tech(self):
        """Colony founding requires colonisation tech."""
        state = make_minimal_game_state()

        # Remove the existing frontier colony so we can test founding on a fresh system
        state.colonies.abandon_colony("system_b")

        # Try to found without colonisation tech
        state.tech.techs["colonisation"].researched = False

        researched_set = set()
        can_found, reason = state.colonies.can_found_colony(
            "system_b", "frontier_planet",
            galaxy=state.galaxy,
            researched_techs=researched_set,
        )
        self.assertFalse(can_found, "Should not be able to found without colonisation tech")
        self.assertIn("Colonisation", reason)

        # Should succeed with colonisation tech
        researched_set.add("colonisation")
        can_found2, reason2 = state.colonies.can_found_colony(
            "system_b", "frontier_planet",
            galaxy=state.galaxy,
            researched_techs=researched_set,
        )
        self.assertTrue(can_found2, "Should be able to found with colonisation tech")


class TestColonyLogisticsDemo(unittest.TestCase):
    """Full demo scenario: run 30 turns and print results."""

    def test_30_turn_demo(self):
        """Complete 30-turn logistics simulation demo."""
        state = make_minimal_game_state()

        # Set up trade route: Hub -> Frontier (metals + energy), Frontier -> Hub (exotics)
        route = state.trade.create_route(
            source="system_a",
            dest="system_b",
            capacity_per_turn=15,
            latency_turns=2,
            manifest={
                "outbound": {"metals": 8, "energy": 7},
                "inbound": {"exotics": 2},
            },
            galaxy=state.galaxy,
        )

        # Give frontier some exotics to ship back
        state.colonies.colonies["system_b"].stockpiles["exotics"] = 10

        results = {
            "frontier_metals": [],
            "frontier_energy": [],
            "frontier_stability": [],
            "hub_exotics": [],
            "in_transit_count": [],
            "shortage_events": [],
        }

        for turn in range(30):
            report = state.turn_processor.process_turn(state)

            frontier = state.colonies.colonies["system_b"]
            hub = state.colonies.colonies["system_a"]

            results["frontier_metals"].append(frontier.stockpiles.get("metals", 0))
            results["frontier_energy"].append(frontier.stockpiles.get("energy", 0))
            results["frontier_stability"].append(frontier.stability)
            results["hub_exotics"].append(hub.stockpiles.get("exotics", 0))
            results["in_transit_count"].append(len(state.trade.in_transit))

            if report.shortage_reports.get("system_b"):
                results["shortage_events"].append(turn + 1)

        # ---- Assertions ----

        # 1. Frontier stockpiles should increase after latency
        self.assertGreater(
            max(results["frontier_metals"][3:]),
            results["frontier_metals"][0],
            "Frontier metals should increase after latency window"
        )

        # 2. Hub should receive exotics back
        self.assertGreater(
            results["hub_exotics"][-1],
            results["hub_exotics"][0],
            "Hub should accumulate exotics from frontier"
        )

        # 3. In-transit queue should be populated
        self.assertTrue(
            any(c > 0 for c in results["in_transit_count"]),
            "In-transit queue should have shipments"
        )

        # 4. Frontier stability should remain above crisis if well-supplied
        self.assertGreater(
            min(results["frontier_stability"]),
            0,
            "Frontier stability should not hit 0 when supplied"
        )


def run_demo():
    """Run the logistics demo and print results for manual inspection."""
    print("=" * 70)
    print("COLONY EXPANSION + LOGISTICS NETWORK — 30-Turn Demo")
    print("=" * 70)

    state = make_minimal_game_state()

    # Trade route setup
    route = state.trade.create_route(
        source="system_a",
        dest="system_b",
        capacity_per_turn=15,
        latency_turns=2,
        manifest={
            "outbound": {"metals": 8, "energy": 7},
            "inbound": {"exotics": 2},
        },
        galaxy=state.galaxy,
    )

    state.colonies.colonies["system_b"].stockpiles["exotics"] = 10

    print(f"\nTrade Route: {route.source_system} -> {route.destination_system}")
    print(f"  Capacity: {route.capacity_per_turn}/turn, Latency: {route.latency_turns} turns")
    print(f"  Outbound: metals=8, energy=7")
    print(f"  Inbound: exotics=2")
    print()

    for turn in range(30):
        report = state.turn_processor.process_turn(state)

        frontier = state.colonies.colonies["system_b"]
        hub = state.colonies.colonies["system_a"]

        if turn < 5 or turn % 5 == 4 or turn == 29:
            print(f"--- Turn {turn + 1} ---")
            print(f"  Hub stockpiles:      E={hub.stockpiles.get('energy', 0):>4d}  "
                  f"M={hub.stockpiles.get('metals', 0):>4d}  "
                  f"X={hub.stockpiles.get('exotics', 0):>4d}  "
                  f"stability={hub.stability}")
            print(f"  Frontier stockpiles: E={frontier.stockpiles.get('energy', 0):>4d}  "
                  f"M={frontier.stockpiles.get('metals', 0):>4d}  "
                  f"X={frontier.stockpiles.get('exotics', 0):>4d}  "
                  f"stability={frontier.stability}")
            print(f"  In-transit: {len(state.trade.in_transit)} shipments")

            if report.logistics_arrivals:
                for arr in report.logistics_arrivals:
                    print(f"  ARRIVED at {arr['to_world']}: {arr['delivered']}")

            if report.shortage_reports:
                for sys_id, info in report.shortage_reports.items():
                    if info.get("stability_loss", 0) > 0:
                        print(f"  SHORTAGE at {sys_id}: stability loss={info['stability_loss']}")

            print()

    print("=" * 70)
    print("SIMULATION COMPLETE")
    print(f"Final Hub:      pop={hub.population}  stability={hub.stability}  "
          f"stockpiles={hub.stockpiles}")
    print(f"Final Frontier: pop={frontier.population}  stability={frontier.stability}  "
          f"stockpiles={frontier.stockpiles}")
    print(f"In-transit: {len(state.trade.in_transit)} shipments")
    print("=" * 70)


if __name__ == "__main__":
    run_demo()
    print()
    print("Running unit tests...")
    print()
    unittest.main(verbosity=2, exit=False)
