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

        self.status_label = Label(
            text="",
            font_size="11sp",
            color=(0.6, 0.9, 0.7, 1),
            size_hint_y=None,
            height=dp(26),
            halign="left",
            valign="middle",
            text_size=(None, None),
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
            height=dp(150),
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
        diplomacy_unlocked = False
        if hasattr(self.game_state, "tech"):
            tech_effects = self.game_state.tech.get_effects()
            diplomacy_unlocked = bool(tech_effects.get("unlock_diplomacy", False))
        branches = entry.get("branch_options", ["tactical"])
        if not diplomacy_unlocked and "diplomacy" in branches:
            branches = [branch for branch in branches if branch != "diplomacy"]
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

        utility_row = BoxLayout(
            orientation="horizontal",
            size_hint_y=None,
            height=dp(30),
            spacing=dp(8),
        )
        export_btn = Button(
            text="Export Spec",
            font_size="11sp",
            background_color=(0.25, 0.25, 0.45, 0.9),
            color=(0.85, 0.95, 1, 1),
        )
        export_btn.encounter_id = encounter_id
        export_btn.system_id = system_id
        export_btn.encounter_type = defender.get("type", "pirates")
        export_btn.bind(on_release=self._export_encounter_spec)
        utility_row.add_widget(export_btn)

        import_btn = Button(
            text="Import Result",
            font_size="11sp",
            background_color=(0.3, 0.2, 0.4, 0.9),
            color=(0.9, 0.85, 1, 1),
        )
        import_btn.encounter_id = encounter_id
        import_btn.bind(on_release=self._import_result_spec)
        utility_row.add_widget(import_btn)
        utility_row.add_widget(Widget())
        card.add_widget(utility_row)
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
        success, message = self.game_state.resolve_diplomacy_action(
            btn.encounter_id, btn.action_name
        )
        self._set_status(message, success=success)
        self.refresh()

    def _start_evasion(self, btn):
        if not self.game_state:
            return
        success, message = self.game_state.resolve_evasion(btn.encounter_id)
        self._set_status(message, success=success)
        self.refresh()

    def _export_encounter_spec(self, btn):
        if not self.game_state:
            self._set_status("No game state available to export encounter spec.", success=False)
            return
        success, message = self.game_state.export_pending_encounter(btn.encounter_id)
        if success:
            self._set_status(f"Encounter spec exported to {message}.", success=True)
            self.refresh()
        else:
            self._set_status(f"Export failed: {message}", success=False)

    def _import_result_spec(self, *_args):
        if not self.game_state:
            self._set_status("No game state available to import result spec.", success=False)
            return
        encounter_id = getattr(_args[0], "encounter_id", "") if _args else ""
        filenames = ["ResultSpec.json"]
        if encounter_id:
            filenames.insert(0, f"ResultSpec_{encounter_id}.json")
        last_message = ""
        for filename in filenames:
            success, message = self.game_state.import_result_spec(filename=filename)
            last_message = message
            if success:
                self._set_status(f"Result spec imported: {message}", success=True)
                self.refresh()
                return
        self._set_status(f"Import failed: {last_message}", success=False)

    def _go_back(self, *args):
        from kivy.app import App
        app = App.get_running_app()
        if app:
            app.switch_screen("galaxy_map")

    def _set_status(self, message: str, success: bool = True) -> None:
        if not hasattr(self, "status_label"):
            return
        self.status_label.text = message or ""
        if success:
            self.status_label.color = (0.6, 0.9, 0.7, 1)
        else:
            self.status_label.color = (0.95, 0.6, 0.6, 1)
