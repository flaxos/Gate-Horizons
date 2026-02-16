"""Regression tests for shipyard screen queue actions scoped by selected system."""

from __future__ import annotations

import sys
import types
from types import SimpleNamespace
import unittest

from gate_horizons.game.colonies import Colony
from gate_horizons.game.shipyard import OrbitalFacility
from gate_horizons.game.state import GameState


class _DummyWidget:
    def __init__(self, *args, **kwargs):
        self.text = kwargs.get("text", "")

    def bind(self, *args, **kwargs):
        return None

    def add_widget(self, *args, **kwargs):
        return None

    def clear_widgets(self, *args, **kwargs):
        return None

    def setter(self, *args, **kwargs):
        return lambda *_args, **_kwargs: None


def _install_kivy_stubs_if_missing() -> None:
    if "kivy" in sys.modules:
        return

    module_names = [
        "kivy",
        "kivy.metrics",
        "kivy.graphics",
        "kivy.uix",
        "kivy.uix.screenmanager",
        "kivy.uix.boxlayout",
        "kivy.uix.gridlayout",
        "kivy.uix.button",
        "kivy.uix.label",
        "kivy.uix.scrollview",
        "kivy.properties",
    ]
    for name in module_names:
        sys.modules[name] = types.ModuleType(name)
    sys.modules["kivy"].__path__ = []
    sys.modules["kivy.uix"].__path__ = []

    sys.modules["kivy.metrics"].dp = lambda value: value
    sys.modules["kivy.properties"].NumericProperty = lambda default=0, **kwargs: default
    sys.modules["kivy.properties"].StringProperty = lambda default="", **kwargs: default

    graphics = sys.modules["kivy.graphics"]
    graphics.Color = _DummyWidget
    graphics.Rectangle = _DummyWidget

    for module_name, attr in (
        ("kivy.uix.screenmanager", "Screen"),
        ("kivy.uix.boxlayout", "BoxLayout"),
        ("kivy.uix.gridlayout", "GridLayout"),
        ("kivy.uix.button", "Button"),
        ("kivy.uix.label", "Label"),
        ("kivy.uix.scrollview", "ScrollView"),
    ):
        setattr(sys.modules[module_name], attr, _DummyWidget)


class TestShipyardScreenQueueActions(unittest.TestCase):
    def _make_state_with_two_system_orders(self) -> GameState:
        gs = GameState.new_game()

        sol_colony = gs.colonies.colonies["sol"]
        alpha_colony = Colony(system_id="alpha", planet_id="alpha_prime", name="Alpha")
        gs.colonies.colonies["alpha"] = alpha_colony

        gs.shipyard.facilities.setdefault("sol", []).append(
            OrbitalFacility(id="fac-sol", facility_type="drydock", level=1)
        )
        gs.shipyard.facilities.setdefault("alpha", []).append(
            OrbitalFacility(id="fac-alpha", facility_type="drydock", level=1)
        )

        for colony in (sol_colony, alpha_colony):
            colony.production_inventory.update(
                {
                    "hull_plating": 10,
                    "drive_assemblies": 5,
                    "avionics": 5,
                }
            )
        gs.resources.global_resources["credits"] = 1_000

        self.assertTrue(gs.build_ship_orbital("alpha", "scout", "ALPHA-SCOUT"))
        self.assertTrue(gs.build_ship_orbital("sol", "scout", "SOL-SCOUT"))
        return gs

    def _make_screen(self, game_state: GameState):
        _install_kivy_stubs_if_missing()
        from gate_horizons.ui.screens.shipyard_screen import ShipyardScreen

        screen = ShipyardScreen.__new__(ShipyardScreen)
        screen.game_state = game_state
        screen.selected_system_id = "sol"
        screen.status_label = SimpleNamespace(text="")
        screen.refresh = lambda: None
        return screen

    def test_cancel_oldest_build_only_affects_selected_system_and_refunds_selected_colony(self):
        gs = self._make_state_with_two_system_orders()
        screen = self._make_screen(gs)

        sol_colony = gs.colonies.colonies["sol"]
        alpha_colony = gs.colonies.colonies["alpha"]
        pre_sol_inventory = dict(sol_colony.production_inventory)
        pre_alpha_inventory = dict(alpha_colony.production_inventory)

        screen._cancel_oldest_build(None)

        summary = gs.shipyard.get_build_queue_summary()
        self.assertEqual(len(summary), 1)
        self.assertEqual(summary[0]["name"], "ALPHA-SCOUT")

        scout_components = gs.production.config.to_dict()["ship_blueprints"]["scout"]["components"]
        for component, amount in scout_components.items():
            expected_refund = int(amount * 0.5)
            self.assertEqual(
                sol_colony.production_inventory[component],
                pre_sol_inventory[component] + expected_refund,
            )
            self.assertEqual(
                alpha_colony.production_inventory[component],
                pre_alpha_inventory[component],
            )

    def test_rush_active_build_only_targets_selected_system(self):
        gs = self._make_state_with_two_system_orders()
        screen = self._make_screen(gs)

        before_summary = {entry["name"]: entry for entry in gs.shipyard.get_build_queue_summary()}
        before_credits = gs.resources.global_resources["credits"]

        screen._rush_active_build(None)

        after_summary = {entry["name"]: entry for entry in gs.shipyard.get_build_queue_summary()}
        rush_cost = gs.production.config.to_dict()["shipyard_balance"]["rush_cost_per_turn"]

        self.assertEqual(
            after_summary["SOL-SCOUT"]["turns_left"],
            before_summary["SOL-SCOUT"]["turns_left"] - 1,
        )
        self.assertEqual(
            after_summary["ALPHA-SCOUT"]["turns_left"],
            before_summary["ALPHA-SCOUT"]["turns_left"],
        )
        self.assertEqual(
            gs.resources.global_resources["credits"],
            before_credits - rush_cost,
        )


if __name__ == "__main__":
    unittest.main()
