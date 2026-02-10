"""Relations overview screen for diplomacy status."""

from kivy.uix.screenmanager import Screen
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.button import Button
from kivy.uix.label import Label
from kivy.uix.scrollview import ScrollView
from kivy.uix.widget import Widget
from kivy.graphics import Color, Rectangle
from kivy.metrics import dp

from ..widgets.resource_bar import TopBar


class RelationsScreen(Screen):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.name = "relations_screen"
        self.game_state = None
        self._build_ui()

    def _build_ui(self):
        root = BoxLayout(orientation="vertical")

        with root.canvas.before:
            Color(0.02, 0.03, 0.08, 1)
            self._bg = Rectangle(pos=root.pos, size=root.size)
        root.bind(
            size=lambda w, v: setattr(self._bg, "size", v),
            pos=lambda w, v: setattr(self._bg, "pos", v),
        )

        self.top_bar = TopBar()
        root.add_widget(self.top_bar)

        header = BoxLayout(
            orientation="horizontal",
            size_hint_y=None,
            height=dp(44),
            padding=[dp(8), dp(4)],
        )
        header.add_widget(Label(
            text="Relations",
            font_size="16sp",
            bold=True,
            color=(0.3, 0.85, 1, 1),
            size_hint_x=0.7,
            halign="left",
            text_size=(None, None),
        ))
        back_btn = Button(
            text="< Back to Map",
            size_hint_x=0.3,
            font_size="12sp",
            background_color=(0.08, 0.15, 0.25, 0.8),
            color=(0.7, 0.85, 1, 1),
        )
        back_btn.bind(on_release=self._go_back)
        header.add_widget(back_btn)
        root.add_widget(header)

        self.status_label = Label(
            text="",
            font_size="11sp",
            color=(0.75, 0.85, 0.95, 0.9),
            size_hint_y=None,
            height=dp(26),
            halign="left",
            valign="middle",
            text_size=(None, None),
        )
        self.status_label.bind(
            size=lambda w, v: setattr(self.status_label, "text_size", (v[0] - dp(16), None)),
        )
        root.add_widget(self.status_label)

        scroll = ScrollView(size_hint=(1, 1))
        self.list_container = BoxLayout(
            orientation="vertical",
            spacing=dp(6),
            size_hint_y=None,
            padding=[dp(8), dp(8)],
        )
        self.list_container.bind(minimum_height=self.list_container.setter("height"))
        scroll.add_widget(self.list_container)
        root.add_widget(scroll)

        self.add_widget(root)

    def set_game_state(self, game_state):
        self.game_state = game_state
        self.refresh()

    def on_pre_enter(self, *args):
        self.refresh()

    def refresh(self):
        if not self.game_state:
            return
        self.top_bar.update(self.game_state)
        self.status_label.text = ""
        self.list_container.clear_widgets()
        diplomacy = getattr(self.game_state, "diplomacy", None)
        if not diplomacy:
            self.list_container.add_widget(self._placeholder("Diplomacy system unavailable."))
            return
        diplomacy_unlocked = False
        if hasattr(self.game_state, "_is_diplomacy_unlocked"):
            diplomacy_unlocked = self.game_state._is_diplomacy_unlocked()
        elif hasattr(self.game_state, "tech"):
            diplomacy_unlocked = bool(self.game_state.tech.get_effects().get("unlock_diplomacy", False))
        if not diplomacy_unlocked:
            lock_message = "Diplomacy locked. Research Signal Decryption to unlock."
            self.status_label.text = lock_message
            self.status_label.color = (0.85, 0.7, 0.45, 1)
            self.list_container.add_widget(self._placeholder(lock_message))
            return

        for faction_id, score in diplomacy.relations.items():
            name = diplomacy.faction_names.get(faction_id, faction_id)
            tier = diplomacy.get_tier(faction_id)
            actions = diplomacy.available_actions(faction_id)
            self.list_container.add_widget(self._relation_card(faction_id, name, tier, score, actions))

    def _relation_card(self, faction_id: str, name: str, tier: str, score: int, actions: list[str]):
        card = BoxLayout(
            orientation="vertical",
            size_hint_y=None,
            height=dp(108),
            padding=[dp(8), dp(6)],
            spacing=dp(2),
        )
        with card.canvas.before:
            Color(0.06, 0.1, 0.18, 0.9)
            bg = Rectangle(pos=card.pos, size=card.size)
        card.bind(
            size=lambda w, v, r=bg: setattr(r, "size", v),
            pos=lambda w, v, r=bg: setattr(r, "pos", v),
        )
        card.add_widget(Label(
            text=name,
            font_size="12sp",
            bold=True,
            color=(0.85, 0.95, 1, 1),
            size_hint_y=None,
            height=dp(22),
            halign="left",
            text_size=(None, None),
        ))
        card.add_widget(Label(
            text=f"{tier.title()} ({score})",
            font_size="11sp",
            color=(0.6, 0.8, 1, 0.85),
            size_hint_y=None,
            height=dp(20),
            halign="left",
            text_size=(None, None),
        ))
        action_row = BoxLayout(
            orientation="horizontal",
            size_hint_y=None,
            height=dp(32),
            spacing=dp(6),
        )
        for action in actions:
            action_btn = Button(
                text=action.title(),
                font_size="10sp",
                background_color=self._action_color(action),
                color=(0.9, 0.95, 1, 1),
            )
            action_btn.faction_id = faction_id
            action_btn.action_name = action
            action_btn.bind(on_release=self._start_diplomacy_action)
            action_row.add_widget(action_btn)
        action_row.add_widget(Widget())
        card.add_widget(action_row)
        return card

    @staticmethod
    def _action_color(action: str) -> tuple[float, float, float, float]:
        action = (action or "").lower()
        if action == "aid":
            return (0.2, 0.45, 0.25, 0.9)
        if action == "threaten":
            return (0.45, 0.2, 0.2, 0.9)
        return (0.2, 0.3, 0.45, 0.9)

    @staticmethod
    def _placeholder(text):
        return Label(
            text=text,
            font_size="12sp",
            color=(0.5, 0.6, 0.7, 0.7),
            size_hint_y=None,
            height=dp(28),
        )

    def _start_diplomacy_action(self, btn):
        if not self.game_state:
            return
        success, message = self.game_state.resolve_relation_action(
            getattr(btn, "faction_id", ""),
            getattr(btn, "action_name", ""),
        )
        if success:
            self.status_label.color = (0.4, 0.95, 0.7, 1)
        else:
            self.status_label.color = (0.95, 0.45, 0.45, 1)
        self.status_label.text = message
        self.refresh()

    def _go_back(self, *args):
        from kivy.app import App
        app = App.get_running_app()
        if app:
            app.switch_screen("galaxy_map")
