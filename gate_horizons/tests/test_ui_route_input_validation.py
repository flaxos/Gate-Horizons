from __future__ import annotations

import sys
import types
from types import SimpleNamespace


def _install_kivy_stubs_if_missing():
    if "kivy" in sys.modules:
        return

    module_names = [
        "kivy",
        "kivy.metrics",
        "kivy.properties",
        "kivy.graphics",
        "kivy.uix",
        "kivy.uix.screenmanager",
        "kivy.uix.boxlayout",
        "kivy.uix.gridlayout",
        "kivy.uix.button",
        "kivy.uix.label",
        "kivy.uix.widget",
        "kivy.uix.scrollview",
        "kivy.uix.popup",
        "kivy.uix.textinput",
    ]
    for name in module_names:
        sys.modules[name] = types.ModuleType(name)

    sys.modules["kivy"].__path__ = []
    sys.modules["kivy.uix"].__path__ = []
    sys.modules["kivy.metrics"].dp = lambda value: value
    sys.modules["kivy.properties"].NumericProperty = lambda default=0, **kwargs: default
    sys.modules["kivy.properties"].StringProperty = lambda default="", **kwargs: default

    class _DummyWidget:
        def __init__(self, *args, **kwargs):
            pass

        def bind(self, *args, **kwargs):
            return None

        def add_widget(self, *args, **kwargs):
            return None

        def clear_widgets(self, *args, **kwargs):
            return None

    sys.modules["kivy.graphics"].Color = _DummyWidget
    sys.modules["kivy.graphics"].Rectangle = _DummyWidget

    for module_name, attr in (
        ("kivy.uix.screenmanager", "Screen"),
        ("kivy.uix.boxlayout", "BoxLayout"),
        ("kivy.uix.gridlayout", "GridLayout"),
        ("kivy.uix.button", "Button"),
        ("kivy.uix.label", "Label"),
        ("kivy.uix.widget", "Widget"),
        ("kivy.uix.scrollview", "ScrollView"),
        ("kivy.uix.popup", "Popup"),
        ("kivy.uix.textinput", "TextInput"),
    ):
        setattr(sys.modules[module_name], attr, _DummyWidget)


def _build_trade_game_state():
    route_calls = []

    def _create_trade_route(**kwargs):
        route_calls.append(kwargs)
        return object(), "created"

    return SimpleNamespace(
        tech=SimpleNamespace(
            get_effects=lambda: {"unlock_trade_routes": True},
            techs={"logistics_1": SimpleNamespace(researched=True)},
        ),
        colonies=SimpleNamespace(colonies={"src": object(), "dst": object()}),
        galaxy=SimpleNamespace(systems={"src": object(), "dst": object()}),
        fleet=SimpleNamespace(ships={"ship-1": SimpleNamespace()}),
        create_trade_route=_create_trade_route,
        route_calls=route_calls,
    )


def test_trade_popup_blocks_invalid_manifest_inputs_and_shows_message():
    _install_kivy_stubs_if_missing()
    from gate_horizons.ui.screens.trade_screen import CreateRoutePopup

    state = _build_trade_game_state()
    popup = CreateRoutePopup.__new__(CreateRoutePopup)
    popup.game_state = state
    popup.selected_source = "src"
    popup.selected_dest = "dst"
    popup.selected_ships = ["ship-1"]
    popup.auto_policy = "manual"
    popup.manifest_inputs = {
        "energy": SimpleNamespace(text="abc"),
        "metals": SimpleNamespace(text="-4"),
        "exotics": SimpleNamespace(text="0"),
        "credits": SimpleNamespace(text="3"),
        "pop": SimpleNamespace(text="1"),
    }
    popup.status_label = SimpleNamespace(text="", color=None)
    popup.create_callback = None
    popup.dismiss = lambda: None

    popup._on_create()

    assert not state.route_calls
    assert "Invalid manifest input" in popup.status_label.text
    assert "Energy" in popup.status_label.text
    assert "Metals" in popup.status_label.text
    assert "Expected non-negative integer" in popup.status_label.text


def test_trade_popup_auto_mode_rejects_invalid_manifest_before_creation():
    _install_kivy_stubs_if_missing()
    from gate_horizons.ui.screens.trade_screen import CreateRoutePopup

    state = _build_trade_game_state()
    popup = CreateRoutePopup.__new__(CreateRoutePopup)
    popup.game_state = state
    popup.selected_source = "src"
    popup.selected_dest = "dst"
    popup.selected_ships = ["ship-1"]
    popup.auto_policy = "auto_deficit"
    popup.manifest_inputs = {
        "energy": SimpleNamespace(text=""),
        "metals": SimpleNamespace(text="1"),
        "exotics": SimpleNamespace(text="0"),
        "credits": SimpleNamespace(text="2"),
        "pop": SimpleNamespace(text="0"),
    }
    popup.status_label = SimpleNamespace(text="", color=None)
    popup.create_callback = None
    popup.dismiss = lambda: None

    popup._on_create()

    assert not state.route_calls
    assert "Energy" in popup.status_label.text
    assert "Expected non-negative integer" in popup.status_label.text


def test_logistics_numeric_inputs_report_invalid_entry_without_coercing_to_zero():
    _install_kivy_stubs_if_missing()
    from gate_horizons.ui.screens.logistics_screen import CreateFreightRoutePopup

    popup = CreateFreightRoutePopup.__new__(CreateFreightRoutePopup)
    popup.waypoints = [{"system_id": "sys-1", "wait_turns": 3, "cargo_rules": []}]
    popup.selected_waypoint_index = 0
    popup.selected_ship_id = "ship-1"
    popup.status_label = SimpleNamespace(text="", color=None)
    popup.input_error_message = None
    popup.wait_turns_input = SimpleNamespace(text="oops")
    popup._refresh_waypoint_list = lambda: None

    popup._update_wait_turns()

    assert popup.waypoints[0]["wait_turns"] == 3
    assert "Invalid wait turns" in popup.status_label.text

    rule = {"amount": 2}
    popup._update_rule_int(rule, "amount", "NaN")
    assert rule["amount"] == 2
    assert "Invalid amount" in popup.status_label.text
