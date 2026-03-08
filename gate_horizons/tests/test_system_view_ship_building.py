import sys
import types
import unittest
from types import SimpleNamespace
from unittest.mock import patch


def _install_kivy_stubs():
    if "kivy" in sys.modules:
        return

    class DummyWidget:
        def __init__(self, *args, **kwargs):
            self.children = []
            for key, value in kwargs.items():
                setattr(self, key, value)

        def add_widget(self, widget):
            self.children.append(widget)

        def clear_widgets(self):
            self.children.clear()

        def bind(self, **kwargs):
            return None

    class DummyPopup(DummyWidget):
        def open(self):
            return None

        def dismiss(self):
            return None

    class DummyScreen(DummyWidget):
        pass

    kivy = types.ModuleType("kivy")
    uix = types.ModuleType("kivy.uix")
    screenmanager = types.ModuleType("kivy.uix.screenmanager")
    floatlayout = types.ModuleType("kivy.uix.floatlayout")
    boxlayout = types.ModuleType("kivy.uix.boxlayout")
    gridlayout = types.ModuleType("kivy.uix.gridlayout")
    button = types.ModuleType("kivy.uix.button")
    label = types.ModuleType("kivy.uix.label")
    widget = types.ModuleType("kivy.uix.widget")
    scrollview = types.ModuleType("kivy.uix.scrollview")
    popup = types.ModuleType("kivy.uix.popup")
    textinput = types.ModuleType("kivy.uix.textinput")
    graphics = types.ModuleType("kivy.graphics")
    metrics = types.ModuleType("kivy.metrics")

    screenmanager.Screen = DummyScreen
    floatlayout.FloatLayout = DummyWidget
    boxlayout.BoxLayout = DummyWidget
    gridlayout.GridLayout = DummyWidget
    button.Button = DummyWidget
    label.Label = DummyWidget
    widget.Widget = DummyWidget
    scrollview.ScrollView = DummyWidget
    popup.Popup = DummyPopup
    textinput.TextInput = DummyWidget

    graphics.Color = DummyWidget
    graphics.Ellipse = DummyWidget
    graphics.Line = DummyWidget
    graphics.Rectangle = DummyWidget

    metrics.dp = lambda value: value

    sys.modules["kivy"] = kivy
    sys.modules["kivy.uix"] = uix
    sys.modules["kivy.uix.screenmanager"] = screenmanager
    sys.modules["kivy.uix.floatlayout"] = floatlayout
    sys.modules["kivy.uix.boxlayout"] = boxlayout
    sys.modules["kivy.uix.gridlayout"] = gridlayout
    sys.modules["kivy.uix.button"] = button
    sys.modules["kivy.uix.label"] = label
    sys.modules["kivy.uix.widget"] = widget
    sys.modules["kivy.uix.scrollview"] = scrollview
    sys.modules["kivy.uix.popup"] = popup
    sys.modules["kivy.uix.textinput"] = textinput
    sys.modules["kivy.graphics"] = graphics
    sys.modules["kivy.metrics"] = metrics

    resource_bar = types.ModuleType("gate_horizons.ui.widgets.resource_bar")
    resource_bar.TopBar = DummyWidget
    sys.modules["gate_horizons.ui.widgets.resource_bar"] = resource_bar


_install_kivy_stubs()

from gate_horizons.ui.screens import system_view


class _StubResources:
    def __init__(self, affordable=True):
        self.affordable = affordable

    def can_afford(self, cost):
        return self.affordable


class _StubColony:
    def __init__(self, can_build=True, queue_len=0, queue_limit=3, concurrency=1, cost=None):
        self._can_build = can_build
        self.shipyard_queue = [{}] * queue_len
        self._queue_limit = queue_limit
        self._concurrency = concurrency
        self._cost = cost or {"metals": 10}

    def can_build_ship(self, ship_class, templates):
        return self._can_build

    def get_ship_build_cost(self, ship_class, templates):
        return dict(self._cost)

    def get_ship_build_concurrency(self):
        return self._concurrency

    def get_ship_build_queue_limit(self):
        return self._queue_limit


class TestSystemViewShipBuilding(unittest.TestCase):
    def _make_screen(self, colony, affordable=True, build_success=False):
        screen = object.__new__(system_view.SystemViewScreen)
        screen.system_id = "sol"
        screen.game_state = SimpleNamespace(
            build_ship=lambda system_id, ship_class: build_success,
            resources=_StubResources(affordable=affordable),
            colonies=SimpleNamespace(colonies={"sol": colony}),
            fleet=SimpleNamespace(_ship_templates={"scout": {"name": "Scout", "build_cost": {"metals": 10}}}),
        )
        screen.top_bar = SimpleNamespace(update=lambda _: None)
        screen._update_info = lambda: None
        return screen

    def test_get_ship_build_button_state_requires_constraints_and_affordability(self):
        colony = _StubColony(can_build=False)
        screen = self._make_screen(colony=colony, affordable=True)

        can_build, can_afford, cost = screen._get_ship_build_button_state(
            colony,
            "scout",
            screen.game_state.fleet._ship_templates,
        )

        self.assertFalse(can_build)
        self.assertTrue(can_afford)
        self.assertEqual(cost, {"metals": 10})
        self.assertFalse(can_build and can_afford)

    def test_on_build_ship_shows_queue_full_notice(self):
        colony = _StubColony(queue_len=3, queue_limit=3, concurrency=1)
        screen = self._make_screen(colony=colony, affordable=True, build_success=False)
        btn = SimpleNamespace(ship_class="scout")

        with patch.object(system_view, "NoticePopup") as popup_cls:
            popup = popup_cls.return_value
            screen._on_build_ship(btn)

            popup_cls.assert_called_once_with(
                title="Ship Construction Blocked",
                message="Shipyard queue is full.",
            )
            popup.open.assert_called_once()

    def test_on_build_ship_shows_spaceport_slot_notice(self):
        colony = _StubColony(concurrency=0, queue_len=0, queue_limit=0)
        screen = self._make_screen(colony=colony, affordable=True, build_success=False)
        btn = SimpleNamespace(ship_class="scout")

        with patch.object(system_view, "NoticePopup") as popup_cls:
            popup = popup_cls.return_value
            screen._on_build_ship(btn)

            popup_cls.assert_called_once_with(
                title="Ship Construction Blocked",
                message="No spaceport slot is available for ship construction.",
            )
            popup.open.assert_called_once()

    def test_on_build_ship_shows_insufficient_resources_notice(self):
        colony = _StubColony(queue_len=0, queue_limit=3, concurrency=1)
        screen = self._make_screen(colony=colony, affordable=False, build_success=False)
        btn = SimpleNamespace(ship_class="scout")

        with patch.object(system_view, "NoticePopup") as popup_cls:
            popup = popup_cls.return_value
            screen._on_build_ship(btn)

            popup_cls.assert_called_once_with(
                title="Ship Construction Blocked",
                message="Insufficient resources to build this ship.",
            )
            popup.open.assert_called_once()


if __name__ == "__main__":
    unittest.main()


class _TrackingResources:
    def __init__(self, affordable_cost):
        self.affordable_cost = affordable_cost
        self.costs_checked = []

    def can_afford(self, cost):
        normalized = dict(cost)
        self.costs_checked.append(normalized)
        return normalized == self.affordable_cost


class TestSystemViewGateAndBuildParity(unittest.TestCase):
    def test_get_gate_activation_button_state_uses_discounted_cost_for_affordability(self):
        screen = object.__new__(system_view.SystemViewScreen)
        resources = _TrackingResources(affordable_cost={"metals": 70, "energy": 35})

        screen.game_state = SimpleNamespace(
            tech=SimpleNamespace(get_effects=lambda: {"gate_cost_reduction": 0.3}),
            galaxy=SimpleNamespace(
                get_gate_activation_cost=lambda system_id, cost_reduction=0.0: {
                    "metals": int(100 * (1.0 - cost_reduction)),
                    "energy": int(50 * (1.0 - cost_reduction)),
                }
            ),
            resources=resources,
        )

        cost, can_activate = screen._get_gate_activation_button_state("sol")

        self.assertEqual(cost, {"metals": 70, "energy": 35})
        self.assertTrue(can_activate)
        self.assertEqual(resources.costs_checked, [{"metals": 70, "energy": 35}])

    def test_on_build_ship_shows_notice_without_attempting_build_when_gated(self):
        colony = _StubColony(can_build=False, queue_len=0, queue_limit=3, concurrency=1)
        build_attempts = []

        screen = object.__new__(system_view.SystemViewScreen)
        screen.system_id = "sol"
        screen.game_state = SimpleNamespace(
            build_ship=lambda *_: build_attempts.append(True) or True,
            resources=_StubResources(affordable=True),
            colonies=SimpleNamespace(colonies={"sol": colony}),
            fleet=SimpleNamespace(_ship_templates={"scout": {"name": "Scout", "build_cost": {"metals": 10}}}),
        )
        screen.top_bar = SimpleNamespace(update=lambda _: None)
        screen._update_info = lambda: None
        btn = SimpleNamespace(ship_class="scout")

        with patch.object(system_view, "NoticePopup") as popup_cls:
            popup = popup_cls.return_value
            screen._on_build_ship(btn)

            popup_cls.assert_called_once_with(
                title="Ship Construction Blocked",
                message="Ship construction is currently unavailable.",
            )
            popup.open.assert_called_once()
            self.assertEqual(build_attempts, [])
