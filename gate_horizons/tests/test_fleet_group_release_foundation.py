from __future__ import annotations

import sys
import types
from types import SimpleNamespace

from gate_horizons.game.fleet_groups import create_group, dispatch_group_order
from gate_horizons.game.settings import GameSettings
from gate_horizons.game.telemetry import TelemetryAdapter
from gate_horizons.game.telemetry_events import RoadmapTelemetryEvent


class _DummyWidget:
    def __init__(self, *args, **kwargs):
        pass

    def bind(self, *args, **kwargs):
        return None

    def add_widget(self, *args, **kwargs):
        return None

    def clear_widgets(self, *args, **kwargs):
        return None


class _DummyApp:
    _app = None

    @classmethod
    def get_running_app(cls):
        return cls._app


def _install_kivy_stubs_if_missing():
    if "kivy" in sys.modules:
        return

    module_names = [
        "kivy",
        "kivy.app",
        "kivy.metrics",
        "kivy.graphics",
        "kivy.uix",
        "kivy.uix.screenmanager",
        "kivy.uix.boxlayout",
        "kivy.uix.button",
        "kivy.uix.gridlayout",
        "kivy.uix.label",
        "kivy.uix.widget",
        "kivy.uix.scrollview",
        "kivy.uix.progressbar",
        "kivy.uix.popup",
        "kivy.uix.floatlayout",
        "kivy.uix.textinput",
        "kivy.uix.dropdown",
        "kivy.uix.togglebutton",
        "kivy.properties",
    ]
    for name in module_names:
        sys.modules[name] = types.ModuleType(name)
    sys.modules["kivy"].__path__ = []
    sys.modules["kivy.uix"].__path__ = []

    sys.modules["kivy.app"].App = _DummyApp
    sys.modules["kivy.metrics"].dp = lambda value: value
    sys.modules["kivy.properties"].NumericProperty = lambda default=0, **kwargs: default
    sys.modules["kivy.properties"].StringProperty = lambda default="", **kwargs: default

    graphics = sys.modules["kivy.graphics"]
    graphics.Color = _DummyWidget
    graphics.Rectangle = _DummyWidget

    for module_name, attr in (
        ("kivy.uix.screenmanager", "Screen"),
        ("kivy.uix.boxlayout", "BoxLayout"),
        ("kivy.uix.button", "Button"),
        ("kivy.uix.gridlayout", "GridLayout"),
        ("kivy.uix.label", "Label"),
        ("kivy.uix.widget", "Widget"),
        ("kivy.uix.scrollview", "ScrollView"),
        ("kivy.uix.progressbar", "ProgressBar"),
        ("kivy.uix.popup", "Popup"),
        ("kivy.uix.floatlayout", "FloatLayout"),
        ("kivy.uix.textinput", "TextInput"),
        ("kivy.uix.dropdown", "DropDown"),
        ("kivy.uix.togglebutton", "ToggleButton"),
    ):
        setattr(sys.modules[module_name], attr, _DummyWidget)


def test_fleet_group_feature_defaults_off():
    settings = GameSettings()
    assert settings.enable_fleet_groups is False


def test_fleet_group_ui_actions_suppressed_when_flag_off():
    _install_kivy_stubs_if_missing()
    from gate_horizons.ui.screens.fleet_screen import FleetScreen

    _DummyApp._app = SimpleNamespace(settings=GameSettings(enable_fleet_groups=False))
    screen = FleetScreen.__new__(FleetScreen)
    assert screen.fleet_group_actions() == []

    calls = []
    telemetry = TelemetryAdapter(lambda event_name, payload: calls.append((event_name, payload)))
    result = create_group(
        game_state=SimpleNamespace(),
        group_id="fg-1",
        ship_ids=["ship-1", "ship-2"],
        system_id="sol",
        turn_index=10,
        telemetry=telemetry,
        settings=GameSettings(enable_fleet_groups=False),
    )
    assert result.accepted is False
    assert result.reason == "feature_disabled"
    assert calls == []


def test_required_telemetry_payloads_are_emitted_with_required_keys():
    emitted = []
    telemetry = TelemetryAdapter(lambda event_name, payload: emitted.append((event_name, dict(payload))))

    telemetry.emit(
        RoadmapTelemetryEvent.FLEET_GROUP_CREATED,
        {
            "group_id": "fg-1",
            "ship_count": 2,
            "system_id": "sol",
            "turn_index": 12,
        },
    )
    dispatch_group_order(
        group_id="fg-1",
        order_type="move",
        target_id="alpha-centauri",
        ship_count=2,
        turn_index=13,
        telemetry=telemetry,
        settings=GameSettings(enable_fleet_groups=True),
    )
    telemetry.emit(
        RoadmapTelemetryEvent.FLEET_GROUP_ORDER_RESULT,
        {
            "group_id": "fg-1",
            "order_type": "move",
            "result": "success",
            "reason": None,
            "turn_index": 14,
        },
    )

    assert [name for name, _ in emitted] == [
        "fleet_group_created",
        "fleet_group_order_issued",
        "fleet_group_order_result",
    ]
    for _, payload in emitted:
        assert "group_id" in payload
        assert "turn_index" in payload
