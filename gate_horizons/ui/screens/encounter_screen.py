"""Encounter resolution screen for pending encounters."""

from kivy.uix.screenmanager import Screen
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.button import Button
from kivy.uix.label import Label
from kivy.uix.scrollview import ScrollView
from kivy.uix.widget import Widget
from kivy.graphics import Color, Rectangle
from kivy.metrics import dp

from ..widgets.resource_bar import TopBar


class EncounterScreen(Screen):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.name = "encounter_screen"
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
            text="Encounters",
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
        pending = list(self.game_state.pending_encounters)
        if not pending:
            self.list_container.add_widget(self._placeholder("No pending encounters."))
            return

        for entry in pending:
            self.list_container.add_widget(self._encounter_card(entry))

    def _encounter_card(self, entry: dict):
        card = BoxLayout(
            orientation="vertical",
            size_hint_y=None,
            height=dp(110),
            padding=[dp(8), dp(6)],
            spacing=dp(4),
        )
        with card.canvas.before:
            Color(0.06, 0.1, 0.18, 0.9)
            bg = Rectangle(pos=card.pos, size=card.size)
        card.bind(
            size=lambda w, v, r=bg: setattr(r, "size", v),
            pos=lambda w, v, r=bg: setattr(r, "pos", v),
        )

        encounter_id = entry.get("encounter_id", "enc-unknown")
        defender = entry.get("defender", {})
        faction_id = defender.get("faction_id") or defender.get("type", "unknown")
        diplomacy = getattr(self.game_state, "diplomacy", None)
        has_diplomacy = bool(diplomacy and faction_id in diplomacy.relations)
        tier = diplomacy.get_tier(faction_id) if has_diplomacy else "neutral"
        score = diplomacy.get_score(faction_id) if has_diplomacy else 0
        branches = entry.get("branch_options", ["tactical"])
        system_id = entry.get("system_id", "")
        title = f"{defender.get('type', 'encounter').title()} @ {system_id}"
        card.add_widget(Label(
            text=title,
            font_size="13sp",
            bold=True,
            color=(0.85, 0.95, 1, 1),
            size_hint_y=None,
            height=dp(22),
            halign="left",
            text_size=(None, None),
        ))
        card.add_widget(Label(
            text=f"ID: {encounter_id}",
            font_size="10sp",
            color=(0.6, 0.75, 0.9, 0.8),
            size_hint_y=None,
            height=dp(18),
            halign="left",
            text_size=(None, None),
        ))
        relation_text = "Relations: N/A"
        if has_diplomacy:
            relation_text = f"Relations: {tier.title()} ({score})"
        card.add_widget(Label(
            text=relation_text,
            font_size="10sp",
            color=(0.6, 0.85, 0.9, 0.8),
            size_hint_y=None,
            height=dp(18),
            halign="left",
            text_size=(None, None),
        ))

        btn_row = BoxLayout(
            orientation="horizontal",
            size_hint_y=None,
            height=dp(36),
            spacing=dp(8),
        )
        if "tactical" in branches:
            tactical_btn = Button(
                text="Start Tactical",
                font_size="12sp",
                background_color=(0.12, 0.35, 0.5, 0.85),
                color=(0.85, 0.95, 1, 1),
            )
            tactical_btn.encounter_id = encounter_id
            tactical_btn.bind(on_release=self._start_tactical)
            btn_row.add_widget(tactical_btn)

        if "diplomacy" in branches and has_diplomacy:
            for action in diplomacy.available_actions(faction_id):
                action_btn = Button(
                    text=action.title(),
                    font_size="11sp",
                    background_color=(0.2, 0.35, 0.2, 0.85),
                    color=(0.85, 0.95, 1, 1),
                )
                action_btn.encounter_id = encounter_id
                action_btn.action_name = action
                action_btn.bind(on_release=self._start_diplomacy)
                btn_row.add_widget(action_btn)

        if "evasion" in branches:
            evasion_btn = Button(
                text="Evasion",
                font_size="11sp",
                background_color=(0.35, 0.25, 0.15, 0.85),
                color=(0.95, 0.9, 0.8, 1),
            )
            evasion_btn.encounter_id = encounter_id
            evasion_btn.bind(on_release=self._start_evasion)
            btn_row.add_widget(evasion_btn)

        btn_row.add_widget(Widget())
        card.add_widget(btn_row)
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

    def _start_tactical(self, btn):
        from kivy.app import App
        app = App.get_running_app()
        if app and hasattr(app, "start_tactical_encounter"):
            app.start_tactical_encounter(btn.encounter_id)

    def _start_diplomacy(self, btn):
        if not self.game_state:
            return
        self.game_state.resolve_diplomacy_action(btn.encounter_id, btn.action_name)
        self.refresh()

    def _start_evasion(self, btn):
        if not self.game_state:
            return
        self.game_state.resolve_evasion(btn.encounter_id)
        self.refresh()

    def _go_back(self, *args):
        from kivy.app import App
        app = App.get_running_app()
        if app:
            app.switch_screen("galaxy_map")
