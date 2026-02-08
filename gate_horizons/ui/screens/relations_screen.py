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
        self.list_container.clear_widgets()
        diplomacy = getattr(self.game_state, "diplomacy", None)
        if not diplomacy:
            self.list_container.add_widget(self._placeholder("Diplomacy system unavailable."))
            return

        for faction_id, score in diplomacy.relations.items():
            name = diplomacy.faction_names.get(faction_id, faction_id)
            tier = diplomacy.get_tier(faction_id)
            self.list_container.add_widget(self._relation_card(name, tier, score))

    @staticmethod
    def _relation_card(name: str, tier: str, score: int):
        card = BoxLayout(
            orientation="vertical",
            size_hint_y=None,
            height=dp(70),
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
        return card

    @staticmethod
    def _placeholder(text):
        return Label(
            text=text,
            font_size="12sp",
            color=(0.5, 0.6, 0.7, 0.7),
            size_hint_y=None,
            height=dp(28),
        )

    def _go_back(self, *args):
        from kivy.app import App
        app = App.get_running_app()
        if app:
            app.switch_screen("galaxy_map")
