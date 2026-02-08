"""Tests for per-colony resource ledger calculations."""

import unittest

from gate_horizons.game.galaxy import GalaxyMap, StarSystem, Planet
from gate_horizons.game.ships import FleetManager
from gate_horizons.game.resources import ResourceManager
from gate_horizons.game.colonies import ColonyManager
from gate_horizons.game.trade import TradeManager
from gate_horizons.game.tech import TechTree
from gate_horizons.game.turn import TurnProcessor
from gate_horizons.game.clock import GameClock
from gate_horizons.game.combat import CombatResolver
from gate_horizons.game.events import EventEngine


class MinimalState:
    pass


def make_state(with_second_colony: bool = False) -> MinimalState:
    state = MinimalState()
    state.galaxy = GalaxyMap()
    state.galaxy.systems["system_a"] = StarSystem(
        id="system_a",
        name="Core",
        x=0.2,
        y=0.5,
        discovered=True,
        surveyed=True,
        tier=1,
        gate_connections=["system_b"] if with_second_colony else [],
        gate_active=True,
        planets=[
            Planet(
                id="planet_a",
                name="Core",
                type="garden",
                colonizable=True,
                resources={"energy": 5, "metals": 5},
                habitability=0.9,
                gravity=1.0,
            ),
        ],
    )
    if with_second_colony:
        state.galaxy.systems["system_b"] = StarSystem(
            id="system_b",
            name="Frontier",
            x=0.8,
            y=0.5,
            discovered=True,
            surveyed=True,
            tier=2,
            gate_connections=["system_a"],
            gate_active=True,
            planets=[
                Planet(
                    id="planet_b",
                    name="Frontier",
                    type="rocky",
                    colonizable=True,
                    resources={"metals": 2},
                    habitability=0.6,
                    gravity=0.9,
                ),
            ],
        )

    state.fleet = FleetManager()
    state.resources = ResourceManager()
    state.colonies = ColonyManager()
    state.trade = TradeManager()
    state.tech = TechTree()
    state.combat = CombatResolver()
    state.events = EventEngine()
    state.turn_processor = TurnProcessor()
    state.game_clock = GameClock()
    state.turn_number = 0
    state.game_time = "January 2157"
    state.log = []
    state.pending_ship_actions = []

    colony_a = state.colonies.establish_colony(
        system_id="system_a",
        planet_id="planet_a",
        name="Core Colony",
        initial_pop=200,
        level=1,
    )
    colony_a.infrastructure["power"]["level"] = 2
    colony_a.infrastructure["industry"]["level"] = 1
    colony_a.infrastructure["mining"]["level"] = 1

    if with_second_colony:
        colony_b = state.colonies.establish_colony(
            system_id="system_b",
            planet_id="planet_b",
            name="Frontier Outpost",
            initial_pop=120,
            level=0,
        )
        colony_b.infrastructure["power"]["level"] = 1
        colony_b.infrastructure["industry"]["level"] = 0

    return state


class TestColonyLedger(unittest.TestCase):
    def test_balanced_net_delta(self):
        state = make_state()
        colony = state.colonies.colonies["system_a"]
        caps = colony.get_storage_caps()
        for resource, cap in caps.items():
            colony.stockpiles[resource] = cap // 2

        production = colony.calculate_production()
        consumption = colony.calculate_consumption()

        report = state.turn_processor.process_turn(state)
        ledger = report.colony_ledger_entries.get("system_a", {})
        net = ledger.get("net", {})

        expected_energy = production.get("energy", 0) - consumption.get("energy", 0)
        expected_metals = production.get("metals", 0) - consumption.get("metals", 0)

        self.assertEqual(net.get("energy", 0), expected_energy)
        self.assertEqual(net.get("metals", 0), expected_metals)

    def test_export_heavy_net_delta(self):
        state = make_state(with_second_colony=True)
        colony = state.colonies.colonies["system_a"]
        caps = colony.get_storage_caps()
        for resource, cap in caps.items():
            colony.stockpiles[resource] = cap // 2
        colony.stockpiles["metals"] = 30

        route = state.trade.create_route(
            source="system_a",
            dest="system_b",
            capacity_per_turn=5,
            latency_turns=2,
            manifest={"outbound": {"metals": 5}, "inbound": {}},
            galaxy=state.galaxy,
            colonies=state.colonies,
        )
        self.assertIsNotNone(route)

        production = colony.calculate_production()
        consumption = colony.calculate_consumption()

        report = state.turn_processor.process_turn(state)
        ledger = report.colony_ledger_entries.get("system_a", {})
        net = ledger.get("net", {})
        exports = ledger.get("exports", {})

        self.assertEqual(exports.get("metals", 0), 5)
        expected_metals = production.get("metals", 0) - consumption.get("metals", 0) - 5
        self.assertEqual(net.get("metals", 0), expected_metals)


if __name__ == "__main__":
    unittest.main(verbosity=2)
