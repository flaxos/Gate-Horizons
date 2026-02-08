"""Tests for trade route capacity based on freighters and latency."""

import unittest

from gate_horizons.game.trade import TradeManager, TradeRoute
from gate_horizons.game.ships import FleetManager
from gate_horizons.game.colonies import ColonyManager


def _load_fleet() -> FleetManager:
    fleet = FleetManager()
    from importlib import resources as pkg_resources
    ships_path = pkg_resources.files("gate_horizons").joinpath("data", "ships.json")
    fleet.load_templates(ships_path)
    return fleet


class TestTradeCapacity(unittest.TestCase):
    def test_capacity_scales_with_freighters(self):
        fleet = _load_fleet()
        freighter = fleet.create_ship("small_freighter", "sys_a", "ISS Hauler")

        route = TradeRoute(
            source_system="sys_a",
            destination_system="sys_b",
            capacity_per_turn=5,
            latency_turns=1,
            resource_manifest={"outbound": {"metals": 20}, "inbound": {}},
        )
        route.assigned_ships = [freighter.id]

        throughput = route.calculate_throughput(fleet=fleet, tech_effects={})
        self.assertEqual(throughput["outbound"]["metals"], 13)

    def test_latency_queue_arrival(self):
        fleet = _load_fleet()
        freighter = fleet.create_ship("small_freighter", "sys_a", "ISS Runner")

        trade = TradeManager()
        route = TradeRoute(
            source_system="sys_a",
            destination_system="sys_b",
            capacity_per_turn=0,
            latency_turns=2,
            resource_manifest={"outbound": {"metals": 5}, "inbound": {}},
        )
        route.assigned_ships = [freighter.id]
        trade.routes[route.id] = route

        colonies = ColonyManager()
        col_a = colonies.establish_colony("sys_a", "p_a", "Colony A", 100, 1)
        col_b = colonies.establish_colony("sys_b", "p_b", "Colony B", 100, 1)
        col_a.stockpiles["metals"] = 10

        trade.compute_and_ship(colonies=colonies, fleet=fleet)
        self.assertEqual(len(trade.in_transit), 1)

        arrivals = trade.process_arrivals(colonies=colonies)
        self.assertEqual(arrivals, [])
        self.assertEqual(col_b.stockpiles["metals"], 0)

        arrivals = trade.process_arrivals(colonies=colonies)
        self.assertEqual(len(arrivals), 1)
        self.assertEqual(col_b.stockpiles["metals"], 5)


if __name__ == "__main__":
    unittest.main(verbosity=2)
