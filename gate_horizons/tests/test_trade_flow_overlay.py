"""Trade flow overlay data mapping tests."""

import unittest

from gate_horizons.game.state import GameState


class TestTradeFlowOverlay(unittest.TestCase):
    def test_build_flow_segments_from_manifest(self):
        state = GameState.new_game()
        system_ids = list(state.galaxy.systems.keys())
        self.assertGreaterEqual(len(system_ids), 2)
        source = system_ids[0]
        destination = system_ids[1]

        path = state.galaxy.get_path(source, destination)
        for system_id in path:
            system = state.galaxy.systems.get(system_id)
            if not system:
                continue
            system.gate_active = True
            system.gate_capacity = 10
            system.gate_status = 1.0

        route = state.trade.create_route(
            source=source,
            dest=destination,
            capacity_per_turn=10,
            latency_turns=1,
            manifest={
                "outbound": {"credits": 5},
                "inbound": {"metals": 3},
            },
            galaxy=state.galaxy,
        )
        self.assertIsNotNone(route)

        segments = state.trade.build_flow_segments(
            colonies=state.colonies,
            fleet=state.fleet,
            tech_effects=state.tech.get_effects(),
            galaxy=state.galaxy,
        )
        resources = {(segment["direction"], segment["resource"]) for segment in segments}
        self.assertIn(("outbound", "credits"), resources)
        self.assertIn(("inbound", "metals"), resources)


if __name__ == "__main__":
    unittest.main(verbosity=2)
