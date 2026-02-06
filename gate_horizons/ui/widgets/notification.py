"""Turn report and notification widgets for Gate Horizons."""

from kivy.uix.boxlayout import BoxLayout
from kivy.uix.label import Label
from kivy.uix.button import Button
from kivy.uix.popup import Popup
from kivy.uix.scrollview import ScrollView
from kivy.metrics import dp


class TurnReportPopup(Popup):
    """Shows the turn report summary after processing a turn."""

    def __init__(self, report=None, on_continue=None, **kwargs):
        self.continue_callback = on_continue

        content = BoxLayout(orientation="vertical", spacing=dp(4), padding=dp(8))

        scroll = ScrollView(size_hint=(1, 0.85))
        report_layout = BoxLayout(
            orientation="vertical",
            spacing=dp(2),
            size_hint_y=None,
        )
        report_layout.bind(minimum_height=report_layout.setter("height"))

        if report:
            lines = report.get_summary_lines()
            for line in lines:
                color = (0.7, 0.85, 1, 1)
                if line.startswith("WARNING:"):
                    color = (1, 0.5, 0.3, 1)
                elif line.startswith("EVENT:"):
                    color = (0.3, 1, 0.7, 1)
                elif line.startswith("COMBAT:"):
                    color = (1, 0.3, 0.3, 1)
                elif line.startswith("RESEARCH"):
                    color = (0.5, 0.8, 1, 1)
                elif line.startswith("MILESTONE:"):
                    color = (1, 1, 0.3, 1)
                elif not line:
                    # Spacer
                    spacer = Label(size_hint_y=None, height=dp(8))
                    report_layout.add_widget(spacer)
                    continue

                lbl = Label(
                    text=line,
                    size_hint_y=None,
                    height=dp(24),
                    font_size="13sp",
                    color=color,
                    text_size=(None, None),
                    halign="left",
                    valign="middle",
                )
                report_layout.add_widget(lbl)

        scroll.add_widget(report_layout)
        content.add_widget(scroll)

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

        title_text = ""
        if report:
            title_text = f"Turn {report.turn_number} - {report.game_date}"

        super().__init__(
            title=title_text,
            content=content,
            size_hint=(0.55, 0.7),
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
