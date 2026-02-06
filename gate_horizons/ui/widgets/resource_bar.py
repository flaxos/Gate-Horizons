"""Top resource bar widget for Gate Horizons."""

from kivy.uix.boxlayout import BoxLayout
from kivy.uix.label import Label
from kivy.properties import NumericProperty, StringProperty


class ResourceLabel(Label):
    pass


class TopBar(BoxLayout):
    """Persistent top bar showing turn counter and resources."""

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.orientation = "horizontal"
        self.padding = [8, 4]
        self.spacing = 4

        self.turn_label = Label(
            text="Turn 0",
            size_hint_x=0.2,
            font_size="14sp",
            color=(0.3, 0.85, 1, 1),
            bold=True,
        )
        self.add_widget(self.turn_label)

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
            lbl = Label(
                text=f"[{icon}] 0",
                size_hint_x=None,
                width=100,
                font_size="12sp",
                color=resource_colors.get(res_type, (0.8, 0.9, 1, 1)),
            )
            self.resource_labels[res_type] = lbl
            self.add_widget(lbl)

        self.notification_label = Label(
            text="",
            size_hint_x=None,
            width=60,
            font_size="12sp",
            color=(1, 0.4, 0.3, 1),
        )
        self.add_widget(self.notification_label)

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
