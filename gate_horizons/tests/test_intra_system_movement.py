"""Tests for intra-system movement (no turn cost)."""

import pytest
from gate_horizons.game.state import GameState
from gate_horizons.game.ships import FleetManager


class TestIsIntraSystemMove:
    """Test the is_intra_system_move predicate."""

    def test_same_system_is_local(self):
        assert FleetManager.is_intra_system_move("sol", "sol") is True

    def test_different_systems_is_not_local(self):
        assert FleetManager.is_intra_system_move("sol", "alpha_centauri") is False

    def test_empty_origin_is_not_local(self):
        assert FleetManager.is_intra_system_move("", "sol") is False

    def test_none_origin_is_not_local(self):
        assert FleetManager.is_intra_system_move(None, "sol") is False

    def test_none_destination_is_not_local(self):
        assert FleetManager.is_intra_system_move("sol", None) is False


class TestLocalMovement:
    """Test that local moves don't advance the turn counter."""

    def setup_method(self):
        self.state = GameState.new_game()

    def test_local_move_succeeds(self):
        """A ship at sol can do a local move within sol."""
        ships_at_sol = self.state.fleet.get_ships_at("sol")
        assert len(ships_at_sol) > 0
        ship = ships_at_sol[0]
        ok, msg = self.state.execute_local_move(ship.id, "sol")
        assert ok is True

    def test_local_move_does_not_advance_turn(self):
        """Intra-system move must not change the turn number."""
        ships_at_sol = self.state.fleet.get_ships_at("sol")
        ship = ships_at_sol[0]
        turn_before = self.state.turn_number
        ok, _ = self.state.execute_local_move(ship.id, "sol")
        assert ok is True
        assert self.state.turn_number == turn_before

    def test_local_move_does_not_trigger_research(self):
        """Local move must not progress research."""
        self.state.tech.start_research("efficient_drives", self.state.resources)
        turns_before = None
        tech = self.state.tech.techs.get("efficient_drives")
        if tech:
            turns_before = tech.turns_remaining

        ships_at_sol = self.state.fleet.get_ships_at("sol")
        ship = ships_at_sol[0]
        self.state.execute_local_move(ship.id, "sol")

        tech_after = self.state.tech.techs.get("efficient_drives")
        if tech_after and turns_before is not None:
            assert tech_after.turns_remaining == turns_before

    def test_inter_system_move_rejected_by_local(self):
        """execute_local_move must reject cross-system moves."""
        ships_at_sol = self.state.fleet.get_ships_at("sol")
        ship = ships_at_sol[0]
        ok, msg = self.state.execute_local_move(ship.id, "alpha_centauri")
        assert ok is False
        assert "intra-system" in msg.lower() or "inter-system" in msg.lower()

    def test_nonexistent_ship_rejected(self):
        """execute_local_move must reject unknown ship IDs."""
        ok, msg = self.state.execute_local_move("fake_ship_99", "sol")
        assert ok is False

    def test_strategic_move_still_costs_turn(self):
        """Normal inter-system movement via process_turn must still advance turn."""
        ships_at_sol = self.state.fleet.get_ships_at("sol")
        ship = ships_at_sol[0]

        # Set a destination to alpha_centauri (needs gate active)
        ac = self.state.galaxy.systems.get("alpha_centauri")
        if ac:
            ac.discovered = True
            self.state.fleet.move_ship(
                ship.id, "alpha_centauri", self.state.galaxy,
            )
            turn_before = self.state.turn_number
            self.state.process_turn()
            assert self.state.turn_number == turn_before + 1
