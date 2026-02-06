"""Fleet management screen for Gate Horizons."""

from kivy.uix.screenmanager import Screen
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.button import Button
from kivy.uix.label import Label
from kivy.uix.widget import Widget
from kivy.uix.scrollview import ScrollView
from kivy.uix.progressbar import ProgressBar
from kivy.graphics import Color, Rectangle
from kivy.metrics import dp

from ..widgets.context_menu import ContextMenu


class FleetScreen(Screen):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.name = "fleet_screen"
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
            text="Fleet Overview",
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

        # Fleet list
        scroll = ScrollView(size_hint=(1, 1))
        self.ship_list = BoxLayout(
            orientation="vertical",
            spacing=dp(4),
            size_hint_y=None,
            padding=[dp(8), dp(4)],
        )
        self.ship_list.bind(minimum_height=self.ship_list.setter("height"))
        scroll.add_widget(self.ship_list)
        root.add_widget(scroll)

        # Maintenance summary
        self.maint_label = Label(
            text="Total Maintenance: 0 credits/turn",
            font_size="12sp",
            color=(1, 0.7, 0.3, 0.9),
            size_hint_y=None,
            height=dp(28),
        )
        root.add_widget(self.maint_label)

        self.add_widget(root)

    def set_game_state(self, game_state):
        self.game_state = game_state
        self._update_list()

    def _update_list(self):
        self.ship_list.clear_widgets()
        if not self.game_state:
            return

        class_colors = {
            "scout": (0.3, 1, 0.7, 0.9),
            "freighter": (1, 0.8, 0.2, 0.9),
            "miner": (0.8, 0.5, 0.2, 0.9),
            "corvette": (1, 0.3, 0.3, 0.9),
        }

        for ship in sorted(
            self.game_state.fleet.ships.values(),
            key=lambda s: s.ship_class,
        ):
            card = BoxLayout(
                orientation="horizontal",
                size_hint_y=None,
                height=dp(56),
                spacing=dp(8),
                padding=[dp(8), dp(4)],
            )
            with card.canvas.before:
                Color(0.06, 0.1, 0.18, 0.9)
                card_bg = Rectangle(pos=card.pos, size=card.size)
            card.bind(
                size=lambda w, v, bg=card_bg: setattr(bg, 'size', v),
                pos=lambda w, v, bg=card_bg: setattr(bg, 'pos', v),
            )

            # Ship class icon/color indicator
            indicator = Widget(size_hint=(None, 1), width=dp(8))
            color = class_colors.get(ship.ship_class, (0.5, 0.5, 0.5, 0.9))
            with indicator.canvas:
                Color(*color)
                ind_rect = Rectangle(pos=indicator.pos, size=indicator.size)
            indicator.bind(
                size=lambda w, v, r=ind_rect: setattr(r, 'size', v),
                pos=lambda w, v, r=ind_rect: setattr(r, 'pos', v),
            )
            card.add_widget(indicator)

            # Ship info
            info = BoxLayout(orientation="vertical", size_hint_x=0.4)
            info.add_widget(Label(
                text=ship.name,
                font_size="13sp",
                bold=True,
                color=(0.85, 0.95, 1, 1),
                halign="left",
                text_size=(None, None),
            ))

            mission = ship.mission or "Idle"
            system = self.game_state.galaxy.systems.get(ship.location)
            loc_name = system.name if system else ship.location
            info.add_widget(Label(
                text=f"{ship.ship_class.title()} @ {loc_name} | {mission}",
                font_size="10sp",
                color=(0.5, 0.7, 0.9, 0.8),
                halign="left",
                text_size=(None, None),
            ))
            card.add_widget(info)

            # Hull bar
            hull_box = BoxLayout(orientation="vertical", size_hint_x=0.2)
            hull_box.add_widget(Label(
                text=f"Hull: {ship.hull}/{ship.stats.max_hull}",
                font_size="10sp",
                color=(0.7, 0.85, 1, 0.9),
                size_hint_y=0.4,
            ))
            hull_bar = ProgressBar(
                max=ship.stats.max_hull,
                value=ship.hull,
                size_hint_y=0.3,
            )
            hull_box.add_widget(hull_bar)
            hull_box.add_widget(Label(
                text=f"Fuel: {ship.fuel}/{ship.stats.fuel_capacity}",
                font_size="10sp",
                color=(0.7, 0.85, 1, 0.9),
                size_hint_y=0.3,
            ))
            card.add_widget(hull_box)

            # Cargo
            cargo_text = ", ".join(f"{v} {k}" for k, v in ship.cargo.items()) if ship.cargo else "Empty"
            card.add_widget(Label(
                text=f"Cargo: {cargo_text}\n({ship.cargo_used}/{ship.stats.cargo_capacity})",
                font_size="10sp",
                color=(0.6, 0.75, 0.9, 0.8),
                size_hint_x=0.2,
                halign="left",
                text_size=(None, None),
            ))

            # Actions button
            action_btn = Button(
                text="Actions",
                size_hint=(None, 1),
                width=dp(70),
                font_size="11sp",
                background_color=(0.12, 0.25, 0.4, 0.8),
                color=(0.85, 0.95, 1, 1),
            )
            action_btn.ship_id = ship.id
            action_btn.bind(on_release=self._show_actions)
            card.add_widget(action_btn)

            self.ship_list.add_widget(card)

        total_maint = self.game_state.fleet.get_total_maintenance()
        self.maint_label.text = f"Total Maintenance: {total_maint} credits/turn | Ships: {len(self.game_state.fleet.ships)}"

    def _show_actions(self, btn):
        if not self.game_state:
            return

        actions = self.game_state.fleet.get_contextual_actions(
            btn.ship_id,
            galaxy=self.game_state.galaxy,
            colonies=self.game_state.colonies,
        )

        ship = self.game_state.fleet.ships.get(btn.ship_id)
        title = f"{ship.name}" if ship else "Ship Actions"

        menu = ContextMenu(
            title_text=title,
            actions=actions,
            callback=lambda action: self._execute_action(btn.ship_id, action),
        )
        menu.open()

    def _execute_action(self, ship_id, action):
        """Delegate to galaxy map's action handler."""
        from kivy.app import App
        app = App.get_running_app()
        if app and hasattr(app, "galaxy_map_screen"):
            app.galaxy_map_screen._execute_action(ship_id, action)
            self._update_list()

    def _go_back(self, *args):
        from kivy.app import App
        app = App.get_running_app()
        if app:
            app.switch_screen("galaxy_map")
