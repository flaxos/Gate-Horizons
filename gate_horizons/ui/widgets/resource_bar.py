"""Top resource bar widget for Gate Horizons."""

from kivy.uix.boxlayout import BoxLayout
from kivy.uix.button import Button
from kivy.uix.label import Label
from kivy.uix.scrollview import ScrollView
from kivy.metrics import dp
from kivy.properties import NumericProperty, StringProperty


class ResourceLabel(Label):
    pass


class TopBar(BoxLayout):
    """Persistent top bar showing turn counter and resources."""

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.orientation = "horizontal"
        self.size_hint_y = None
        self.height = dp(36)
        self.padding = [8, 4]
        self.spacing = 4

        self.turn_label = Label(
            text="Turn 0",
            size_hint_x=None,
            width=dp(200),
            font_size="14sp",
            color=(0.3, 0.85, 1, 1),
            bold=True,
        )
        self.add_widget(self.turn_label)

        self.resources_expanded = True
        self.resource_toggle = Button(
            text="Resources ▾",
            size_hint_x=None,
            width=dp(120),
            font_size="12sp",
            background_color=(0.08, 0.15, 0.25, 0.8),
            color=(0.7, 0.85, 1, 1),
        )
        self.resource_toggle.bind(on_release=self._toggle_resources)
        self.add_widget(self.resource_toggle)

        self.resource_scroll = ScrollView(
            size_hint=(1, 1),
            do_scroll_x=True,
            do_scroll_y=False,
            bar_width=dp(2),
        )
        self.resource_container = BoxLayout(
            orientation="horizontal",
            size_hint_x=None,
            height=dp(32),
            spacing=dp(6),
            padding=[dp(4), 0],
        )
        self.resource_container.bind(
            minimum_width=self.resource_container.setter("width"),
        )
        self.resource_scroll.add_widget(self.resource_container)
        self.add_widget(self.resource_scroll)

        self.resource_labels = {}
        resource_icons = {
            "energy": "E",
            "metals": "M",
            "exotics": "X",
            "credits": "C",
            "intel": "I",
        }
        resource_colors = {
            "energy": (1, 0.9, 0.2, 1),
            "metals": (0.7, 0.7, 0.8, 1),
            "exotics": (0.8, 0.3, 1, 1),
            "credits": (0.2, 1, 0.4, 1),
            "intel": (0.3, 0.7, 1, 1),
        }

        for res_type, icon in resource_icons.items():
            lbl = ResourceLabel(
                text=f"[{icon}] 0",
                size_hint=(None, None),
                width=dp(92),
                height=dp(32),
                font_size="12sp",
                color=resource_colors.get(res_type, (0.8, 0.9, 1, 1)),
            )
            self.resource_labels[res_type] = lbl
            self.resource_container.add_widget(lbl)

        self.notification_label = Label(
            text="",
            size_hint_x=None,
            width=60,
            font_size="12sp",
            color=(1, 0.4, 0.3, 1),
        )
        self.add_widget(self.notification_label)

    def _toggle_resources(self, *args):
        self._set_resource_visibility(not self.resources_expanded)

    def _set_resource_visibility(self, visible: bool) -> None:
        self.resources_expanded = visible
        self.resource_scroll.opacity = 1 if visible else 0
        self.resource_scroll.disabled = not visible
        if visible:
            self.resource_scroll.size_hint_x = 1
            self.resource_toggle.text = "Resources ▾"
        else:
            self.resource_scroll.size_hint_x = None
            self.resource_scroll.width = 0
            self.resource_toggle.text = "Resources ▸"
        if self.resource_scroll.parent:
            self.resource_scroll.parent.do_layout()

    def update(self, game_state):
        """Update all labels from game state."""
        self.turn_label.text = f"Turn {game_state.turn_number} - {game_state.game_time}"

        net = game_state.resources.get_net_summary()
        resource_icons = {
            "energy": "E",
            "metals": "M",
            "exotics": "X",
            "credits": "C",
            "intel": "I",
        }

        for res_type, icon in resource_icons.items():
            amount = game_state.resources.global_resources.get(res_type, 0)
            delta = net.get(res_type, 0)
            sign = "+" if delta >= 0 else ""
            lbl = self.resource_labels.get(res_type)
            if lbl:
                lbl.text = f"[{icon}] {amount} ({sign}{delta})"

        # Notification badge
        pending = len(game_state.events.event_queue) if hasattr(game_state, 'events') else 0
        self.notification_label.text = f"[!{pending}]" if pending > 0 else ""
