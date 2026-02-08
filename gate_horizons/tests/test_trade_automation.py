"""Tests for automated trade route allocation."""

import unittest

from gate_horizons.game.trade import TradeManager, TradeRoute
from gate_horizons.game.colonies import ColonyManager


class TestTradeAutomation(unittest.TestCase):
    def test_auto_ships_to_deficits_with_latency(self):
        colonies = ColonyManager()
        source = colonies.establish_colony("sys_a", "p_a", "Source", 100, 1)
        dest = colonies.establish_colony("sys_b", "p_b", "Dest", 100, 1)
        source.stockpiles["metals"] = 10
        source.stockpiles["energy"] = 8

        trade = TradeManager()
        route = TradeRoute(
            source_system="sys_a",
            destination_system="sys_b",
            capacity_per_turn=6,
            latency_turns=2,
            resource_manifest={"outbound": {}, "inbound": {}},
            auto_policy="auto_deficit",
            auto_allowlist=["metals", "energy"],
            auto_max_per_resource={"metals": 4, "energy": 4},
        )
        trade.routes[route.id] = route

        reports = trade.compute_and_ship(colonies=colonies)
        self.assertEqual(len(trade.in_transit), 1)
        self.assertTrue(reports[0]["shipped"])

        shipment = trade.in_transit[0]
        self.assertEqual(shipment.resources.get("metals"), 4)
        self.assertEqual(shipment.resources.get("energy"), 2)
        self.assertEqual(source.stockpiles["metals"], 6)
        self.assertEqual(source.stockpiles["energy"], 6)

        arrivals = trade.process_arrivals(colonies=colonies)
        self.assertEqual(arrivals, [])

        arrivals = trade.process_arrivals(colonies=colonies)
        self.assertEqual(len(arrivals), 1)
        self.assertEqual(dest.stockpiles["metals"], 4)
        self.assertEqual(dest.stockpiles["energy"], 2)

    def test_auto_respects_empty_source_and_full_destination(self):
        colonies = ColonyManager()
        source = colonies.establish_colony("sys_a", "p_a", "Source", 100, 1)
        dest = colonies.establish_colony("sys_b", "p_b", "Dest", 100, 1)

        trade = TradeManager()
        route = TradeRoute(
            source_system="sys_a",
            destination_system="sys_b",
            capacity_per_turn=5,
            latency_turns=1,
            resource_manifest={"outbound": {}, "inbound": {}},
            auto_policy="auto_deficit",
            auto_allowlist=["metals"],
            auto_max_per_resource={"metals": 5},
        )
        trade.routes[route.id] = route

        caps = dest.get_storage_caps()
        dest.stockpiles["metals"] = caps.get("metals", 0)

        trade.compute_and_ship(colonies=colonies)
        self.assertEqual(len(trade.in_transit), 0)

        dest.stockpiles["metals"] = 0
        source.stockpiles["metals"] = 0

        trade.compute_and_ship(colonies=colonies)
        self.assertEqual(len(trade.in_transit), 0)


if __name__ == "__main__":
    unittest.main(verbosity=2)
