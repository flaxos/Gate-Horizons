"""Colony management screen for Gate Horizons."""

from kivy.uix.screenmanager import Screen
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.gridlayout import GridLayout
from kivy.uix.button import Button
from kivy.uix.label import Label
from kivy.uix.widget import Widget
from kivy.uix.scrollview import ScrollView
from kivy.uix.progressbar import ProgressBar
from kivy.graphics import Color, Rectangle
from kivy.metrics import dp

from ..widgets.resource_bar import TopBar
from gate_horizons.game.colonies import INFRASTRUCTURE_TYPES, BUILD_COSTS, BUILD_TURNS


class ColonyScreen(Screen):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.name = "colony_screen"
        self.game_state = None
        self.selected_colony = None
        self._build_ui()

    def _build_ui(self):
        outer = BoxLayout(orientation="vertical")

        with outer.canvas.before:
            Color(0.02, 0.03, 0.08, 1)
            self._bg = Rectangle(pos=outer.pos, size=outer.size)
        outer.bind(
            size=lambda w, v: setattr(self._bg, 'size', v),
            pos=lambda w, v: setattr(self._bg, 'pos', v),
        )

        # Top bar
        self.top_bar = TopBar()
        outer.add_widget(self.top_bar)

        root = BoxLayout(orientation="horizontal")

        # Left: colony list
        left_panel = BoxLayout(
            orientation="vertical",
            size_hint_x=0.3,
            padding=dp(8),
            spacing=dp(4),
        )

        left_panel.add_widget(Label(
            text="Colonies",
            font_size="16sp",
            bold=True,
            color=(0.3, 0.85, 1, 1),
            size_hint_y=None,
            height=dp(36),
        ))

        self.colony_list = BoxLayout(
            orientation="vertical",
            spacing=dp(4),
            size_hint_y=None,
        )
        self.colony_list.bind(minimum_height=self.colony_list.setter("height"))

        scroll = ScrollView(size_hint=(1, 1))
        scroll.add_widget(self.colony_list)
        left_panel.add_widget(scroll)

        back_btn = Button(
            text="< Back to Map",
            size_hint_y=None,
            height=dp(36),
            font_size="12sp",
            background_color=(0.08, 0.15, 0.25, 0.8),
            color=(0.7, 0.85, 1, 1),
        )
        back_btn.bind(on_release=self._go_back)
        left_panel.add_widget(back_btn)

        root.add_widget(left_panel)

        # Right: colony detail
        self.detail_panel = BoxLayout(
            orientation="vertical",
            size_hint_x=0.7,
            padding=dp(12),
            spacing=dp(6),
        )
        with self.detail_panel.canvas.before:
            Color(0.04, 0.06, 0.12, 0.95)
            self._detail_bg = Rectangle(pos=self.detail_panel.pos, size=self.detail_panel.size)
        self.detail_panel.bind(
            size=lambda w, v: setattr(self._detail_bg, 'size', v),
            pos=lambda w, v: setattr(self._detail_bg, 'pos', v),
        )

        root.add_widget(self.detail_panel)
        outer.add_widget(root)
        self.add_widget(outer)

    def set_game_state(self, game_state):
        self.game_state = game_state
        self.top_bar.update(game_state)
        self._update_colony_list()

    def _update_colony_list(self):
        self.colony_list.clear_widgets()
        if not self.game_state:
            return

        for sid, colony in self.game_state.colonies.colonies.items():
            is_selected = sid == self.selected_colony
            btn = Button(
                text=f"{colony.name}\nPop: {colony.population} | T{colony.get_tier()}",
                size_hint_y=None,
                height=dp(50),
                font_size="12sp",
                background_color=(0.2, 0.4, 0.6, 0.9) if is_selected else (0.12, 0.25, 0.4, 0.8),
                color=(1, 1, 1, 1) if is_selected else (0.85, 0.95, 1, 1),
                halign="left",
                valign="middle",
            )
            btn.colony_id = sid
            btn.bind(on_release=lambda b: self._select_colony(b.colony_id))
            self.colony_list.add_widget(btn)

        if not self.game_state.colonies.colonies:
            self.colony_list.add_widget(Label(
                text="No colonies established",
                font_size="13sp",
                color=(0.5, 0.5, 0.6, 0.7),
                size_hint_y=None,
                height=dp(30),
            ))

        # Auto-select first colony
        if self.game_state.colonies.colonies and not self.selected_colony:
            first_id = next(iter(self.game_state.colonies.colonies))
            self._select_colony(first_id)

    def _select_colony(self, colony_id):
        self.selected_colony = colony_id
        self._update_colony_list()
        self._update_detail()

    def _update_detail(self):
        self.detail_panel.clear_widgets()
        if not self.game_state or not self.selected_colony:
            return

        colony = self.game_state.colonies.colonies.get(self.selected_colony)
        if not colony:
            return

        # Scrollable detail content
        scroll = ScrollView(size_hint=(1, 1))
        detail_content = BoxLayout(
            orientation="vertical",
            spacing=dp(6),
            size_hint_y=None,
            padding=[0, dp(4)],
        )
        detail_content.bind(minimum_height=detail_content.setter("height"))

        # Header
        detail_content.add_widget(Label(
            text=colony.name,
            font_size="18sp",
            bold=True,
            color=(0.3, 0.85, 1, 1),
            size_hint_y=None,
            height=dp(36),
        ))

        tier_names = {1: "Core World", 2: "Developing", 3: "Frontier Outpost"}
        detail_content.add_widget(Label(
            text=f"Tier {colony.get_tier()} - {tier_names.get(colony.get_tier(), 'Unknown')}",
            font_size="12sp",
            color=(0.5, 0.7, 0.9, 0.8),
            size_hint_y=None,
            height=dp(22),
        ))

        # Stats row
        stats = BoxLayout(
            orientation="horizontal",
            size_hint_y=None,
            height=dp(40),
            spacing=dp(16),
        )

        housing_level = colony.infrastructure.get("housing", {}).get("level", 0)
        housing_cap = 100 + housing_level * 150
        stats.add_widget(Label(
            text=f"Population: {colony.population}/{housing_cap}",
            font_size="13sp",
            color=(0.8, 0.9, 1, 1),
        ))

        happy_color = (0.2, 1, 0.4, 1) if colony.happiness >= 60 else (1, 0.5, 0.2, 1)
        stats.add_widget(Label(
            text=f"Happiness: {colony.happiness}%",
            font_size="13sp",
            color=happy_color,
        ))
        detail_content.add_widget(stats)

        # Warnings
        warnings = []
        if colony.population > housing_cap * 0.9:
            warnings.append("Overcrowding! Build more housing.")
        if colony.happiness < 40:
            warnings.append("Low happiness - population growth reduced!")
        if colony.happiness < 30:
            warnings.append("Colony unrest! Immediate attention needed.")

        for warning in warnings:
            detail_content.add_widget(Label(
                text=f"WARNING: {warning}",
                font_size="11sp",
                color=(1, 0.4, 0.2, 1),
                size_hint_y=None,
                height=dp(20),
                halign="left",
                text_size=(dp(500), None),
            ))

        # Infrastructure grid
        detail_content.add_widget(Label(
            text="Infrastructure",
            font_size="14sp",
            bold=True,
            color=(0.6, 0.8, 1, 1),
            size_hint_y=None,
            height=dp(28),
            halign="left",
            text_size=(dp(500), None),
        ))

        infra_labels = {
            "housing": "Housing",
            "industry": "Industry",
            "defense": "Defense",
            "research": "Research Lab",
            "spaceport": "Spaceport",
        }

        for infra_type, label in infra_labels.items():
            infra = colony.infrastructure.get(infra_type, {})
            level = infra.get("level", 0)
            building = infra.get("building", False)
            turns = infra.get("turns_remaining", 0)

            row = BoxLayout(orientation="horizontal", size_hint_y=None, height=dp(38))

            # Name and level
            status = f" (Building... {turns} turns)" if building else ""
            row.add_widget(Label(
                text=f"{label}: Lv {level}{status}",
                font_size="12sp",
                color=(1, 1, 0.3, 1) if building else (0.7, 0.85, 1, 1),
                size_hint_x=0.4,
                halign="left",
                text_size=(dp(200), None),
            ))

            # Level bar
            bar = ProgressBar(max=5, value=level, size_hint_x=0.2)
            row.add_widget(bar)

            # Cost display
            cost = colony.get_build_cost(infra_type)
            cost_text = ", ".join(f"{v}{k[0].upper()}" for k, v in cost.items())
            build_turns = max(1, BUILD_TURNS.get(infra_type, 3))
            row.add_widget(Label(
                text=f"{cost_text} | {build_turns}t",
                font_size="10sp",
                color=(0.5, 0.6, 0.7, 0.8),
                size_hint_x=0.2,
            ))

            # Build / Queue button
            can_build = (
                not building
                and self.game_state.resources.can_afford(cost)
            )
            if building:
                # Allow queuing
                queue_btn = Button(
                    text="Queue",
                    size_hint_x=0.2,
                    font_size="11sp",
                    background_color=(0.2, 0.25, 0.4, 0.8),
                    color=(0.6, 0.7, 0.9, 1),
                )
                queue_btn.infra_type = infra_type
                queue_btn.bind(on_release=self._on_queue)
                row.add_widget(queue_btn)
            else:
                build_btn = Button(
                    text="Build",
                    size_hint_x=0.2,
                    font_size="11sp",
                    background_color=(0.15, 0.4, 0.2, 0.9) if can_build else (0.2, 0.2, 0.2, 0.5),
                    color=(0.3, 1, 0.5, 1) if can_build else (0.4, 0.4, 0.4, 0.5),
                    disabled=not can_build,
                )
                build_btn.infra_type = infra_type
                build_btn.bind(on_release=self._on_build)
                row.add_widget(build_btn)

            detail_content.add_widget(row)

        # Build queue display
        if colony.build_queue:
            detail_content.add_widget(Label(
                text="Build Queue:",
                font_size="12sp",
                bold=True,
                color=(0.6, 0.8, 1, 1),
                size_hint_y=None,
                height=dp(24),
                halign="left",
                text_size=(dp(500), None),
            ))
            for i, item in enumerate(colony.build_queue):
                q_row = BoxLayout(orientation="horizontal", size_hint_y=None, height=dp(28))
                q_row.add_widget(Label(
                    text=f"  {i+1}. {infra_labels.get(item['type'], item['type'])}",
                    font_size="11sp",
                    color=(0.6, 0.75, 0.9, 0.8),
                    size_hint_x=0.7,
                    halign="left",
                    text_size=(dp(300), None),
                ))
                cancel_btn = Button(
                    text="Cancel",
                    size_hint_x=0.3,
                    font_size="10sp",
                    background_color=(0.3, 0.1, 0.1, 0.7),
                    color=(1, 0.6, 0.6, 1),
                )
                cancel_btn.queue_index = i
                cancel_btn.bind(on_release=self._on_cancel_queue)
                q_row.add_widget(cancel_btn)
                detail_content.add_widget(q_row)

        # Production summary
        detail_content.add_widget(Label(
            text="Production / Consumption",
            font_size="14sp",
            bold=True,
            color=(0.6, 0.8, 1, 1),
            size_hint_y=None,
            height=dp(28),
            halign="left",
            text_size=(dp(500), None),
        ))

        prod = colony.calculate_production()
        cons = colony.calculate_consumption()

        prod_text = "  ".join(f"+{v} {k}" for k, v in prod.items() if v > 0)
        cons_text = "  ".join(f"-{v} {k}" for k, v in cons.items() if v > 0)

        detail_content.add_widget(Label(
            text=f"Produces: {prod_text or 'nothing'}",
            font_size="11sp",
            color=(0.3, 1, 0.5, 0.9),
            size_hint_y=None,
            height=dp(22),
            halign="left",
            text_size=(dp(500), None),
        ))
        detail_content.add_widget(Label(
            text=f"Consumes: {cons_text or 'nothing'}",
            font_size="11sp",
            color=(1, 0.5, 0.3, 0.9),
            size_hint_y=None,
            height=dp(22),
            halign="left",
            text_size=(dp(500), None),
        ))

        # Net summary
        net = {}
        for r in set(list(prod.keys()) + list(cons.keys())):
            net[r] = prod.get(r, 0) - cons.get(r, 0)
        net_text = "  ".join(
            f"{'+'if v>=0 else ''}{v} {k}" for k, v in net.items() if v != 0
        )
        detail_content.add_widget(Label(
            text=f"Net: {net_text or 'balanced'}",
            font_size="11sp",
            color=(0.7, 0.85, 1, 0.9),
            size_hint_y=None,
            height=dp(22),
            halign="left",
            text_size=(dp(500), None),
        ))

        # Growth projection
        growth_rate = 0.05
        if colony.happiness >= 80:
            growth_rate += 0.02
        elif colony.happiness < 40:
            growth_rate -= 0.03
        projected_growth = max(1, int(colony.population * growth_rate))
        if colony.population >= housing_cap:
            projected_growth = 0
        detail_content.add_widget(Label(
            text=f"Growth: ~+{projected_growth} pop/turn",
            font_size="11sp",
            color=(0.5, 0.8, 1, 0.8),
            size_hint_y=None,
            height=dp(22),
            halign="left",
            text_size=(dp(500), None),
        ))

        scroll.add_widget(detail_content)
        self.detail_panel.add_widget(scroll)

    def _on_build(self, btn):
        if not self.game_state or not self.selected_colony:
            return

        colony = self.game_state.colonies.colonies.get(self.selected_colony)
        if not colony:
            return

        cost = colony.get_build_cost(btn.infra_type)
        if self.game_state.resources.can_afford(cost):
            self.game_state.resources.spend_dict(cost)
            colony.start_construction(btn.infra_type)
            self.top_bar.update(self.game_state)
            self._update_detail()

    def _on_queue(self, btn):
        if not self.game_state or not self.selected_colony:
            return

        colony = self.game_state.colonies.colonies.get(self.selected_colony)
        if not colony:
            return

        colony.queue_construction(btn.infra_type)
        self._update_detail()

    def _on_cancel_queue(self, btn):
        if not self.game_state or not self.selected_colony:
            return

        colony = self.game_state.colonies.colonies.get(self.selected_colony)
        if not colony:
            return

        if 0 <= btn.queue_index < len(colony.build_queue):
            colony.build_queue.pop(btn.queue_index)
            self._update_detail()

    def _go_back(self, *args):
        from kivy.app import App
        app = App.get_running_app()
        if app:
            app.switch_screen("galaxy_map")
