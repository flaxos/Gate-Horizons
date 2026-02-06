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

from ..widgets.resource_bar import TopBar


class TechDetailPopup(Popup):
    """Shows detailed tech info and allows starting research."""

    def __init__(self, tech=None, tech_tree=None, resources=None, on_research=None, **kwargs):
        self.tech = tech
        self.tech_tree = tech_tree
        self.resources = resources
        self.research_callback = on_research

        content = BoxLayout(orientation="vertical", spacing=dp(8), padding=dp(12))

        # Tech name
        content.add_widget(Label(
            text=tech.name if tech else "",
            font_size="16sp",
            bold=True,
            color=(0.3, 0.85, 1, 1),
            size_hint_y=None,
            height=dp(30),
        ))

        # Branch and tier
        content.add_widget(Label(
            text=f"Branch: {tech.branch.title()}  |  {tech.tier.replace('tier', 'Tier ')}",
            font_size="12sp",
            color=(0.5, 0.7, 0.9, 0.8),
            size_hint_y=None,
            height=dp(22),
        ))

        # Description
        desc_label = Label(
            text=tech.description if tech else "",
            font_size="12sp",
            color=(0.7, 0.85, 1, 0.9),
            size_hint_y=None,
            text_size=(dp(350), None),
            halign="left",
            valign="top",
        )
        desc_label.bind(texture_size=desc_label.setter("size"))
        content.add_widget(desc_label)

        # Effects
        if tech and tech.effect:
            effects_text = "Effects:\n"
            for k, v in tech.effect.items():
                effects_text += f"  {k.replace('_', ' ').title()}: {v}\n"
            content.add_widget(Label(
                text=effects_text.strip(),
                font_size="11sp",
                color=(0.3, 1, 0.5, 0.9),
                size_hint_y=None,
                height=dp(20 + len(tech.effect) * 18),
                text_size=(dp(350), None),
                halign="left",
                valign="top",
            ))

        # Prerequisites
        if tech and tech.prerequisites:
            prereq_names = []
            for pid in tech.prerequisites:
                p = tech_tree.techs.get(pid) if tech_tree else None
                pname = p.name if p else pid
                status = " [done]" if (p and p.researched) else " [needed]"
                prereq_names.append(f"  {pname}{status}")
            prereq_text = "Prerequisites:\n" + "\n".join(prereq_names)
            content.add_widget(Label(
                text=prereq_text,
                font_size="11sp",
                color=(0.6, 0.7, 0.9, 0.8),
                size_hint_y=None,
                height=dp(20 + len(tech.prerequisites) * 18),
                text_size=(dp(350), None),
                halign="left",
                valign="top",
            ))

        # Cost and status
        if tech:
            if tech.researched:
                content.add_widget(Label(
                    text="RESEARCHED",
                    font_size="14sp",
                    bold=True,
                    color=(0.3, 1, 0.5, 1),
                    size_hint_y=None,
                    height=dp(28),
                ))
            elif tech.researching:
                content.add_widget(Label(
                    text=f"IN PROGRESS - {tech.turns_remaining} turns remaining",
                    font_size="13sp",
                    bold=True,
                    color=(1, 1, 0.3, 1),
                    size_hint_y=None,
                    height=dp(28),
                ))
                # Show progress bar
                total_turns = tech.cost.get("turns", 3)
                elapsed = total_turns - tech.turns_remaining
                bar = ProgressBar(
                    max=total_turns,
                    value=elapsed,
                    size_hint_y=None,
                    height=dp(20),
                )
                content.add_widget(bar)
            elif tech_tree and tech_tree.can_research(tech.id):
                cost_parts = []
                for k, v in tech.cost.items():
                    cost_parts.append(f"{v} {k}")
                cost_text = ", ".join(cost_parts)
                can_afford = resources.can_afford(tech.cost) if resources else False

                research_btn = Button(
                    text=f"Begin Research ({cost_text})",
                    size_hint_y=None,
                    height=dp(40),
                    font_size="13sp",
                    background_color=(0.15, 0.4, 0.2, 0.9) if can_afford else (0.2, 0.2, 0.2, 0.5),
                    color=(0.3, 1, 0.5, 1) if can_afford else (0.4, 0.4, 0.4, 0.5),
                    disabled=not can_afford,
                )
                research_btn.bind(on_release=self._on_research)
                content.add_widget(research_btn)

                if not can_afford:
                    content.add_widget(Label(
                        text="Insufficient resources",
                        font_size="11sp",
                        color=(1, 0.4, 0.3, 0.8),
                        size_hint_y=None,
                        height=dp(20),
                    ))
            else:
                content.add_widget(Label(
                    text="LOCKED - prerequisites not met",
                    font_size="12sp",
                    color=(0.4, 0.4, 0.5, 0.6),
                    size_hint_y=None,
                    height=dp(24),
                ))

        # Close button
        close_btn = Button(
            text="Close",
            size_hint_y=None,
            height=dp(36),
            font_size="12sp",
            background_color=(0.15, 0.15, 0.2, 0.8),
            color=(0.7, 0.7, 0.8, 1),
        )
        close_btn.bind(on_release=lambda x: self.dismiss())
        content.add_widget(close_btn)

        content.add_widget(Widget())

        super().__init__(
            title=tech.name if tech else "Tech Details",
            content=content,
            size_hint=(0.45, 0.7),
            title_color=(0.3, 0.85, 1, 1),
            separator_color=(0.15, 0.6, 0.8, 0.6),
            background_color=(0.04, 0.06, 0.12, 0.95),
            **kwargs,
        )

    def _on_research(self, *args):
        self.dismiss()
        if self.research_callback and self.tech:
            self.research_callback(self.tech.id)


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

        # Top bar
        self.top_bar = TopBar()
        root.add_widget(self.top_bar)

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
            size_hint_x=0.4,
            halign="left",
            text_size=(None, None),
        ))

        self.research_status = Label(
            text="No active research",
            font_size="12sp",
            color=(0.5, 0.7, 0.9, 0.8),
            size_hint_x=0.4,
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

        # Active research progress bar
        self.progress_bar_container = BoxLayout(
            orientation="horizontal",
            size_hint_y=None,
            height=dp(24),
            padding=[dp(8), dp(2)],
            spacing=dp(4),
        )
        self.research_progress = ProgressBar(max=1, value=0, size_hint_x=0.8)
        self.progress_label = Label(
            text="",
            font_size="10sp",
            color=(1, 1, 0.3, 0.9),
            size_hint_x=0.2,
        )
        self.progress_bar_container.add_widget(self.research_progress)
        self.progress_bar_container.add_widget(self.progress_label)
        root.add_widget(self.progress_bar_container)

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
        self.top_bar.update(game_state)
        self._update_tree()

    def _update_tree(self):
        self.tree_layout.clear_widgets()
        if not self.game_state:
            return

        # Update research status and progress
        if self.game_state.tech.active_research:
            tech = self.game_state.tech.techs.get(self.game_state.tech.active_research)
            if tech:
                self.research_status.text = f"Researching: {tech.name} ({tech.turns_remaining} turns)"
                total_turns = tech.cost.get("turns", 3)
                elapsed = total_turns - tech.turns_remaining
                self.research_progress.max = total_turns
                self.research_progress.value = elapsed
                self.progress_label.text = f"{elapsed}/{total_turns} turns"
            else:
                self.research_status.text = "No active research"
                self.research_progress.value = 0
                self.progress_label.text = ""
        else:
            self.research_status.text = "No active research"
            self.research_progress.value = 0
            self.progress_label.text = ""

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
                width=dp(220),
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
                    height=dp(90),
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
                    text_size=(dp(200), None),
                ))

                card.add_widget(Label(
                    text=tech.description[:60] + ("..." if len(tech.description) > 60 else ""),
                    font_size="10sp",
                    color=(0.5, 0.6, 0.7, 0.8),
                    size_hint_y=None,
                    height=dp(16),
                    halign="left",
                    text_size=(dp(200), None),
                ))

                # Cost / Status row
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
                elif status.startswith("IN PROGRESS"):
                    # Mini progress bar
                    total_turns = tech.cost.get("turns", 3)
                    elapsed = total_turns - tech.turns_remaining
                    bar = ProgressBar(
                        max=total_turns,
                        value=elapsed,
                        size_hint_y=None,
                        height=dp(10),
                    )
                    card.add_widget(bar)
                    card.add_widget(Label(
                        text=status,
                        font_size="10sp",
                        color=text_color,
                        size_hint_y=None,
                        height=dp(16),
                    ))
                else:
                    card.add_widget(Label(
                        text=status,
                        font_size="10sp",
                        color=text_color,
                        size_hint_y=None,
                        height=dp(20),
                    ))

                # Tap card to see details
                detail_btn = Button(
                    text="Details",
                    size_hint_y=None,
                    height=dp(22),
                    font_size="9sp",
                    background_color=(0.1, 0.15, 0.25, 0.6),
                    color=(0.5, 0.65, 0.8, 0.8),
                )
                detail_btn.tech_id = tech.id
                detail_btn.bind(on_release=self._show_tech_detail)
                card.add_widget(detail_btn)

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
            self.top_bar.update(self.game_state)
            self._update_tree()

    def _show_tech_detail(self, btn):
        if not self.game_state:
            return
        tech = self.game_state.tech.techs.get(btn.tech_id)
        if not tech:
            return

        popup = TechDetailPopup(
            tech=tech,
            tech_tree=self.game_state.tech,
            resources=self.game_state.resources,
            on_research=self._start_research_from_detail,
        )
        popup.open()

    def _start_research_from_detail(self, tech_id):
        if not self.game_state:
            return
        result = self.game_state.tech.start_research(
            tech_id, self.game_state.resources
        )
        if result:
            self.top_bar.update(self.game_state)
            self._update_tree()

    def _go_back(self, *args):
        from kivy.app import App
        app = App.get_running_app()
        if app:
            app.switch_screen("galaxy_map")
