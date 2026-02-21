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
        "kivy.core.text",
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
    sys.modules["kivy.core.text"].Label = _DummyWidget

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


def _first_non_colony_system_id(state):
    colony_systems = set(state.colonies.colonies.keys())
    for system_id in state.galaxy.systems:
        if system_id not in colony_systems:
            return system_id
    raise AssertionError("Expected at least one non-colony system")


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


def _run_from_fleet_screen_with_ui_spies(state, ship_id, action):
    _install_kivy_stubs_if_missing()
    from gate_horizons.ui.screens.fleet_screen import FleetScreen

    screen = FleetScreen.__new__(FleetScreen)
    screen.game_state = state

    called = {
        "destination": 0,
        "escort_target": 0,
        "notice": [],
        "refresh": 0,
    }
    screen._on_move = lambda btn: called.__setitem__("destination", called["destination"] + 1)
    screen._show_escort_target_menu = lambda sid: called.__setitem__("escort_target", called["escort_target"] + 1)
    screen._show_notice = lambda message, title="Notice": called["notice"].append((message, title))
    screen.top_bar = SimpleNamespace(update=lambda game_state: called.__setitem__("refresh", called["refresh"] + 1))
    screen._update_list = lambda: None

    screen._execute_action(ship_id, action)
    return called


def _run_from_gravity_well_screen(state, ship_id, action):
    _install_kivy_stubs_if_missing()
    from gate_horizons.ui.screens.gravity_well_map import GravityWellScreen

    screen = GravityWellScreen.__new__(GravityWellScreen)
    screen.game_state = state
    screen.set_game_state = lambda game_state: None
    screen._execute_ship_action(ship_id, action)


def _run_from_system_view_screen(state, ship_id, action):
    _install_kivy_stubs_if_missing()
    from gate_horizons.ui.screens.system_view import SystemViewScreen

    screen = SystemViewScreen.__new__(SystemViewScreen)
    screen.game_state = state
    screen.system_id = state.fleet.ships[ship_id].location
    screen.top_bar = SimpleNamespace(update=lambda game_state: None)
    screen.refresh = lambda: None
    screen._execute_ship_action(ship_id, action)


def _run_ship_action_entrypoint_with_params(entrypoint, state, ship_id, action, params):
    _install_kivy_stubs_if_missing()
    if entrypoint == "fleet":
        from gate_horizons.ui.screens.fleet_screen import FleetScreen

        screen = FleetScreen.__new__(FleetScreen)
        screen.game_state = state
        screen.top_bar = SimpleNamespace(update=lambda game_state: None)
        screen._update_list = lambda: None
        screen._on_move = lambda btn: None
        screen._show_notice = lambda *args, **kwargs: None
        screen._execute_action(ship_id, action, params=params)
        return
    if entrypoint == "galaxy":
        from gate_horizons.ui.screens.galaxy_map import GalaxyMapScreen

        screen = GalaxyMapScreen.__new__(GalaxyMapScreen)
        screen.game_state = state
        screen.refresh = lambda: None
        screen._show_notice = lambda *args, **kwargs: None
        screen._show_destination_menu = lambda sid: None
        screen._show_escort_target_menu = lambda sid: None
        screen._execute_action(ship_id, action, params=params)
        return
    if entrypoint == "gravity":
        from gate_horizons.ui.screens.gravity_well_map import GravityWellScreen

        screen = GravityWellScreen.__new__(GravityWellScreen)
        screen.game_state = state
        screen.set_game_state = lambda game_state: None
        screen._show_notice = lambda *args, **kwargs: None
        screen._show_destination_menu = lambda sid: None
        screen._show_escort_target_menu = lambda sid: None
        screen._execute_ship_action(ship_id, action, params=params)
        return
    if entrypoint == "system":
        from gate_horizons.ui.screens.system_view import SystemViewScreen

        screen = SystemViewScreen.__new__(SystemViewScreen)
        screen.game_state = state
        screen.system_id = state.fleet.ships[ship_id].location
        screen.top_bar = SimpleNamespace(update=lambda game_state: None)
        screen.refresh = lambda: None
        screen._execute_ship_action(ship_id, action, params=params)
        return
    raise AssertionError(f"Unknown entrypoint: {entrypoint}")


def _run_from_gravity_well_with_ui_spies(state, ship_id, action):
    _install_kivy_stubs_if_missing()
    from gate_horizons.ui.screens.gravity_well_map import GravityWellScreen

    screen = GravityWellScreen.__new__(GravityWellScreen)
    screen.game_state = state

    called = {
        "destination": 0,
        "escort_target": 0,
        "notice": [],
        "refresh": 0,
    }
    screen._show_destination_menu = lambda sid: called.__setitem__("destination", called["destination"] + 1)
    screen._show_escort_target_menu = lambda sid: called.__setitem__("escort_target", called["escort_target"] + 1)
    screen._show_notice = lambda message, title="Notice": called["notice"].append((message, title))
    screen.set_game_state = lambda game_state: called.__setitem__("refresh", called["refresh"] + 1)

    screen._execute_ship_action(ship_id, action)
    return called




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
        _run_from_system_view_screen,
    ):
        state, ship_id = _build_state_with_cargo()
        runner(state, ship_id, action)
        ship = state.fleet.ships[ship_id]
        outcomes.append((dict(ship.cargo), ship.cargo_used, len(state.pending_ship_orders)))

    assert outcomes[0] == outcomes[1] == outcomes[2] == outcomes[3]
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


def test_gravity_well_dispatch_invokes_move_and_escort_follow_up_ui_paths():
    move_state, move_ship_id = _build_state_with_cargo()
    move_calls = _run_from_gravity_well_with_ui_spies(move_state, move_ship_id, Action(name="Move To"))

    escort_state, escort_ship_id = _build_state_with_cargo()
    escort_calls = _run_from_gravity_well_with_ui_spies(escort_state, escort_ship_id, Action(name="Escort"))

    assert move_calls["destination"] == 1
    assert move_calls["escort_target"] == 0
    assert move_calls["notice"] == []
    assert move_calls["refresh"] == 1

    assert escort_calls["destination"] == 0
    assert escort_calls["escort_target"] == 1
    assert escort_calls["notice"] == []
    assert escort_calls["refresh"] == 1


def test_fleet_dispatch_invokes_move_and_escort_follow_up_ui_paths():
    move_state, move_ship_id = _build_state_with_cargo()
    move_calls = _run_from_fleet_screen_with_ui_spies(move_state, move_ship_id, Action(name="Move To"))

    escort_state, escort_ship_id = _build_state_with_cargo()
    escort_calls = _run_from_fleet_screen_with_ui_spies(escort_state, escort_ship_id, Action(name="Escort"))

    assert move_calls["destination"] == 1
    assert move_calls["escort_target"] == 0
    assert move_calls["notice"] == []
    assert move_calls["refresh"] == 1

    assert escort_calls["destination"] == 0
    assert escort_calls["escort_target"] == 1
    assert escort_calls["notice"] == []
    assert escort_calls["refresh"] == 1


def _first_reachable_destination(state, ship_id):
    ship = state.fleet.ships[ship_id]
    for sid in state.galaxy.systems.keys():
        if sid == ship.location:
            continue
        if state.galaxy.get_path(ship.location, sid):
            return sid
    raise AssertionError("Expected at least one reachable destination")


def test_submit_strategic_movement_rejects_active_local_transit():
    state = GameState.new_game()
    ship = next(iter(state.fleet.ships.values()))
    destination = _first_reachable_destination(state, ship.id)
    ship.local_destination_body_id = "mock-body"
    ship.local_transit_remaining_ticks = 1

    success, message, _ = state.submit_strategic_movement(ship.id, destination)

    assert success is False
    assert message == "Cannot start strategic movement during local transit"


def test_ui_move_callbacks_route_through_submit_strategic_movement(monkeypatch):
    _install_kivy_stubs_if_missing()
    from gate_horizons.ui.screens.fleet_screen import FleetScreen
    from gate_horizons.ui.screens.galaxy_map import GalaxyMapScreen
    from gate_horizons.ui.screens.gravity_well_map import GravityWellScreen

    call_records = []

    for screen_kind in ("fleet", "galaxy", "gravity"):
        state = GameState.new_game()
        ship = next(iter(state.fleet.ships.values()))
        destination = _first_reachable_destination(state, ship.id)

        def _submit_stub(ship_id, destination_id):
            call_records.append((screen_kind, ship_id, destination_id))
            return True, "submitted", {"ship_id": ship_id, "system_id": destination_id}

        monkeypatch.setattr(state, "submit_strategic_movement", _submit_stub)

        if screen_kind == "fleet":
            screen = FleetScreen.__new__(FleetScreen)
            notices = []
            screen.game_state = state
            screen.top_bar = SimpleNamespace(update=lambda game_state: None)
            screen._update_list = lambda: None
            screen._show_notice = lambda message, title="Notice": notices.append(message)
            screen._move_ship(ship.id, destination)
            assert notices == ["submitted"]
        elif screen_kind == "galaxy":
            screen = GalaxyMapScreen.__new__(GalaxyMapScreen)
            notices = []
            screen.game_state = state
            screen.refresh = lambda: None
            screen._show_notice = lambda message, title="Notice": notices.append(message)
            screen._move_ship_to(ship.id, destination)
            assert notices == ["submitted"]
        else:
            screen = GravityWellScreen.__new__(GravityWellScreen)
            notices = []
            screen.game_state = state
            screen.set_game_state = lambda game_state: None
            screen._show_notice = lambda message, title="Notice": notices.append(message)
            screen._move_ship_to(ship.id, destination)
            assert notices == ["submitted"]

    assert [record[0] for record in call_records] == ["fleet", "galaxy", "gravity"]


def test_ui_move_callbacks_surface_consistent_local_transit_failure_notice():
    _install_kivy_stubs_if_missing()
    from gate_horizons.ui.screens.fleet_screen import FleetScreen
    from gate_horizons.ui.screens.galaxy_map import GalaxyMapScreen
    from gate_horizons.ui.screens.gravity_well_map import GravityWellScreen

    notices = []
    for screen_kind in ("fleet", "galaxy", "gravity"):
        state = GameState.new_game()
        ship = next(iter(state.fleet.ships.values()))
        destination = _first_reachable_destination(state, ship.id)
        ship.local_destination_body_id = "mock-body"
        ship.local_transit_remaining_ticks = 1

        if screen_kind == "fleet":
            screen = FleetScreen.__new__(FleetScreen)
            screen.game_state = state
            screen.top_bar = SimpleNamespace(update=lambda game_state: None)
            screen._update_list = lambda: None
            screen._show_notice = lambda message, title="Notice": notices.append((screen_kind, message))
            screen._move_ship(ship.id, destination)
        elif screen_kind == "galaxy":
            screen = GalaxyMapScreen.__new__(GalaxyMapScreen)
            screen.game_state = state
            screen.refresh = lambda: None
            screen._show_notice = lambda message, title="Notice": notices.append((screen_kind, message))
            screen._move_ship_to(ship.id, destination)
        else:
            screen = GravityWellScreen.__new__(GravityWellScreen)
            screen.game_state = state
            screen.set_game_state = lambda game_state: None
            screen._show_notice = lambda message, title="Notice": notices.append((screen_kind, message))
            screen._move_ship_to(ship.id, destination)

    assert notices == [
        ("fleet", "Cannot start strategic movement during local transit"),
        ("galaxy", "Cannot start strategic movement during local transit"),
        ("gravity", "Cannot start strategic movement during local transit"),
    ]


def test_dispatch_cargo_and_colonist_actions_return_failure_for_no_colony_or_noop():
    state = GameState.new_game()
    ship = next(iter(state.fleet.ships.values()))

    ship.location = _first_non_colony_system_id(state)
    for action_name in ("Unload Cargo", "Load Cargo", "Load Colonists", "Unload Colonists"):
        result = state.dispatch_ship_context_action(ship.id, action_name)
        assert result == {
            "success": False,
            "message": "No colony present",
            "requires_ui": None,
            "changed": False,
        }

    ship.location = next(iter(state.colonies.colonies.keys()))
    ship.cargo.clear()
    colony = state.colonies.colonies[ship.location]
    colony.stockpiles = {resource: 0 for resource in colony.stockpiles}

    assert state.dispatch_ship_context_action(ship.id, "Unload Cargo") == {
        "success": False,
        "message": "No cargo to unload",
        "requires_ui": None,
        "changed": False,
    }
    assert state.dispatch_ship_context_action(ship.id, "Load Cargo") == {
        "success": False,
        "message": "No cargo to load",
        "requires_ui": None,
        "changed": False,
    }
    assert state.dispatch_ship_context_action(ship.id, "Unload Colonists") == {
        "success": False,
        "message": "No colonists to unload",
        "requires_ui": None,
        "changed": False,
    }


def test_dispatch_cargo_and_colonist_actions_report_transfers_when_changed():
    state = GameState.new_game()
    ship = next(iter(state.fleet.ships.values()))
    ship.location = next(iter(state.colonies.colonies.keys()))

    colony = state.colonies.colonies[ship.location]
    colony.stockpiles = {resource: 0 for resource in colony.stockpiles}
    colony.stockpiles["metals"] = 5
    ship.cargo.clear()

    load_result = state.dispatch_ship_context_action(ship.id, "Load Cargo")
    assert load_result["success"] is True
    assert load_result["changed"] is True
    assert load_result["message"] == "Transferred: metals: 5"

    unload_result = state.dispatch_ship_context_action(ship.id, "Unload Cargo")
    assert unload_result["success"] is True
    assert unload_result["changed"] is True
    assert unload_result["message"] == "Transferred: metals: 5"

    ship.cargo["pop"] = 7
    unload_colonists_result = state.dispatch_ship_context_action(ship.id, "Unload Colonists")
    assert unload_colonists_result["success"] is True
    assert unload_colonists_result["changed"] is True
    assert unload_colonists_result["message"] == "Transferred: pop: 7"

    load_colonists_result = state.dispatch_ship_context_action(ship.id, "Load Colonists")
    assert load_colonists_result["success"] is True
    assert load_colonists_result["changed"] is True
    assert load_colonists_result["message"].startswith("Transferred: pop: ")


def test_dispatch_transfer_actions_report_noop_messages_for_capacity_or_storage_limits():
    state = GameState.new_game()
    ship = next(iter(state.fleet.ships.values()))
    ship.location = next(iter(state.colonies.colonies.keys()))
    colony = state.colonies.colonies[ship.location]

    ship.cargo.clear()
    ship.add_cargo("metals", ship.stats.cargo_capacity)
    colony.stockpiles["metals"] = 50
    result = state.dispatch_ship_context_action(ship.id, "Load Cargo")
    assert result == {
        "success": False,
        "message": "No cargo could be loaded (ship is full)",
        "requires_ui": None,
        "changed": False,
    }

    ship.cargo.clear()
    ship.cargo["pop"] = ship.stats.cargo_capacity
    result = state.dispatch_ship_context_action(ship.id, "Load Colonists")
    assert result == {
        "success": False,
        "message": "No colonists could be loaded (ship is full)",
        "requires_ui": None,
        "changed": False,
    }

    ship.cargo.clear()
    ship.cargo["metals"] = 10
    caps = colony.get_storage_caps()
    colony.stockpiles["metals"] = caps.get("metals", 0)
    result = state.dispatch_ship_context_action(ship.id, "Unload Cargo")
    assert result == {
        "success": False,
        "message": "No cargo could be unloaded",
        "requires_ui": None,
        "changed": False,
    }


def _snapshot_transfer_state(state, ship_id):
    ship = state.fleet.ships[ship_id]
    colony = state.colonies.colonies[ship.location]
    return {
        "ship_cargo": dict(sorted(ship.cargo.items())),
        "ship_cargo_used": ship.cargo_used,
        "colony_stockpiles": dict(sorted(colony.stockpiles.items())),
        "population": colony.population,
    }


def test_parameterized_transfer_actions_have_entrypoint_parity_for_state_and_messages():
    entrypoints = ("galaxy", "fleet", "gravity", "system")

    for action, params in (
        ("Load Cargo", {"manifest": {"metals": 3}}),
        ("Unload Cargo", {"manifest": {"metals": 2}}),
        ("Load Colonists", {"amount": 2}),
        ("Unload Colonists", {"amount": 2}),
    ):
        snapshots = []
        messages = []

        for entrypoint in entrypoints:
            state = GameState.new_game()
            ship = next(iter(state.fleet.ships.values()))
            ship.location = next(iter(state.colonies.colonies.keys()))
            colony = state.colonies.colonies[ship.location]
            colony.stockpiles["metals"] = 10
            ship.cargo.clear()
            ship.cargo["metals"] = 4
            ship.cargo["pop"] = 4

            result = state.dispatch_ship_context_action(ship.id, action, params=params)
            expected_message = result["message"]

            state = GameState.new_game()
            ship = next(iter(state.fleet.ships.values()))
            ship.location = next(iter(state.colonies.colonies.keys()))
            colony = state.colonies.colonies[ship.location]
            colony.stockpiles["metals"] = 10
            ship.cargo.clear()
            ship.cargo["metals"] = 4
            ship.cargo["pop"] = 4

            captured = {}
            original_dispatch = state.dispatch_ship_context_action

            def _spy_dispatch(ship_id, action_name, params=None):
                outcome = original_dispatch(ship_id, action_name, params=params)
                captured["result"] = outcome
                return outcome

            state.dispatch_ship_context_action = _spy_dispatch
            _run_ship_action_entrypoint_with_params(entrypoint, state, ship.id, Action(name=action), params)

            snapshots.append(_snapshot_transfer_state(state, ship.id))
            messages.append(captured["result"]["message"])
            assert captured["result"]["message"] == expected_message

        assert snapshots[0] == snapshots[1] == snapshots[2] == snapshots[3]
        assert messages[0] == messages[1] == messages[2] == messages[3]


def test_parameterized_transfer_actions_reject_invalid_manifest_or_amount_consistently():
    state = GameState.new_game()
    ship = next(iter(state.fleet.ships.values()))
    ship.location = next(iter(state.colonies.colonies.keys()))

    assert state.dispatch_ship_context_action(ship.id, "Load Cargo", params={"manifest": "invalid"}) == {
        "success": False,
        "message": "Transfer manifest must be a mapping",
        "requires_ui": None,
        "changed": False,
    }
    assert state.dispatch_ship_context_action(ship.id, "Unload Cargo", params={"manifest": {"metals": -1}}) == {
        "success": False,
        "message": "Invalid transfer amount for metals: -1",
        "requires_ui": None,
        "changed": False,
    }
    assert state.dispatch_ship_context_action(ship.id, "Load Colonists", params={"amount": -2}) == {
        "success": False,
        "message": "Invalid transfer amount: -2",
        "requires_ui": None,
        "changed": False,
    }
