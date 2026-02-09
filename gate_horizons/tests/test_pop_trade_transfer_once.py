"""Regression test for POP transfers applying only once per shipment."""

import unittest

from gate_horizons.game.state import GameState
from gate_horizons.game.trade import Shipment


class TestPopTradeTransferOnce(unittest.TestCase):
    def test_pop_transfer_applies_once_per_turn(self):
        state = GameState.new_game()

        state.colonies.establish_colony(
            system_id="alpha_centauri",
            planet_id="ac_haven",
            name="Haven",
            initial_pop=10,
            level=0,
        )

        source = state.colonies.colonies["sol"]
        dest = state.colonies.colonies["alpha_centauri"]
        source.population = 10
        dest.population = 10

        route = state.trade.create_route(
            source="sol",
            dest="alpha_centauri",
            capacity_per_turn=10,
            latency_turns=1,
            manifest={"outbound": {"pop": 3}, "inbound": {}},
            colonies=state.colonies,
            galaxy=state.galaxy,
        )
        self.assertIsNotNone(route)

        state.trade.in_transit.append(Shipment(
            route_id=route.id,
            from_world="sol",
            to_world="alpha_centauri",
            resources={"pop": 3},
            turns_remaining=1,
        ))

        start_source = source.population_units
        start_dest = dest.population_units

        state.process_turn()

        self.assertEqual(source.population_units, start_source - 3)
        self.assertEqual(dest.population_units, start_dest + 3)


if __name__ == "__main__":
    unittest.main()
