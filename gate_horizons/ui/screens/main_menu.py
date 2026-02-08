"""Main menu screen for Gate Horizons."""

from kivy.uix.screenmanager import Screen
from kivy.uix.floatlayout import FloatLayout
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.button import Button
from kivy.uix.label import Label
from kivy.graphics import Color, Ellipse, Rectangle, Line
from kivy.clock import Clock
from kivy.metrics import dp
import random


class MainMenuScreen(Screen):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.name = "main_menu"
        self._stars = []
        self._nebulae = []
        self._glow_clusters = []
        self._build_ui()

    def _build_ui(self):
        layout = FloatLayout()

        # Background will be drawn on canvas
        layout.bind(size=self._draw_background, pos=self._draw_background)

        # Title area
        title_layout = BoxLayout(
            orientation="vertical",
            size_hint=(0.6, 0.4),
            pos_hint={"center_x": 0.5, "top": 0.9},
            spacing=dp(4),
        )

        title = Label(
            text="GATE HORIZONS",
            font_size="38sp",
            bold=True,
            color=(0.2, 0.8, 1, 1),
            size_hint_y=0.5,
        )
        subtitle = Label(
            text="A Space Exploration & Empire Management Sim",
            font_size="14sp",
            color=(0.6, 0.78, 0.95, 0.85),
            size_hint_y=0.3,
        )
        tagline = Label(
            text="Command the frontier. Forge a legacy among the stars.",
            font_size="12sp",
            color=(0.45, 0.7, 0.95, 0.75),
            size_hint_y=0.2,
        )
        title_layout.add_widget(title)
        title_layout.add_widget(subtitle)
        title_layout.add_widget(tagline)
        layout.add_widget(title_layout)

        # Menu buttons
        btn_layout = BoxLayout(
            orientation="vertical",
            size_hint=(0.3, 0.35),
            pos_hint={"center_x": 0.5, "center_y": 0.35},
            spacing=dp(10),
        )

        buttons = [
            ("New Game", self._on_new_game),
            ("Continue", self._on_continue),
            ("Load Game", self._on_load_game),
            ("Settings", self._on_settings),
        ]

        for text, callback in buttons:
            btn = Button(
                text=text,
                font_size="16sp",
                size_hint_y=None,
                height=dp(48),
                background_color=(0.08, 0.16, 0.3, 0.95),
                color=(0.78, 0.9, 1, 1),
                background_normal="",
                background_down="",
            )
            btn.bind(on_release=callback)
            btn_layout.add_widget(btn)

        layout.add_widget(btn_layout)

        # Version label
        version = Label(
            text="v0.1 — Phase 1 Demo",
            font_size="10sp",
            color=(0.3, 0.4, 0.5, 0.6),
            size_hint=(None, None),
            size=(dp(200), dp(20)),
            pos_hint={"right": 0.98, "y": 0.01},
        )
        layout.add_widget(version)

        self.add_widget(layout)
        self.layout = layout

        # Generate stars once
        self._stars = [
            (random.random(), random.random(), random.uniform(0.5, 2.5), random.uniform(0.3, 1.0))
            for _ in range(100)
        ]
        self._nebulae = [
            (
                random.uniform(0.05, 0.9),
                random.uniform(0.4, 0.95),
                random.uniform(0.18, 0.45),
                random.uniform(0.12, 0.35),
                random.uniform(0.08, 0.2),
                random.uniform(0.25, 0.45),
                random.uniform(0.5, 0.85),
                random.uniform(0.18, 0.3),
            )
            for _ in range(6)
        ]
        self._glow_clusters = [
            (random.uniform(0.1, 0.9), random.uniform(0.1, 0.8), random.uniform(0.02, 0.05))
            for _ in range(12)
        ]

    def _draw_background(self, *args):
        self.layout.canvas.before.clear()
        with self.layout.canvas.before:
            # Dark space background
            Color(0.02, 0.03, 0.08, 1)
            Rectangle(pos=self.layout.pos, size=self.layout.size)

            # Subtle atmospheric glow gradients
            Color(0.04, 0.08, 0.18, 0.7)
            Rectangle(
                pos=(self.layout.x, self.layout.y + self.layout.height * 0.55),
                size=(self.layout.width, self.layout.height * 0.45),
            )
            Color(0.01, 0.05, 0.12, 0.65)
            Rectangle(
                pos=(self.layout.x, self.layout.y),
                size=(self.layout.width, self.layout.height * 0.35),
            )

            # Nebula clouds
            for nx, ny, w, h, r, g, b, alpha in self._nebulae:
                Color(r, g, b, alpha)
                Ellipse(
                    pos=(
                        self.layout.x + nx * self.layout.width,
                        self.layout.y + ny * self.layout.height,
                    ),
                    size=(w * self.layout.width, h * self.layout.height),
                )

            # Distant planet limb
            planet_size = self.layout.width * 0.9
            Color(0.05, 0.12, 0.22, 0.9)
            Ellipse(
                pos=(
                    self.layout.center_x - planet_size * 0.55,
                    self.layout.y - planet_size * 0.55,
                ),
                size=(planet_size, planet_size),
            )
            Color(0.18, 0.45, 0.75, 0.6)
            Line(
                circle=(
                    self.layout.center_x - planet_size * 0.05,
                    self.layout.y + planet_size * 0.05,
                    planet_size * 0.48,
                ),
                width=1.2,
            )

            # Ring station silhouette
            ring_center = (
                self.layout.x + self.layout.width * 0.15,
                self.layout.y + self.layout.height * 0.7,
            )
            ring_radius = self.layout.width * 0.18
            Color(0.12, 0.18, 0.28, 0.9)
            Line(circle=(ring_center[0], ring_center[1], ring_radius), width=3)
            Color(0.22, 0.5, 0.85, 0.35)
            Line(circle=(ring_center[0], ring_center[1], ring_radius * 0.92), width=1)

            # Dock lights and ship glows
            for gx, gy, scale in self._glow_clusters:
                Color(0.22, 0.75, 1, 0.35)
                Ellipse(
                    pos=(
                        self.layout.x + gx * self.layout.width,
                        self.layout.y + gy * self.layout.height,
                    ),
                    size=(scale * self.layout.width, scale * self.layout.width),
                )

            # Stars
            for sx, sy, size, alpha in self._stars:
                Color(0.8, 0.85, 1, alpha * 0.6)
                x = self.layout.x + sx * self.layout.width
                y = self.layout.y + sy * self.layout.height
                Ellipse(pos=(x, y), size=(size, size))

    def _on_new_game(self, *args):
        app = self._get_app()
        if app:
            app.start_new_game()

    def _on_continue(self, *args):
        app = self._get_app()
        if app:
            app.continue_game()

    def _on_load_game(self, *args):
        app = self._get_app()
        if app:
            app.show_load_screen()

    def _on_settings(self, *args):
        app = self._get_app()
        if not app:
            return
        from gate_horizons.ui.widgets.settings import SettingsPopup
        settings = getattr(app, "settings", None)
        if not settings:
            return
        popup = SettingsPopup(
            settings=settings,
            on_save=getattr(app, "apply_settings", None),
        )
        popup.open()

    def _get_app(self):
        from kivy.app import App
        return App.get_running_app()
