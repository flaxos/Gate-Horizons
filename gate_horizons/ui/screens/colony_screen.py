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


class ColonyScreen(Screen):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.name = "colony_screen"
        self.game_state = None
        self.selected_colony = None
        self._build_ui()

    def _build_ui(self):
        root = BoxLayout(orientation="horizontal")

        with root.canvas.before:
            Color(0.02, 0.03, 0.08, 1)
            self._bg = Rectangle(pos=root.pos, size=root.size)
        root.bind(
            size=lambda w, v: setattr(self._bg, 'size', v),
            pos=lambda w, v: setattr(self._bg, 'pos', v),
        )

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
        self.add_widget(root)

    def set_game_state(self, game_state):
        self.game_state = game_state
        self._update_colony_list()

    def _update_colony_list(self):
        self.colony_list.clear_widgets()
        if not self.game_state:
            return

        for sid, colony in self.game_state.colonies.colonies.items():
            btn = Button(
                text=f"{colony.name}\nPop: {colony.population} | T{colony.get_tier()}",
                size_hint_y=None,
                height=dp(50),
                font_size="12sp",
                background_color=(0.12, 0.25, 0.4, 0.8),
                color=(0.85, 0.95, 1, 1),
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
        self._update_detail()

    def _update_detail(self):
        self.detail_panel.clear_widgets()
        if not self.game_state or not self.selected_colony:
            return

        colony = self.game_state.colonies.colonies.get(self.selected_colony)
        if not colony:
            return

        # Header
        self.detail_panel.add_widget(Label(
            text=colony.name,
            font_size="18sp",
            bold=True,
            color=(0.3, 0.85, 1, 1),
            size_hint_y=None,
            height=dp(36),
        ))

        tier_names = {1: "Core World", 2: "Developing", 3: "Frontier Outpost"}
        self.detail_panel.add_widget(Label(
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
        stats.add_widget(Label(
            text=f"Population: {colony.population}",
            font_size="13sp",
            color=(0.8, 0.9, 1, 1),
        ))

        happy_color = (0.2, 1, 0.4, 1) if colony.happiness >= 60 else (1, 0.5, 0.2, 1)
        stats.add_widget(Label(
            text=f"Happiness: {colony.happiness}%",
            font_size="13sp",
            color=happy_color,
        ))
        self.detail_panel.add_widget(stats)

        # Infrastructure grid
        self.detail_panel.add_widget(Label(
            text="Infrastructure",
            font_size="14sp",
            bold=True,
            color=(0.6, 0.8, 1, 1),
            size_hint_y=None,
            height=dp(28),
            halign="left",
            text_size=(None, None),
        ))

        infra_grid = GridLayout(
            cols=1,
            size_hint_y=None,
            spacing=dp(6),
            padding=[0, dp(4)],
        )
        infra_grid.bind(minimum_height=infra_grid.setter("height"))

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

            row = BoxLayout(orientation="horizontal", size_hint_y=None, height=dp(36))

            # Name and level
            status = f" (Building... {turns} turns)" if building else ""
            row.add_widget(Label(
                text=f"{label}: Level {level}{status}",
                font_size="12sp",
                color=(0.7, 0.85, 1, 1),
                size_hint_x=0.5,
                halign="left",
                text_size=(None, None),
            ))

            # Level bar
            bar = ProgressBar(max=5, value=level, size_hint_x=0.25)
            row.add_widget(bar)

            # Build button
            cost = colony.get_build_cost(infra_type)
            can_build = (
                not building
                and self.game_state.resources.can_afford(cost)
            )
            build_btn = Button(
                text="Build",
                size_hint_x=0.25,
                font_size="11sp",
                background_color=(0.15, 0.4, 0.2, 0.9) if can_build else (0.2, 0.2, 0.2, 0.5),
                color=(0.3, 1, 0.5, 1) if can_build else (0.4, 0.4, 0.4, 0.5),
                disabled=not can_build,
            )
            build_btn.infra_type = infra_type
            build_btn.bind(on_release=self._on_build)
            row.add_widget(build_btn)

            infra_grid.add_widget(row)

        self.detail_panel.add_widget(infra_grid)

        # Production summary
        self.detail_panel.add_widget(Label(
            text="Production / Consumption",
            font_size="14sp",
            bold=True,
            color=(0.6, 0.8, 1, 1),
            size_hint_y=None,
            height=dp(28),
            halign="left",
            text_size=(None, None),
        ))

        prod = colony.calculate_production()
        cons = colony.calculate_consumption()

        summary = BoxLayout(
            orientation="vertical",
            size_hint_y=None,
            height=dp(80),
        )

        prod_text = "  ".join(f"+{v} {k}" for k, v in prod.items() if v > 0)
        cons_text = "  ".join(f"-{v} {k}" for k, v in cons.items() if v > 0)

        summary.add_widget(Label(
            text=f"Produces: {prod_text}",
            font_size="11sp",
            color=(0.3, 1, 0.5, 0.9),
            size_hint_y=None,
            height=dp(22),
            halign="left",
            text_size=(None, None),
        ))
        summary.add_widget(Label(
            text=f"Consumes: {cons_text}",
            font_size="11sp",
            color=(1, 0.5, 0.3, 0.9),
            size_hint_y=None,
            height=dp(22),
            halign="left",
            text_size=(None, None),
        ))

        self.detail_panel.add_widget(summary)

        # Spacer
        self.detail_panel.add_widget(Widget())

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
            self._update_detail()

    def _go_back(self, *args):
        from kivy.app import App
        app = App.get_running_app()
        if app:
            app.switch_screen("galaxy_map")
