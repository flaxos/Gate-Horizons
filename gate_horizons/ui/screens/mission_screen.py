"""Mission tracking screen for Gate Horizons."""

from kivy.uix.screenmanager import Screen
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.button import Button
from kivy.uix.label import Label
from kivy.uix.scrollview import ScrollView
from kivy.uix.widget import Widget
from kivy.graphics import Color, Rectangle
from kivy.metrics import dp

from gate_horizons.game.missions import mission_display_data
from ..widgets.resource_bar import TopBar


class MissionScreen(Screen):
    """Mission overview screen showing active and completed missions."""

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.name = "mission_screen"
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
            text="Missions",
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

        main = BoxLayout(orientation="horizontal", spacing=dp(8), padding=[dp(8), dp(8)])

        # Active missions
        active_panel = BoxLayout(orientation="vertical", size_hint_x=0.5, spacing=dp(6))
        active_panel.add_widget(Label(
            text="Active Missions",
            font_size="14sp",
            bold=True,
            color=(0.3, 1, 0.6, 1),
            size_hint_y=None,
            height=dp(26),
        ))
        self.active_list = BoxLayout(
            orientation="vertical",
            spacing=dp(4),
            size_hint_y=None,
        )
        self.active_list.bind(minimum_height=self.active_list.setter("height"))
        active_scroll = ScrollView(size_hint=(1, 1))
        active_scroll.add_widget(self.active_list)
        active_panel.add_widget(active_scroll)

        # Completed missions
        completed_panel = BoxLayout(orientation="vertical", size_hint_x=0.5, spacing=dp(6))
        completed_panel.add_widget(Label(
            text="Completed Missions",
            font_size="14sp",
            bold=True,
            color=(1, 0.85, 0.3, 1),
            size_hint_y=None,
            height=dp(26),
        ))
        self.completed_list = BoxLayout(
            orientation="vertical",
            spacing=dp(4),
            size_hint_y=None,
        )
        self.completed_list.bind(minimum_height=self.completed_list.setter("height"))
        completed_scroll = ScrollView(size_hint=(1, 1))
        completed_scroll.add_widget(self.completed_list)
        completed_panel.add_widget(completed_scroll)

        main.add_widget(active_panel)
        main.add_widget(completed_panel)

        root.add_widget(main)
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
        self._populate_lists()

    def _populate_lists(self):
        self.active_list.clear_widgets()
        self.completed_list.clear_widgets()

        active_missions = list(getattr(self.game_state.missions, "active_missions", []))
        completed_missions = list(getattr(self.game_state.missions, "completed_missions", []))

        if not active_missions:
            self.active_list.add_widget(self._placeholder_label("No active missions yet."))
        else:
            for mission in active_missions:
                self.active_list.add_widget(self._mission_card(mission, status="Active"))

        if not completed_missions:
            self.completed_list.add_widget(self._placeholder_label("No missions completed yet."))
        else:
            for mission in completed_missions:
                self.completed_list.add_widget(self._mission_card(mission, status="Completed"))

    def _mission_card(self, mission, status="Active"):
        data = mission_display_data(mission)
        reward = data.get("reward", {}) or {}
        reward_text = ", ".join(f"{amount} {resource}" for resource, amount in reward.items())
        progress_summary = data.get("progress_summary") or ""
        status_text = status.upper()
        if progress_summary and status.lower() == "active":
            status_text = f"{status_text} · {progress_summary}"

        card = BoxLayout(
            orientation="vertical",
            size_hint_y=None,
            height=dp(84),
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
            text=data.get("title", "Mission"),
            font_size="12sp",
            bold=True,
            color=(0.85, 0.95, 1, 1),
            size_hint_y=None,
            height=dp(20),
            halign="left",
            text_size=(None, None),
        ))
        card.add_widget(Label(
            text=data.get("description", ""),
            font_size="10sp",
            color=(0.6, 0.75, 0.9, 0.9),
            size_hint_y=None,
            height=dp(20),
            halign="left",
            text_size=(None, None),
        ))
        card.add_widget(Label(
            text=f"{status_text}",
            font_size="10sp",
            color=(0.3, 1, 0.6, 0.9) if status.lower() == "active" else (1, 0.85, 0.3, 0.9),
            size_hint_y=None,
            height=dp(18),
            halign="left",
            text_size=(None, None),
        ))
        reward_line = f"Rewards: {reward_text}" if reward_text else "Rewards: —"
        card.add_widget(Label(
            text=reward_line,
            font_size="10sp",
            color=(0.8, 0.8, 0.9, 0.8),
            size_hint_y=None,
            height=dp(18),
            halign="left",
            text_size=(None, None),
        ))
        return card

    @staticmethod
    def _placeholder_label(text):
        return Label(
            text=text,
            font_size="11sp",
            color=(0.5, 0.6, 0.7, 0.7),
            size_hint_y=None,
            height=dp(28),
        )

    def _go_back(self, *args):
        from kivy.app import App
        app = App.get_running_app()
        if app:
            app.switch_screen("galaxy_map")
