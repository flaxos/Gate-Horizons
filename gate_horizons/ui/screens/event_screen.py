"""Event popup screen for Gate Horizons."""

from kivy.uix.boxlayout import BoxLayout
from kivy.uix.button import Button
from kivy.uix.label import Label
from kivy.uix.popup import Popup
from kivy.uix.scrollview import ScrollView
from kivy.metrics import dp


class EventPopup(Popup):
    """Modal popup for displaying and resolving game events."""

    def __init__(self, event=None, game_state=None, on_resolved=None, **kwargs):
        self.event = event
        self.game_state = game_state
        self.on_resolved = on_resolved

        content = BoxLayout(orientation="vertical", spacing=dp(8), padding=dp(12))

        # Event description (scrollable)
        desc_scroll = ScrollView(size_hint=(1, 0.5))
        desc_label = Label(
            text=event.description if event else "",
            font_size="13sp",
            color=(0.75, 0.85, 0.95, 1),
            size_hint_y=None,
            text_size=(dp(400), None),
            halign="left",
            valign="top",
        )
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
                )
                btn.choice_index = i
                btn.bind(on_release=self._on_choice)
                choices_layout.add_widget(btn)

        content.add_widget(choices_layout)

        title_text = event.title if event else "Event"

        super().__init__(
            title=title_text,
            content=content,
            size_hint=(0.55, 0.65),
            title_color=(0.3, 0.85, 1, 1),
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
                on_continue=self.on_resolved,
            )
            outcome_popup.open()
        elif self.on_resolved:
            self.on_resolved()


class EventOutcomePopup(Popup):
    """Shows the result of an event choice."""

    def __init__(self, outcome=None, on_continue=None, **kwargs):
        self.continue_callback = on_continue

        content = BoxLayout(orientation="vertical", spacing=dp(8), padding=dp(12))

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
            font_size="16sp",
            bold=True,
            color=result_color,
            size_hint_y=None,
            height=dp(32),
        ))

        # Outcome description
        desc_scroll = ScrollView(size_hint=(1, 0.5))
        desc_label = Label(
            text=outcome.description if outcome else "",
            font_size="13sp",
            color=(0.75, 0.85, 0.95, 1),
            size_hint_y=None,
            text_size=(dp(380), None),
            halign="left",
            valign="top",
        )
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
                    font_size="12sp",
                    color=(0.3, 1, 0.5, 0.9),
                    size_hint_y=None,
                    height=dp(24),
                ))

            if outcome.costs_applied:
                costs_text = "Lost: " + ", ".join(
                    f"-{v} {k}" for k, v in outcome.costs_applied.items()
                )
                content.add_widget(Label(
                    text=costs_text,
                    font_size="12sp",
                    color=(1, 0.4, 0.3, 0.9),
                    size_hint_y=None,
                    height=dp(24),
                ))

        # Continue button
        continue_btn = Button(
            text="Continue",
            size_hint_y=None,
            height=dp(44),
            font_size="14sp",
            bold=True,
            background_color=(0.1, 0.35, 0.5, 0.9),
            color=(1, 1, 1, 1),
        )
        continue_btn.bind(on_release=self._on_continue)
        content.add_widget(continue_btn)

        super().__init__(
            title="Outcome",
            content=content,
            size_hint=(0.5, 0.55),
            title_color=(0.3, 0.85, 1, 1),
            separator_color=(0.15, 0.6, 0.8, 0.6),
            background_color=(0.04, 0.06, 0.12, 0.95),
            auto_dismiss=False,
            **kwargs,
        )

    def _on_continue(self, *args):
        self.dismiss()
        if self.continue_callback:
            self.continue_callback()
