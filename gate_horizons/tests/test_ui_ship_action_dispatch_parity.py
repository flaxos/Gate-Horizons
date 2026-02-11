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


def _run_from_fleet_screen_with_notices(state, ship_id, action):
    _install_kivy_stubs_if_missing()
    from gate_horizons.ui.screens.fleet_screen import FleetScreen

    notices = []
    screen = FleetScreen.__new__(FleetScreen)
    screen.game_state = state
    screen.top_bar = SimpleNamespace(update=lambda game_state: None)
    screen._update_list = lambda: None
    screen._on_move = lambda btn: None
    screen._show_notice = lambda message, title="Notice": notices.append((message, title))
    screen._execute_action(ship_id, action)
    return notices


def _run_from_gravity_well_screen(state, ship_id, action):
    _install_kivy_stubs_if_missing()
    from gate_horizons.ui.screens.gravity_well_map import GravityWellScreen

    screen = GravityWellScreen.__new__(GravityWellScreen)
    screen.game_state = state
    screen.set_game_state = lambda game_state: None
    screen._execute_ship_action(ship_id, action)




def _run_toggle_mining_from_fleet(state, ship_id):
    _install_kivy_stubs_if_missing()
    from gate_horizons.ui.screens.fleet_screen import FleetScreen

    screen = FleetScreen.__new__(FleetScreen)
    screen.game_state = state
    screen.top_bar = SimpleNamespace(update=lambda game_state: None)
    screen._update_list = lambda: None
    screen._show_notice = lambda message, title="Notice": None
    btn = SimpleNamespace(ship_id=ship_id)
    screen._toggle_mining(btn)


def _run_unassign_trade_from_fleet(state, ship_id):
    _install_kivy_stubs_if_missing()
    from gate_horizons.ui.screens.fleet_screen import FleetScreen

    screen = FleetScreen.__new__(FleetScreen)
    screen.game_state = state
    screen.top_bar = SimpleNamespace(update=lambda game_state: None)
    screen._update_list = lambda: None
    screen._show_notice = lambda message, title="Notice": None
    btn = SimpleNamespace(ship_id=ship_id)
    screen._unassign_trade(btn)


def _build_state_with_miner():
    state = GameState.new_game()
    miner = next(ship for ship in state.fleet.ships.values() if ship.ship_class == "miner")
    miner.mining = False
    miner.mission = None
    miner.path = []
    miner.destination = None
    return state, miner.id


def _build_state_with_trade_assignment():
    state = GameState.new_game()
    freighter = next(
        ship for ship in state.fleet.ships.values()
        if ship.ship_class in {"freighter", "small_freighter", "medium_freighter", "large_freighter"}
        or "freighter" in (ship.ship_class or "")
    )

    systems = list(state.galaxy.systems.keys())
    route = None
    for source_id in systems:
        for dest_id in systems:
            if source_id == dest_id:
                continue
            route = state.trade.create_route(
                source=source_id,
                dest=dest_id,
                capacity_per_turn=10,
                latency_turns=1,
                manifest={"outbound": {}, "inbound": {}},
                galaxy=state.galaxy,
                ships=[freighter.id],
            )
            if route:
                break
        if route:
            break
    assert route is not None

    freighter.trade_route = route.id
    freighter.mission = "trade"
    freighter.path = [route.destination_system]
    freighter.destination = route.destination_system
    return state, freighter.id, route.id


def _mining_snapshot(state, ship_id):
    ship = state.fleet.ships[ship_id]
    return {
        "mining": ship.mining,
        "mission": ship.mission,
        "path": list(ship.path),
        "destination": ship.destination,
        "pending_last_action": state.pending_ship_actions[-1]["action"] if state.pending_ship_actions else None,
        "log_last": state.log[-1] if state.log else None,
    }


def _trade_unassign_snapshot(state, ship_id, route_id):
    ship = state.fleet.ships[ship_id]
    route = state.trade.routes[route_id]
    return {
        "trade_route": ship.trade_route,
        "mission": ship.mission,
        "path": list(ship.path),
        "destination": ship.destination,
        "assigned_ships": list(route.assigned_ships),
        "pending_last_action": state.pending_ship_actions[-1]["action"] if state.pending_ship_actions else None,
        "log_last": state.log[-1] if state.log else None,
    }
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



def test_toggle_mining_parity_between_fleet_and_galaxy_dispatch():
    fleet_state, fleet_ship_id = _build_state_with_miner()
    _run_toggle_mining_from_fleet(fleet_state, fleet_ship_id)
    fleet_snapshot = _mining_snapshot(fleet_state, fleet_ship_id)

    galaxy_state, galaxy_ship_id = _build_state_with_miner()
    _run_from_galaxy_screen(galaxy_state, galaxy_ship_id, Action(name="Toggle Mining"))
    galaxy_snapshot = _mining_snapshot(galaxy_state, galaxy_ship_id)

    assert fleet_snapshot == galaxy_snapshot


def test_unassign_trade_parity_between_fleet_and_galaxy_dispatch():
    fleet_state, fleet_ship_id, fleet_route_id = _build_state_with_trade_assignment()
    _run_unassign_trade_from_fleet(fleet_state, fleet_ship_id)
    fleet_snapshot = _trade_unassign_snapshot(fleet_state, fleet_ship_id, fleet_route_id)

    galaxy_state, galaxy_ship_id, galaxy_route_id = _build_state_with_trade_assignment()
    _run_from_galaxy_screen(galaxy_state, galaxy_ship_id, Action(name="Unassign Trade Route"))
    galaxy_snapshot = _trade_unassign_snapshot(galaxy_state, galaxy_ship_id, galaxy_route_id)

    assert fleet_snapshot == galaxy_snapshot


def test_fleet_screen_shows_notice_when_dispatch_action_fails():
    state = GameState.new_game()
    ship = next(iter(state.fleet.ships.values()))
    ship.path = ["alpha_centauri"]
    ship.destination = "alpha_centauri"

    notices = _run_from_fleet_screen_with_notices(state, ship.id, Action(name="Refuel"))

    assert notices
    assert notices[0][0] == f"{ship.name} is currently in transit"
