"""Tests for intra-system body-level movement and tick progression."""

from gate_horizons.game.state import GameState
from gate_horizons.game.ships import FleetManager, Ship


class TestIsIntraSystemMove:
    def test_same_system_is_local(self):
        assert FleetManager.is_intra_system_move("sol", "sol") is True

    def test_different_systems_is_not_local(self):
        assert FleetManager.is_intra_system_move("sol", "alpha_centauri") is False


class TestLocalMovement:
    def setup_method(self):
        self.state = GameState.new_game()
        self.system = self.state.galaxy.systems["sol"]
        assert len(self.system.planets) >= 2
        self.origin_body_id = self.system.planets[0].id
        self.target_body_id = self.system.planets[1].id
        self.ship = self.state.fleet.get_ships_at("sol")[0]
        self.ship.body_id = self.origin_body_id

    def test_local_move_starts_body_transit(self):
        ok, msg = self.state.execute_local_move(self.ship.id, self.target_body_id)
        assert ok is True
        assert "transiting locally" in msg.lower()
        assert self.ship.local_destination_body_id == self.target_body_id
        assert self.ship.local_transit_remaining_ticks > 0
        assert self.ship.body_id == self.origin_body_id

    def test_local_tick_progression_does_not_advance_turn(self):
        ok, _ = self.state.execute_local_move(self.ship.id, self.target_body_id)
        assert ok is True

        turn_before = self.state.turn_number
        tick_before = self.state.game_clock.current_tick

        while self.ship.local_transit_remaining_ticks > 0:
            arrivals = self.state.process_local_movement_tick()

        assert self.state.turn_number == turn_before
        assert self.state.game_clock.current_tick > tick_before
        assert self.ship.body_id == self.target_body_id
        assert self.ship.local_destination_body_id is None
        assert any(entry["ship_id"] == self.ship.id for entry in arrivals)

    def test_local_move_rejects_unknown_body(self):
        ok, msg = self.state.execute_local_move(self.ship.id, "missing_body")
        assert ok is False
        assert "body" in msg.lower()

    def test_local_move_state_survives_save_load(self, tmp_path):
        ok, _ = self.state.execute_local_move(self.ship.id, self.target_body_id)
        assert ok is True

        save_path = tmp_path / "local_move.json"
        self.state.save(str(save_path))
        loaded = GameState.from_dict(__import__("json").loads(save_path.read_text()))
        loaded_ship = loaded.fleet.ships[self.ship.id]

        assert loaded_ship.body_id == self.origin_body_id
        assert loaded_ship.local_destination_body_id == self.target_body_id
        assert loaded_ship.local_transit_remaining_ticks == self.ship.local_transit_remaining_ticks


class TestFleetLocalTickProcessor:
    def test_process_local_movement_tick_arrival(self):
        ship = Ship(location="sol", body_id="sol_earth", local_destination_body_id="sol_mars", local_transit_remaining_ticks=1, local_transit_total_ticks=1)
        fm = FleetManager()
        fm.ships[ship.id] = ship

        arrivals = fm.process_local_movement_tick()

        assert len(arrivals) == 1
        assert ship.body_id == "sol_mars"
        assert ship.local_destination_body_id is None
