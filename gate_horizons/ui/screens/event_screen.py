"""Event popup screen for Gate Horizons."""

import os
import random

from kivy.uix.boxlayout import BoxLayout
from kivy.uix.button import Button
from kivy.uix.label import Label
from kivy.uix.popup import Popup
from kivy.uix.scrollview import ScrollView
from kivy.uix.widget import Widget
from kivy.graphics import Color, Ellipse, Rectangle, Line
from kivy.metrics import dp


# ---------------------------------------------------------------------------
# Backdrop rendering helpers
# ---------------------------------------------------------------------------

# Tag -> color palette mapping for procedural backdrops
TAG_PALETTES = {
    "derelict": {
        "bg": (0.04, 0.03, 0.06),
        "accent": (0.25, 0.18, 0.35),
        "highlight": (0.5, 0.35, 0.7),
    },
    "alien_tech": {
        "bg": (0.02, 0.05, 0.08),
        "accent": (0.1, 0.35, 0.5),
        "highlight": (0.2, 0.7, 0.9),
    },
    "anomaly": {
        "bg": (0.06, 0.03, 0.04),
        "accent": (0.35, 0.12, 0.2),
        "highlight": (0.8, 0.3, 0.5),
    },
    "biological": {
        "bg": (0.02, 0.06, 0.03),
        "accent": (0.08, 0.3, 0.15),
        "highlight": (0.2, 0.8, 0.4),
    },
    "gate_tech": {
        "bg": (0.03, 0.04, 0.08),
        "accent": (0.1, 0.2, 0.45),
        "highlight": (0.3, 0.5, 1.0),
    },
    "mining": {
        "bg": (0.06, 0.04, 0.02),
        "accent": (0.35, 0.22, 0.1),
        "highlight": (0.8, 0.6, 0.2),
    },
    "distress": {
        "bg": (0.06, 0.02, 0.02),
        "accent": (0.4, 0.1, 0.08),
        "highlight": (1.0, 0.3, 0.2),
    },
    "intelligence": {
        "bg": (0.03, 0.03, 0.06),
        "accent": (0.15, 0.15, 0.35),
        "highlight": (0.4, 0.4, 0.9),
    },
}

DEFAULT_PALETTE = {
    "bg": (0.03, 0.04, 0.07),
    "accent": (0.1, 0.2, 0.35),
    "highlight": (0.3, 0.6, 0.9),
}


def _palette_for_tags(tags):
    """Pick a colour palette based on event tags, first match wins."""
    if tags:
        for tag in tags:
            if tag in TAG_PALETTES:
                return TAG_PALETTES[tag]
    return DEFAULT_PALETTE


class BackdropWidget(Widget):
    """Procedural backdrop that renders a themed space scene."""

    def __init__(self, palette=None, seed=None, **kwargs):
        super().__init__(**kwargs)
        self.palette = palette or DEFAULT_PALETTE
        self._seed = seed or random.randint(0, 999999)
        self.bind(size=self._redraw, pos=self._redraw)

    def _redraw(self, *args):
        self.canvas.clear()
        rng = random.Random(self._seed)
        bg = self.palette["bg"]
        accent = self.palette["accent"]
        highlight = self.palette["highlight"]

        with self.canvas:
            # Base gradient background
            Color(*bg, 1)
            Rectangle(pos=self.pos, size=self.size)

            # Nebula-like accent blobs
            for _ in range(6):
                cx = self.x + rng.random() * self.width
                cy = self.y + rng.random() * self.height
                r = rng.uniform(0.15, 0.4) * min(self.width, self.height)
                Color(*accent, rng.uniform(0.08, 0.2))
                Ellipse(pos=(cx - r, cy - r), size=(r * 2, r * 2))

            # Stars
            for _ in range(50):
                sx = self.x + rng.random() * self.width
                sy = self.y + rng.random() * self.height
                s = rng.uniform(0.8, 2.5)
                Color(0.8, 0.85, 1, rng.uniform(0.2, 0.8))
                Ellipse(pos=(sx, sy), size=(s, s))

            # Highlight elements (arcs, glows)
            for _ in range(3):
                cx = self.x + rng.uniform(0.2, 0.8) * self.width
                cy = self.y + rng.uniform(0.2, 0.8) * self.height
                r = rng.uniform(0.08, 0.2) * min(self.width, self.height)
                Color(*highlight, rng.uniform(0.06, 0.15))
                Ellipse(pos=(cx - r, cy - r), size=(r * 2, r * 2))

            # A couple of subtle line elements
            for _ in range(2):
                x1 = self.x + rng.random() * self.width
                y1 = self.y + rng.random() * self.height
                x2 = self.x + rng.random() * self.width
                y2 = self.y + rng.random() * self.height
                Color(*highlight, rng.uniform(0.04, 0.1))
                Line(points=[x1, y1, x2, y2], width=rng.uniform(0.5, 1.5))

            # Vignette overlay (darken edges)
            edge_alpha = 0.35
            edge_w = self.width * 0.15
            # Left
            Color(0, 0, 0, edge_alpha)
            Rectangle(pos=self.pos, size=(edge_w, self.height))
            # Right
            Color(0, 0, 0, edge_alpha)
            Rectangle(
                pos=(self.x + self.width - edge_w, self.y),
                size=(edge_w, self.height),
            )


# ---------------------------------------------------------------------------
# Event popups
# ---------------------------------------------------------------------------


class EventPopup(Popup):
    """Modal popup for displaying and resolving game events.

    Uses a landscape-friendly horizontal layout:
      [Backdrop | Description + Choices]
    """

    def __init__(self, event=None, game_state=None, on_resolved=None, **kwargs):
        self.event = event
        self.game_state = game_state
        self.on_resolved = on_resolved

        # --- outer horizontal split: backdrop | content ---
        outer = BoxLayout(orientation="horizontal", spacing=dp(0))

        # Left: procedural backdrop
        palette = _palette_for_tags(getattr(event, "tags", None))
        seed = hash(event.id) if event else 0
        backdrop = BackdropWidget(
            palette=palette,
            seed=seed,
            size_hint=(0.35, 1),
        )
        outer.add_widget(backdrop)

        # Right: text + choices
        content = BoxLayout(
            orientation="vertical",
            spacing=dp(10),
            padding=[dp(16), dp(12), dp(12), dp(12)],
            size_hint=(0.65, 1),
        )

        # Event description (scrollable, gets majority of vertical space)
        desc_scroll = ScrollView(size_hint=(1, 1))
        desc_label = Label(
            text=event.description if event else "",
            font_size="14sp",
            color=(0.78, 0.88, 0.96, 1),
            size_hint_y=None,
            text_size=(None, None),  # set dynamically
            halign="left",
            valign="top",
            markup=True,
        )
        # Dynamically size text_size to the available scroll width
        def _update_text_width(instance, value):
            desc_label.text_size = (desc_scroll.width - dp(8), None)
        desc_scroll.bind(width=_update_text_width)
        desc_label.bind(texture_size=desc_label.setter("size"))
        desc_scroll.add_widget(desc_label)
        content.add_widget(desc_scroll)

        # Choice buttons
        choices_layout = BoxLayout(
            orientation="vertical",
            spacing=dp(6),
            size_hint_y=None,
        )
        choices_layout.bind(minimum_height=choices_layout.setter("height"))

        if event:
            for i, choice in enumerate(event.choices):
                btn = Button(
                    text=choice.get("text", f"Option {i+1}"),
                    size_hint_y=None,
                    height=dp(48),
                    font_size="13sp",
                    background_color=(0.12, 0.25, 0.4, 0.8),
                    color=(0.85, 0.95, 1, 1),
                    halign="left",
                    valign="middle",
                    text_size=(None, None),
                )
                # Make button text wrap properly
                def _update_btn_text(inst, val, b=btn):
                    b.text_size = (b.width - dp(16), None)
                btn.bind(width=_update_btn_text)
                btn.choice_index = i
                btn.bind(on_release=self._on_choice)
                choices_layout.add_widget(btn)

        content.add_widget(choices_layout)
        outer.add_widget(content)

        title_text = event.title if event else "Event"

        super().__init__(
            title=title_text,
            content=outer,
            size_hint=(0.82, 0.78),
            title_color=(0.3, 0.85, 1, 1),
            title_size="16sp",
            separator_color=(0.15, 0.6, 0.8, 0.6),
            background_color=(0.04, 0.06, 0.12, 0.95),
            auto_dismiss=False,
            **kwargs,
        )

    def _on_choice(self, btn):
        if not self.event or not self.game_state:
            self.dismiss()
            return

        outcome = self.game_state.events.resolve_event(
            self.event.id, btn.choice_index, self.game_state
        )

        self.dismiss()

        if outcome:
            # Show outcome popup
            outcome_popup = EventOutcomePopup(
                outcome=outcome,
                event=self.event,
                on_continue=self.on_resolved,
            )
            outcome_popup.open()
        elif self.on_resolved:
            self.on_resolved()


class EventOutcomePopup(Popup):
    """Shows the result of an event choice with a themed backdrop."""

    def __init__(self, outcome=None, event=None, on_continue=None, **kwargs):
        self.continue_callback = on_continue

        # --- outer horizontal split: backdrop | content ---
        outer = BoxLayout(orientation="horizontal", spacing=dp(0))

        # Left: procedural backdrop (same theme as event)
        palette = _palette_for_tags(getattr(event, "tags", None)) if event else DEFAULT_PALETTE
        seed = (hash(getattr(event, "id", "")) + 7) if event else 7
        backdrop = BackdropWidget(
            palette=palette,
            seed=seed,
            size_hint=(0.3, 1),
        )
        outer.add_widget(backdrop)

        # Right: outcome content
        content = BoxLayout(
            orientation="vertical",
            spacing=dp(10),
            padding=[dp(16), dp(12), dp(12), dp(12)],
            size_hint=(0.7, 1),
        )

        # Result indicator
        result_colors = {
            "success": (0.2, 1, 0.4, 1),
            "partial": (1, 0.8, 0.2, 1),
            "failure": (1, 0.3, 0.2, 1),
        }
        result_text = (outcome.result or "unknown").upper() if outcome else "UNKNOWN"
        result_color = result_colors.get(outcome.result if outcome else "", (0.7, 0.7, 0.7, 1))

        content.add_widget(Label(
            text=result_text,
            font_size="18sp",
            bold=True,
            color=result_color,
            size_hint_y=None,
            height=dp(36),
        ))

        # Outcome description
        desc_scroll = ScrollView(size_hint=(1, 1))
        desc_label = Label(
            text=outcome.description if outcome else "",
            font_size="14sp",
            color=(0.78, 0.88, 0.96, 1),
            size_hint_y=None,
            text_size=(None, None),
            halign="left",
            valign="top",
        )
        def _update_text_width(instance, value):
            desc_label.text_size = (desc_scroll.width - dp(8), None)
        desc_scroll.bind(width=_update_text_width)
        desc_label.bind(texture_size=desc_label.setter("size"))
        desc_scroll.add_widget(desc_label)
        content.add_widget(desc_scroll)

        # Rewards/Costs
        if outcome:
            if outcome.rewards_applied:
                rewards_text = "Gained: " + ", ".join(
                    f"+{v} {k}" for k, v in outcome.rewards_applied.items()
                )
                content.add_widget(Label(
                    text=rewards_text,
                    font_size="13sp",
                    color=(0.3, 1, 0.5, 0.9),
                    size_hint_y=None,
                    height=dp(26),
                ))

            if outcome.costs_applied:
                costs_text = "Lost: " + ", ".join(
                    f"-{v} {k}" for k, v in outcome.costs_applied.items()
                )
                content.add_widget(Label(
                    text=costs_text,
                    font_size="13sp",
                    color=(1, 0.4, 0.3, 0.9),
                    size_hint_y=None,
                    height=dp(26),
                ))

        # Continue button
        continue_btn = Button(
            text="Continue",
            size_hint_y=None,
            height=dp(46),
            font_size="14sp",
            bold=True,
            background_color=(0.1, 0.35, 0.5, 0.9),
            color=(1, 1, 1, 1),
        )
        continue_btn.bind(on_release=self._on_continue)
        content.add_widget(continue_btn)

        outer.add_widget(content)

        super().__init__(
            title="Outcome",
            content=outer,
            size_hint=(0.72, 0.68),
            title_color=(0.3, 0.85, 1, 1),
            title_size="16sp",
            separator_color=(0.15, 0.6, 0.8, 0.6),
            background_color=(0.04, 0.06, 0.12, 0.95),
            auto_dismiss=False,
            **kwargs,
        )

    def _on_continue(self, *args):
        self.dismiss()
        if self.continue_callback:
            self.continue_callback()
