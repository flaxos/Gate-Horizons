from __future__ import annotations

import sys
import types
from types import SimpleNamespace

from gate_horizons.game.ships import Action
from gate_horizons.game.state import GameState


class _DummyWidget:
    def __init__(self, *args, **kwargs):
        pass

    def bind(self, *args, **kwargs):
        return None

    def add_widget(self, *args, **kwargs):
        return None

    def clear_widgets(self, *args, **kwargs):
        return None

    def open(self, *args, **kwargs):
        return None

    def dismiss(self, *args, **kwargs):
        return None


class _DummyClock:
    @staticmethod
    def schedule_interval(*args, **kwargs):
        return None


class _DummyApp:
    @staticmethod
    def get_running_app():
        return None


def _install_kivy_stubs_if_missing():
    if "kivy" in sys.modules:
        return

    module_names = [
        "kivy",
        "kivy.app",
        "kivy.clock",
        "kivy.properties",
        "kivy.metrics",
        "kivy.graphics",
        "kivy.core",
        "kivy.core.window",
        "kivy.uix",
        "kivy.uix.screenmanager",
        "kivy.uix.floatlayout",
        "kivy.uix.boxlayout",
        "kivy.uix.gridlayout",
        "kivy.uix.button",
        "kivy.uix.label",
        "kivy.uix.widget",
        "kivy.uix.popup",
        "kivy.uix.scrollview",
        "kivy.uix.progressbar",
        "kivy.uix.textinput",
        "kivy.uix.dropdown",
        "kivy.uix.togglebutton",
    ]
    for name in module_names:
        sys.modules[name] = types.ModuleType(name)
    sys.modules["kivy"].__path__ = []
    sys.modules["kivy.uix"].__path__ = []

    sys.modules["kivy.app"].App = _DummyApp
    sys.modules["kivy.clock"].Clock = _DummyClock
    sys.modules["kivy.properties"].NumericProperty = lambda default=0, **kwargs: default
    sys.modules["kivy.properties"].StringProperty = lambda default="", **kwargs: default
    sys.modules["kivy.metrics"].dp = lambda value: value

    graphics = sys.modules["kivy.graphics"]
    graphics.Color = _DummyWidget
    graphics.Ellipse = _DummyWidget
    graphics.Line = _DummyWidget
    graphics.Rectangle = _DummyWidget
    graphics.RoundedRectangle = _DummyWidget
    graphics.Triangle = _DummyWidget
    sys.modules["kivy.core.window"].Window = SimpleNamespace(bind=lambda **kwargs: None, unbind=lambda **kwargs: None)

    for module_name, attr in (
        ("kivy.uix.screenmanager", "Screen"),
        ("kivy.uix.floatlayout", "FloatLayout"),
        ("kivy.uix.boxlayout", "BoxLayout"),
        ("kivy.uix.gridlayout", "GridLayout"),
        ("kivy.uix.button", "Button"),
        ("kivy.uix.label", "Label"),
        ("kivy.uix.widget", "Widget"),
        ("kivy.uix.popup", "Popup"),
        ("kivy.uix.scrollview", "ScrollView"),
        ("kivy.uix.progressbar", "ProgressBar"),
        ("kivy.uix.textinput", "TextInput"),
        ("kivy.uix.dropdown", "DropDown"),
        ("kivy.uix.togglebutton", "ToggleButton"),
    ):
        setattr(sys.modules[module_name], attr, _DummyWidget)


def _build_state_with_cargo():
    state = GameState.new_game()
    ship = next(iter(state.fleet.ships.values()))
    ship.cargo["metals"] = 4
    return state, ship.id


def _run_from_galaxy_screen(state, ship_id, action):
    _install_kivy_stubs_if_missing()
    from gate_horizons.ui.screens.galaxy_map import GalaxyMapScreen

    screen = GalaxyMapScreen.__new__(GalaxyMapScreen)
    screen.game_state = state
    screen.refresh = lambda: None
    screen._show_notice = lambda message, title="Notice": None
    screen._show_destination_menu = lambda sid: None
    screen._show_escort_target_menu = lambda sid: None
    screen._execute_action(ship_id, action)


def _run_from_fleet_screen(state, ship_id, action):
    _install_kivy_stubs_if_missing()
    from gate_horizons.ui.screens.fleet_screen import FleetScreen

    screen = FleetScreen.__new__(FleetScreen)
    screen.game_state = state
    screen.top_bar = SimpleNamespace(update=lambda game_state: None)
    screen._update_list = lambda: None
    screen._on_move = lambda btn: None
    screen._execute_action(ship_id, action)


def _run_from_gravity_well_screen(state, ship_id, action):
    _install_kivy_stubs_if_missing()
    from gate_horizons.ui.screens.gravity_well_map import GravityWellScreen

    screen = GravityWellScreen.__new__(GravityWellScreen)
    screen.game_state = state
    screen.set_game_state = lambda game_state: None
    screen._execute_ship_action(ship_id, action)


def test_ship_action_dispatch_parity_across_screen_entrypoints():
    action = Action(name="Emergency Jettison")

    outcomes = []
    for runner in (
        _run_from_galaxy_screen,
        _run_from_fleet_screen,
        _run_from_gravity_well_screen,
    ):
        state, ship_id = _build_state_with_cargo()
        runner(state, ship_id, action)
        ship = state.fleet.ships[ship_id]
        outcomes.append((dict(ship.cargo), ship.cargo_used, len(state.pending_ship_orders)))

    assert outcomes[0] == outcomes[1] == outcomes[2]
    assert outcomes[0] == ({}, 0, 0)
