"""Fleet management screen for Gate Horizons."""

import math

from kivy.uix.screenmanager import Screen
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.button import Button
from kivy.uix.gridlayout import GridLayout
from kivy.uix.label import Label
from kivy.uix.widget import Widget
from kivy.uix.scrollview import ScrollView
from kivy.uix.progressbar import ProgressBar
from kivy.uix.popup import Popup
from kivy.graphics import Color, Rectangle
from kivy.metrics import dp

from ..widgets.resource_bar import TopBar
from ..widgets.context_menu import ContextMenu, DestinationMenu
from gate_horizons.game.feature_flags import fleet_groups_enabled


class FleetScreen(Screen):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.name = "fleet_screen"
        self.game_state = None
        self._build_ui()

    def fleet_group_actions_available(self) -> bool:
        from kivy.app import App

        app = App.get_running_app()
        settings = getattr(app, "settings", None) if app else None
        return fleet_groups_enabled(settings)

    def fleet_group_actions(self) -> list[str]:
        if not self.fleet_group_actions_available():
            return []
        return ["create_fleet_group", "dispatch_group_order"]

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
        self.top_bar.update(game_state)
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
        freighter_classes = {"freighter", "small_freighter", "medium_freighter", "large_freighter"}

        for ship in sorted(
            self.game_state.fleet.ships.values(),
            key=lambda s: s.ship_class,
        ):
            card = BoxLayout(
                orientation="horizontal",
                size_hint_y=None,
                height=dp(64),
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
            ship_class = ship.ship_class or ""
            color = class_colors.get(ship_class)
            if not color and (ship_class in freighter_classes or "freighter" in ship_class):
                color = class_colors["freighter"]
            color = color or (0.5, 0.5, 0.5, 0.9)
            with indicator.canvas:
                Color(*color)
                ind_rect = Rectangle(pos=indicator.pos, size=indicator.size)
            indicator.bind(
                size=lambda w, v, r=ind_rect: setattr(r, 'size', v),
                pos=lambda w, v, r=ind_rect: setattr(r, 'pos', v),
            )
            card.add_widget(indicator)

            # Ship info
            info = BoxLayout(orientation="vertical", size_hint_x=0.3)
            info.add_widget(Label(
                text=ship.name,
                font_size="13sp",
                bold=True,
                color=(0.85, 0.95, 1, 1),
                halign="left",
                text_size=(None, None),
            ))

            mission = ship.mission or "Idle"
            if ship.mining:
                mission = "Mining"
            system = self.game_state.galaxy.systems.get(ship.location)
            loc_name = system.name if system else ship.location
            info.add_widget(Label(
                text=f"{ship.ship_class.title()} @ {loc_name} | {mission}",
                font_size="10sp",
                color=(0.5, 0.7, 0.9, 0.8),
                halign="left",
                text_size=(None, None),
            ))
            travel_status = None
            if ship.path or ship.destination:
                path = ship.path or []
                destination_id = ship.destination or (path[-1] if path else None)
                if destination_id:
                    dest_system = self.game_state.galaxy.systems.get(destination_id)
                    dest_name = dest_system.name if dest_system else destination_id
                    speed = ship.stats.speed or 1
                    eta_turns = math.ceil(len(path) / speed) if path else 0
                    travel_status = (
                        f"🟡 In Transit • Destination: {dest_name} • ETA: {eta_turns} turns"
                    )
            if travel_status:
                info.add_widget(Label(
                    text=travel_status,
                    font_size="9sp",
                    color=(1, 0.85, 0.4, 0.9),
                    halign="left",
                    text_size=(None, None),
                ))
            card.add_widget(info)

            # Hull bar
            hull_box = BoxLayout(orientation="vertical", size_hint_x=0.15)
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
                size_hint_x=0.15,
                halign="left",
                text_size=(None, None),
            ))

            # Quick action buttons
            quick_actions = BoxLayout(orientation="vertical", size_hint_x=0.25, spacing=dp(2))

            # Top row: class-specific quick action
            top_row = BoxLayout(orientation="horizontal", spacing=dp(2))

            if ship.ship_class == "miner":
                mine_text = "Stop Mining" if ship.mining else "Mine"
                mine_btn = Button(
                    text=mine_text,
                    font_size="10sp",
                    background_color=(0.5, 0.3, 0.1, 0.9) if ship.mining else (0.15, 0.35, 0.2, 0.9),
                    color=(1, 0.8, 0.5, 1) if ship.mining else (0.3, 1, 0.5, 1),
                )
                mine_btn.ship_id = ship.id
                mine_btn.bind(on_release=self._toggle_mining)
                top_row.add_widget(mine_btn)

                if ship.cargo_used > 0:
                    deliver_btn = Button(
                        text="Deliver",
                        font_size="10sp",
                        background_color=(0.2, 0.3, 0.5, 0.9),
                        color=(0.7, 0.85, 1, 1),
                    )
                    deliver_btn.ship_id = ship.id
                    deliver_btn.bind(on_release=self._deliver_cargo)
                    top_row.add_widget(deliver_btn)

            elif ship.ship_class in {"freighter", "small_freighter", "medium_freighter", "large_freighter"} or "freighter" in (ship.ship_class or ""):
                if ship.trade_route:
                    route_btn = Button(
                        text="Unassign",
                        font_size="10sp",
                        background_color=(0.4, 0.2, 0.1, 0.9),
                        color=(1, 0.6, 0.4, 1),
                    )
                    route_btn.ship_id = ship.id
                    route_btn.bind(on_release=self._unassign_trade)
                    top_row.add_widget(route_btn)
                if ship.cargo_used > 0:
                    unload_btn = Button(
                        text="Unload",
                        font_size="10sp",
                        background_color=(0.2, 0.3, 0.5, 0.9),
                        color=(0.7, 0.85, 1, 1),
                    )
                    unload_btn.ship_id = ship.id
                    unload_btn.bind(on_release=self._unload_cargo)
                    top_row.add_widget(unload_btn)

            # Move button (universal)
            move_btn = Button(
                text="Move",
                font_size="10sp",
                background_color=(0.12, 0.25, 0.4, 0.8),
                color=(0.85, 0.95, 1, 1),
            )
            move_btn.ship_id = ship.id
            move_btn.bind(on_release=self._on_move)
            top_row.add_widget(move_btn)

            quick_actions.add_widget(top_row)

            # Bottom row: Actions menu
            action_btn = Button(
                text="All Actions...",
                font_size="10sp",
                background_color=(0.12, 0.25, 0.4, 0.8),
                color=(0.85, 0.95, 1, 1),
            )
            action_btn.ship_id = ship.id
            action_btn.bind(on_release=self._show_actions)
            quick_actions.add_widget(action_btn)

            card.add_widget(quick_actions)

            self.ship_list.add_widget(card)

        total_maint = self.game_state.fleet.get_total_maintenance()
        self.maint_label.text = f"Total Maintenance: {total_maint} credits/turn | Ships: {len(self.game_state.fleet.ships)}"

    def _toggle_mining(self, btn):
        if not self.game_state:
            return
        success, message, _ = self.game_state.toggle_ship_mining(btn.ship_id)
        if not success:
            self._show_notice(message)
        self.top_bar.update(self.game_state)
        self._update_list()

    def _deliver_cargo(self, btn):
        """Deliver mined cargo to colony stockpiles."""
        if not self.game_state:
            return
        self.game_state.unload_ship_cargo_to_colony(btn.ship_id)
        self.top_bar.update(self.game_state)
        self._update_list()

    def _unload_cargo(self, btn):
        """Unload freighter cargo to colony stockpiles."""
        if not self.game_state:
            return
        self.game_state.unload_ship_cargo_to_colony(btn.ship_id)
        self.top_bar.update(self.game_state)
        self._update_list()

    def _unassign_trade(self, btn):
        """Unassign ship from trade route."""
        if not self.game_state:
            return
        success, message = self.game_state.unassign_ship_from_trade_routes(btn.ship_id)
        if not success:
            self._show_notice(message)
        self.top_bar.update(self.game_state)
        self._update_list()

    def _on_move(self, btn):
        """Show destination menu for ship."""
        if not self.game_state:
            return
        ship = self.game_state.fleet.ships.get(btn.ship_id)
        if not ship:
            return

        reachable = []
        for sid, system in self.game_state.galaxy.systems.items():
            if sid == ship.location:
                continue
            if system.discovered and system.gate_active:
                path = self.game_state.galaxy.get_path(ship.location, sid)
                if path:
                    reachable.append(system)

        menu = DestinationMenu(
            systems=reachable,
            callback=lambda dest_id, sid=btn.ship_id: self._move_ship(sid, dest_id),
        )
        menu.open()

    def _move_ship(self, ship_id, dest_id):
        if not self.game_state:
            return
        success, message, _ = self.game_state.submit_strategic_movement(ship_id, dest_id)
        self._show_notice(message)
        if not success:
            self.top_bar.update(self.game_state)
            self._update_list()
            return
        self._update_list()

    def _show_actions(self, btn):
        if not self.game_state:
            return

        actions = self.game_state.fleet.get_contextual_actions(
            btn.ship_id,
            galaxy=self.game_state.galaxy,
            colonies=self.game_state.colonies,
            game_state=self.game_state,
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
        """Execute ship action through shared game-state dispatcher."""
        if not self.game_state:
            return
        result = self.game_state.dispatch_ship_context_action(
            ship_id,
            action.name,
            params={"credits": action.cost.get("credits", 5)} if action.name == "Deploy Probe" else None,
        )
        required_ui = result.get("requires_ui")
        if required_ui == "destination":
            btn = type("_ShipBtn", (), {"ship_id": ship_id})()
            self._on_move(btn)
        elif required_ui == "escort_target":
            self._show_escort_target_menu(ship_id)

        if not result.get("success"):
            self._show_notice(result.get("message", "Action failed."))
        self.top_bar.update(self.game_state)
        self._update_list()

    def _show_escort_target_menu(self, ship_id):
        """Show a popup menu for selecting an escort target."""
        ship = self.game_state.fleet.ships.get(ship_id)
        if not ship:
            return

        escort_targets = [
            escort_ship
            for escort_ship in self.game_state.fleet.get_ships_at(ship.location)
            if escort_ship.id != ship_id
        ]
        if not escort_targets:
            self._show_notice("No escort targets available in this system.")
            return

        escort_targets.sort(key=lambda escort_ship: escort_ship.name)

        content = BoxLayout(
            orientation="vertical",
            spacing=dp(8),
            padding=dp(10),
        )
        content.add_widget(
            Label(
                text="Select a target ship to escort:",
                size_hint_y=None,
                height=dp(24),
                color=(0.8, 0.9, 1, 1),
                font_size="12sp",
            )
        )

        scroll = ScrollView(size_hint=(1, 1))
        target_list = GridLayout(
            cols=1,
            spacing=dp(6),
            size_hint_y=None,
        )
        target_list.bind(minimum_height=target_list.setter("height"))

        popup = Popup(
            title="Escort Target",
            content=content,
            size_hint=(0.45, 0.5),
            title_color=(0.3, 0.85, 1, 1),
            separator_color=(0.15, 0.6, 0.8, 0.6),
            background_color=(0.04, 0.06, 0.12, 0.95),
        )

        for target in escort_targets:
            target_btn = Button(
                text=target.name,
                size_hint_y=None,
                height=dp(36),
                font_size="12sp",
                background_color=(0.15, 0.2, 0.35, 0.9),
                color=(0.85, 0.92, 1, 1),
            )
            target_btn.bind(
                on_release=lambda btn, target_id=target.id: self._issue_escort_order(
                    ship_id,
                    target_id,
                    popup,
                )
            )
            target_list.add_widget(target_btn)

        scroll.add_widget(target_list)
        content.add_widget(scroll)

        cancel_btn = Button(
            text="Cancel",
            size_hint_y=None,
            height=dp(36),
            font_size="12sp",
            background_color=(0.2, 0.2, 0.25, 0.9),
            color=(0.8, 0.9, 1, 1),
        )
        cancel_btn.bind(on_release=lambda btn: popup.dismiss())
        content.add_widget(cancel_btn)
        popup.open()

    def _issue_escort_order(self, ship_id, target_id, popup):
        popup.dismiss()
        success, message, _ = self.game_state.issue_ship_order(
            ship_id,
            "Escort",
            params={"target_ship_id": target_id},
        )
        if not success:
            self._show_notice(message)
        self.top_bar.update(self.game_state)
        self._update_list()

    def _show_notice(self, message: str, title: str = "Notice") -> None:
        content = BoxLayout(orientation="vertical", spacing=dp(8), padding=dp(12))
        content.add_widget(Label(
            text=message,
            font_size="12sp",
            color=(0.7, 0.85, 1, 0.9),
            size_hint_y=None,
            height=dp(56),
            halign="center",
            valign="middle",
        ))
        ok_btn = Button(
            text="OK",
            size_hint_y=None,
            height=dp(36),
            font_size="12sp",
            background_color=(0.15, 0.2, 0.35, 0.9),
            color=(0.8, 0.9, 1, 1),
        )
        popup = Popup(
            title=title,
            content=content,
            size_hint=(0.4, 0.35),
            title_color=(0.3, 0.85, 1, 1),
            separator_color=(0.15, 0.6, 0.8, 0.6),
            background_color=(0.04, 0.06, 0.12, 0.95),
        )
        ok_btn.bind(on_release=lambda x: popup.dismiss())
        content.add_widget(ok_btn)
        popup.open()

    def _go_back(self, *args):
        from kivy.app import App
        app = App.get_running_app()
        if app:
            app.switch_screen("galaxy_map")
