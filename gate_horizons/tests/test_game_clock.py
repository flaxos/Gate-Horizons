import unittest

from gate_horizons.game.state import GameState


class TestGameClockGuards(unittest.TestCase):
    def test_economy_no_double_charge_same_tick(self):
        state = GameState.new_game()
        initial_credits = state.resources.global_resources.get("credits", 0)

        state.turn_processor.process_turn(state)
        after_first = state.resources.global_resources.get("credits", 0)

        state.game_clock.current_tick -= 1
        state.game_clock.turn_number -= 1
        state.turn_number = state.game_clock.turn_number

        state.turn_processor.process_turn(state)
        after_second = state.resources.global_resources.get("credits", 0)

        self.assertNotEqual(initial_credits, after_first)
        self.assertEqual(after_first, after_second)

    def test_movement_no_progress_without_destination(self):
        state = GameState.new_game()
        idle_ship = next(iter(state.fleet.ships.values()))

        starting_location = idle_ship.location
        starting_fuel = idle_ship.fuel
        self.assertFalse(idle_ship.path)
        self.assertIsNone(idle_ship.destination)

        state.process_turn()

        self.assertEqual(idle_ship.location, starting_location)
        self.assertEqual(idle_ship.fuel, starting_fuel)


if __name__ == "__main__":
    unittest.main()
