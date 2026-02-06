"""Tech tree screen for Gate Horizons."""

from kivy.uix.screenmanager import Screen
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.button import Button
from kivy.uix.label import Label
from kivy.uix.widget import Widget
from kivy.uix.scrollview import ScrollView
from kivy.uix.progressbar import ProgressBar
from kivy.uix.popup import Popup
from kivy.graphics import Color, Rectangle, Line
from kivy.metrics import dp


class TechScreen(Screen):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.name = "tech_screen"
        self.game_state = None
        self._build_ui()

    def _build_ui(self):
        root = BoxLayout(orientation="vertical")

        with root.canvas.before:
            Color(0.02, 0.03, 0.08, 1)
            self._bg = Rectangle(pos=root.pos, size=root.size)
        root.bind(
            size=lambda w, v: setattr(self._bg, 'size', v),
            pos=lambda w, v: setattr(self._bg, 'pos', v),
        )

        # Header
        header = BoxLayout(
            orientation="horizontal",
            size_hint_y=None,
            height=dp(44),
            padding=[dp(8), dp(4)],
        )

        header.add_widget(Label(
            text="Technology Research",
            font_size="16sp",
            bold=True,
            color=(0.3, 0.85, 1, 1),
            size_hint_x=0.5,
            halign="left",
            text_size=(None, None),
        ))

        self.research_status = Label(
            text="No active research",
            font_size="12sp",
            color=(0.5, 0.7, 0.9, 0.8),
            size_hint_x=0.3,
        )
        header.add_widget(self.research_status)

        back_btn = Button(
            text="< Back to Map",
            size_hint_x=0.2,
            font_size="12sp",
            background_color=(0.08, 0.15, 0.25, 0.8),
            color=(0.7, 0.85, 1, 1),
        )
        back_btn.bind(on_release=self._go_back)
        header.add_widget(back_btn)

        root.add_widget(header)

        # Tech tree columns
        scroll = ScrollView(size_hint=(1, 1))
        self.tree_layout = BoxLayout(
            orientation="horizontal",
            spacing=dp(12),
            padding=dp(8),
            size_hint_x=None,
        )
        self.tree_layout.bind(minimum_width=self.tree_layout.setter("width"))
        scroll.add_widget(self.tree_layout)
        root.add_widget(scroll)

        self.add_widget(root)

    def set_game_state(self, game_state):
        self.game_state = game_state
        self._update_tree()

    def _update_tree(self):
        self.tree_layout.clear_widgets()
        if not self.game_state:
            return

        # Update research status
        if self.game_state.tech.active_research:
            tech = self.game_state.tech.techs.get(self.game_state.tech.active_research)
            if tech:
                self.research_status.text = f"Researching: {tech.name} ({tech.turns_remaining} turns)"
        else:
            self.research_status.text = "No active research"

        branches = ["propulsion", "engineering", "sensors", "xenology"]
        branch_colors = {
            "propulsion": (0.3, 0.7, 1, 1),
            "engineering": (1, 0.7, 0.2, 1),
            "sensors": (0.3, 1, 0.5, 1),
            "xenology": (0.8, 0.3, 1, 1),
        }

        for branch in branches:
            branch_techs = self.game_state.tech.get_branch_techs(branch)
            if not branch_techs:
                continue

            column = BoxLayout(
                orientation="vertical",
                size_hint=(None, 1),
                width=dp(200),
                spacing=dp(8),
                padding=[dp(4), dp(8)],
            )

            # Branch header
            color = branch_colors.get(branch, (0.7, 0.7, 0.7, 1))
            column.add_widget(Label(
                text=branch.upper(),
                font_size="14sp",
                bold=True,
                color=color,
                size_hint_y=None,
                height=dp(30),
            ))

            for tech in branch_techs:
                # Determine state
                if tech.researched:
                    bg_color = (0.1, 0.3, 0.15, 0.9)
                    text_color = (0.3, 1, 0.5, 1)
                    status = "RESEARCHED"
                elif tech.researching:
                    bg_color = (0.2, 0.2, 0.1, 0.9)
                    text_color = (1, 1, 0.3, 1)
                    status = f"IN PROGRESS ({tech.turns_remaining} turns)"
                elif self.game_state.tech.can_research(tech.id):
                    bg_color = (0.12, 0.2, 0.35, 0.9)
                    text_color = (0.7, 0.85, 1, 1)
                    status = "AVAILABLE"
                else:
                    bg_color = (0.08, 0.08, 0.1, 0.6)
                    text_color = (0.4, 0.4, 0.5, 0.6)
                    status = "LOCKED"

                card = BoxLayout(
                    orientation="vertical",
                    size_hint_y=None,
                    height=dp(80),
                    padding=dp(6),
                )
                with card.canvas.before:
                    Color(*bg_color)
                    card_bg = Rectangle(pos=card.pos, size=card.size)
                card.bind(
                    size=lambda w, v, bg=card_bg: setattr(bg, 'size', v),
                    pos=lambda w, v, bg=card_bg: setattr(bg, 'pos', v),
                )

                card.add_widget(Label(
                    text=tech.name,
                    font_size="12sp",
                    bold=True,
                    color=text_color,
                    size_hint_y=None,
                    height=dp(20),
                    halign="left",
                    text_size=(dp(180), None),
                ))

                card.add_widget(Label(
                    text=tech.description[:60] + ("..." if len(tech.description) > 60 else ""),
                    font_size="10sp",
                    color=(0.5, 0.6, 0.7, 0.8),
                    size_hint_y=None,
                    height=dp(16),
                    halign="left",
                    text_size=(dp(180), None),
                ))

                # Cost / Status
                if status == "AVAILABLE":
                    cost_parts = []
                    for k, v in tech.cost.items():
                        cost_parts.append(f"{v} {k}")
                    cost_text = ", ".join(cost_parts)

                    btn = Button(
                        text=f"Research ({cost_text})",
                        size_hint_y=None,
                        height=dp(28),
                        font_size="10sp",
                        background_color=(0.15, 0.4, 0.2, 0.9),
                        color=(0.3, 1, 0.5, 1),
                    )
                    btn.tech_id = tech.id
                    btn.bind(on_release=self._on_research)
                    card.add_widget(btn)
                else:
                    card.add_widget(Label(
                        text=status,
                        font_size="10sp",
                        color=text_color,
                        size_hint_y=None,
                        height=dp(20),
                    ))

                column.add_widget(card)

            column.add_widget(Widget())  # Spacer
            self.tree_layout.add_widget(column)

    def _on_research(self, btn):
        if not self.game_state:
            return

        result = self.game_state.tech.start_research(
            btn.tech_id, self.game_state.resources
        )
        if result:
            self._update_tree()

    def _go_back(self, *args):
        from kivy.app import App
        app = App.get_running_app()
        if app:
            app.switch_screen("galaxy_map")
