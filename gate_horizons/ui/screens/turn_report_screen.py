"""Full-screen turn report summary screen."""

from kivy.uix.screenmanager import Screen
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.label import Label
from kivy.uix.button import Button
from kivy.uix.scrollview import ScrollView
from kivy.uix.widget import Widget
from kivy.graphics import Color, Rectangle
from kivy.metrics import dp


class TurnReportScreen(Screen):
    """Full-screen summary after processing a turn."""

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.name = "turn_report"
        self._report = None
        self._continue_callback = None
        self._view_encounters_callback = None
        self._return_screen = "galaxy_map"
        self._build_ui()

    def _build_ui(self):
        root = BoxLayout(orientation="vertical", spacing=dp(8), padding=dp(12))
        with root.canvas.before:
            Color(0.02, 0.03, 0.08, 1)
            self._bg = Rectangle(pos=root.pos, size=root.size)
        root.bind(
            size=lambda w, v: setattr(self._bg, "size", v),
            pos=lambda w, v: setattr(self._bg, "pos", v),
        )

        self.title_label = Label(
            text="Turn Report",
            font_size="18sp",
            bold=True,
            color=(0.3, 0.85, 1, 1),
            size_hint_y=None,
            height=dp(32),
        )
        root.add_widget(self.title_label)

        scroll = ScrollView(size_hint=(1, 1))
        self.report_layout = BoxLayout(
            orientation="vertical",
            spacing=dp(6),
            size_hint_y=None,
            padding=[0, dp(4), 0, dp(4)],
        )
        self.report_layout.bind(minimum_height=self.report_layout.setter("height"))
        scroll.add_widget(self.report_layout)
        root.add_widget(scroll)

        self.encounter_btn = Button(
            text="Resolve Encounters",
            size_hint_y=None,
            height=dp(40),
            font_size="13sp",
            bold=True,
            background_color=(0.35, 0.18, 0.4, 0.9),
            color=(1, 0.9, 1, 1),
        )
        self.encounter_btn.bind(on_release=self._on_view_encounters)
        root.add_widget(self.encounter_btn)

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
        root.add_widget(continue_btn)

        self.add_widget(root)

    def set_report(self, report, pending_encounters, on_continue, on_view_encounters, return_screen):
        self._report = report
        self._continue_callback = on_continue
        self._view_encounters_callback = on_view_encounters
        self._return_screen = return_screen or "galaxy_map"

        if report:
            self.title_label.text = f"Turn {report.turn_number} — {report.game_date}"
        else:
            self.title_label.text = "Turn Report"

        self.encounter_btn.opacity = 1 if pending_encounters else 0
        self.encounter_btn.disabled = not pending_encounters
        if pending_encounters:
            self.encounter_btn.text = f"Resolve Encounters ({pending_encounters})"

        self._build_sections()

    def _build_sections(self):
        self.report_layout.clear_widgets()
        report = self._report
        if not report:
            self.report_layout.add_widget(Label(
                text="No report data available.",
                font_size="12sp",
                color=(0.7, 0.85, 1, 0.9),
                size_hint_y=None,
                height=dp(24),
            ))
            return

        sections = [
            ("Research", self._research_lines(report), "tech_screen"),
            ("Production", self._production_lines(report), "production_screen"),
            ("Colonies", self._colony_lines(report), "colony_screen"),
            ("Fleet", self._fleet_lines(report), "fleet_screen"),
            ("Events", self._event_lines(report), "encounter_screen"),
        ]

        for title, lines, screen_name in sections:
            self._add_section(title, lines, screen_name)

    def _add_section(self, title, lines, screen_name):
        header = BoxLayout(
            orientation="horizontal",
            size_hint_y=None,
            height=dp(28),
            spacing=dp(8),
        )
        header.add_widget(Label(
            text=title,
            font_size="14sp",
            bold=True,
            color=(0.6, 0.8, 1, 1),
            size_hint_x=0.8,
            halign="left",
            valign="middle",
        ))
        open_btn = Button(
            text="Open",
            size_hint_x=0.2,
            font_size="11sp",
            background_color=(0.08, 0.15, 0.25, 0.8),
            color=(0.7, 0.85, 1, 1),
        )
        open_btn.bind(on_release=lambda *_: self._navigate_to(screen_name))
        header.add_widget(open_btn)
        self.report_layout.add_widget(header)

        if not lines:
            self.report_layout.add_widget(Label(
                text="No updates this turn.",
                font_size="11sp",
                color=(0.5, 0.65, 0.8, 0.8),
                size_hint_y=None,
                height=dp(20),
            ))
        else:
            for line in lines:
                self.report_layout.add_widget(Label(
                    text=f"• {line}",
                    font_size="11sp",
                    color=(0.7, 0.85, 1, 0.9),
                    size_hint_y=None,
                    height=dp(20),
                    halign="left",
                    valign="middle",
                ))

        self.report_layout.add_widget(Widget(size_hint_y=None, height=dp(8)))

    @staticmethod
    def _format_dict_items(items):
        if not items:
            return []
        return [f"{key}: {value}" for key, value in items.items()]

    @staticmethod
    def _format_list_items(items, label=None):
        lines = []
        for item in items or []:
            if isinstance(item, dict):
                lines.append(item.get("summary") or item.get("name") or label or "Update")
            else:
                lines.append(str(item))
        return lines

    def _research_lines(self, report):
        lines = []
        if report.tech_completed:
            lines.append(f"Tech completed: {report.tech_completed}")
        return lines

    def _production_lines(self, report):
        lines = []
        lines.extend(self._format_list_items(report.construction_completed, "Construction completed"))
        if report.shipyard_report:
            lines.extend(self._format_dict_items(report.shipyard_report))
        if report.mining_output:
            lines.append(f"Mining output: {', '.join(self._format_dict_items(report.mining_output))}")
        return lines

    def _colony_lines(self, report):
        lines = []
        lines.extend(self._format_list_items(report.colony_reports, "Colony update"))
        if report.shortage_reports:
            lines.append(f"Shortages: {', '.join(self._format_dict_items(report.shortage_reports))}")
        if report.colony_ledger_summary:
            lines.append(report.colony_ledger_summary)
        return lines

    def _fleet_lines(self, report):
        lines = []
        lines.extend(self._format_list_items(report.ships_moved, "Ship movement"))
        lines.extend(self._format_list_items(report.ship_actions, "Ship action"))
        lines.extend(self._format_list_items(report.ship_orders, "Ship order"))
        return lines

    def _event_lines(self, report):
        lines = []
        lines.extend(self._format_list_items(report.events_triggered, "Event"))
        lines.extend(self._format_list_items(report.combat_encounters, "Combat"))
        lines.extend(self._format_list_items(report.discoveries, "Discovery"))
        lines.extend(self._format_list_items(report.warnings, "Warning"))
        if report.milestone_reached:
            lines.append(f"Milestone: {report.milestone_reached}")
        if report.missions_completed:
            lines.extend(self._format_list_items(report.missions_completed, "Mission complete"))
        return lines

    def _navigate_to(self, screen_name):
        from kivy.app import App
        app = App.get_running_app()
        if app:
            app.switch_screen(screen_name)

    def _on_continue(self, *args):
        from kivy.app import App
        app = App.get_running_app()
        if self._continue_callback:
            self._continue_callback()
        if app:
            app.switch_screen(self._return_screen)

    def _on_view_encounters(self, *args):
        if self._view_encounters_callback:
            self._view_encounters_callback()
