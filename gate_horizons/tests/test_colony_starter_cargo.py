"""Tests for colony starter cargo validation and UI copy."""

import os
import unittest

from gate_horizons.game.state import GameState


class TestColonyStarterCargo(unittest.TestCase):
    def _prepare_state_with_colony_ship(self):
        state = GameState.new_game()
        tech = state.tech.techs.get("colonisation")
        if tech:
            tech.researched = True
        state.resources.global_resources.update({
            "credits": 200,
            "metals": 200,
            "energy": 200,
        })
        target_system = None
        target_planet = None
        for system in state.galaxy.systems.values():
            if system.id == "sol":
                continue
            for planet in system.planets:
                if planet.colonizable:
                    target_system = system
                    target_planet = planet
                    break
            if target_system:
                break
        self.assertIsNotNone(target_system, "Expected a colonizable system in demo galaxy")
        colony_ship = state.fleet.create_ship("colony_ship", target_system.id, "ISS Ark")
        return state, colony_ship, target_system, target_planet

    def test_establish_colony_order_rejects_missing_starter_cargo(self):
        state, colony_ship, target_system, _ = self._prepare_state_with_colony_ship()
        success, message, order = state.issue_ship_order(
            colony_ship.id,
            "Establish Colony",
            params={"system_id": target_system.id},
        )
        self.assertFalse(success)
        self.assertIn("starter cargo", message.lower())
        self.assertIsNone(order)
        self.assertEqual(len(state.pending_ship_orders), 0)

    def test_establish_colony_order_queues_with_starter_cargo(self):
        state, colony_ship, target_system, _ = self._prepare_state_with_colony_ship()
        starter = state.colonies.get_starter_cargo_requirement()
        for resource, amount in starter.items():
            colony_ship.cargo[resource] = amount

        success, message, order = state.issue_ship_order(
            colony_ship.id,
            "Establish Colony",
            params={"system_id": target_system.id},
        )
        self.assertTrue(success, msg=message)
        self.assertIsNotNone(order)
        self.assertEqual(len(state.pending_ship_orders), 1)


class TestColonyStarterCargoUI(unittest.TestCase):
    def test_system_view_mentions_starter_cargo(self):
        ui_path = os.path.join(
            os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
            "ui", "screens", "system_view.py",
        )
        with open(ui_path, encoding="utf-8") as handle:
            source = handle.read()

        self.assertIn("Starter cargo", source)
