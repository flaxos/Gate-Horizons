"""Logistics management screen for Gate Horizons.

Provides UI for:
- Viewing and managing freighter routes (source, destination, ship)
- Viewing route status, ETA, and cargo manifest
- Creating new routes with waypoints and cargo rules
- Assigning ships to routes
"""

from kivy.uix.screenmanager import Screen
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.button import Button
from kivy.uix.label import Label
from kivy.uix.scrollview import ScrollView
from kivy.graphics import Color, Rectangle
from kivy.metrics import dp

from ..widgets.resource_bar import TopBar


class LogisticsScreen(Screen):
    """Freighter route management screen.

    Left panel: route list
    Right panel: route details, ship status, cargo manifest
    """

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.name = "logistics_screen"
        self.game_state = None
        self.selected_route_id = None
        self._build_ui()

    def _build_ui(self):
        outer = BoxLayout(orientation="vertical")

        with outer.canvas.before:
            Color(0.02, 0.03, 0.08, 1)
            self._bg = Rectangle(pos=outer.pos, size=outer.size)
        outer.bind(
            size=lambda w, v: setattr(self._bg, "size", v),
            pos=lambda w, v: setattr(self._bg, "pos", v),
        )

        self.top_bar = TopBar()
        outer.add_widget(self.top_bar)

        root = BoxLayout(orientation="horizontal")

        # --- Left: route list ---
        left = BoxLayout(orientation="vertical", size_hint_x=0.3, padding=dp(8), spacing=dp(4))
        left.add_widget(Label(
            text="Freight Routes", font_size="16sp", bold=True,
            color=(0.3, 0.85, 1, 1), size_hint_y=None, height=dp(36),
        ))
        self.route_list = BoxLayout(
            orientation="vertical", spacing=dp(4), size_hint_y=None,
        )
        self.route_list.bind(minimum_height=self.route_list.setter("height"))
        scroll = ScrollView(size_hint=(1, 1))
        scroll.add_widget(self.route_list)
        left.add_widget(scroll)

        # New route button
        new_route_btn = Button(
            text="+ New Route", size_hint_y=None, height=dp(36),
            font_size="12sp", background_color=(0.1, 0.3, 0.15, 0.9),
            color=(0.7, 1, 0.7, 1),
        )
        new_route_btn.bind(on_release=self._new_route)
        left.add_widget(new_route_btn)

        back_btn = Button(
            text="< Back to Map", size_hint_y=None, height=dp(36),
            font_size="12sp", background_color=(0.08, 0.15, 0.25, 0.8),
            color=(0.7, 0.85, 1, 1),
        )
        back_btn.bind(on_release=self._go_back)
        left.add_widget(back_btn)
        root.add_widget(left)

        # --- Right: route details ---
        right = BoxLayout(orientation="vertical", size_hint_x=0.7, padding=dp(8), spacing=dp(8))
        right.add_widget(Label(
            text="Route Details", font_size="16sp", bold=True,
            color=(1, 0.8, 0.3, 1), size_hint_y=None, height=dp(36),
        ))

        self.route_detail_label = Label(
            text="Select a route to view details",
            font_size="12sp", color=(0.8, 0.8, 0.8, 1),
            halign="left", valign="top",
            size_hint_y=None, height=dp(300),
        )
        self.route_detail_label.bind(size=self.route_detail_label.setter("text_size"))

        self.ship_status_label = Label(
            text="", font_size="12sp", color=(0.7, 0.9, 0.7, 1),
            halign="left", valign="top",
            size_hint_y=None, height=dp(150),
        )
        self.ship_status_label.bind(size=self.ship_status_label.setter("text_size"))

        details_scroll = ScrollView(size_hint=(1, 1))
        details_box = BoxLayout(orientation="vertical", size_hint_y=None, spacing=dp(4))
        details_box.bind(minimum_height=details_box.setter("height"))
        details_box.add_widget(self.route_detail_label)
        details_box.add_widget(self.ship_status_label)

        # Cancel route button
        cancel_btn = Button(
            text="Cancel Route", size_hint_y=None, height=dp(36),
            font_size="12sp", background_color=(0.35, 0.1, 0.1, 0.9),
            color=(1, 0.6, 0.6, 1),
        )
        cancel_btn.bind(on_release=self._cancel_route)
        details_box.add_widget(cancel_btn)

        details_scroll.add_widget(details_box)
        right.add_widget(details_scroll)

        root.add_widget(right)
        outer.add_widget(root)
        self.add_widget(outer)

    def on_enter(self, *args):
        self.refresh()

    def set_game_state(self, game_state):
        self.game_state = game_state

    def refresh(self):
        if not self.game_state:
            return
        self.top_bar.update(self.game_state)
        self._refresh_route_list()
        self._refresh_details()

    def _refresh_route_list(self):
        self.route_list.clear_widgets()
        if not self.game_state:
            return
        for route_id, route in self.game_state.logistics.routes.items():
            waypoint_names = " -> ".join(w.system_id for w in route.waypoints)
            status = "Active" if route.active else "Paused"
            btn = Button(
                text=f"{route.name}\n{waypoint_names}\n[{status}]",
                font_size="10sp", size_hint_y=None, height=dp(56),
                background_color=(0.1, 0.2, 0.35, 0.9),
                color=(0.8, 0.9, 1, 1),
            )
            btn.route_id = route_id
            btn.bind(on_release=self._select_route)
            self.route_list.add_widget(btn)

        if not self.game_state.logistics.routes:
            self.route_list.add_widget(Label(
                text="No routes defined", font_size="11sp",
                color=(0.5, 0.5, 0.5, 1), size_hint_y=None, height=dp(30),
            ))

    def _select_route(self, instance):
        self.selected_route_id = instance.route_id
        self._refresh_details()

    def _refresh_details(self):
        if not self.game_state or not self.selected_route_id:
            return
        route = self.game_state.logistics.routes.get(self.selected_route_id)
        if not route:
            self.route_detail_label.text = "Route not found"
            return

        text = f"[b]Route: {route.name}[/b]\n\n"
        text += f"Status: {'Active' if route.active else 'Paused'}\n"
        text += f"Current waypoint: {route.current_waypoint_index}\n\n"
        text += "[b]Waypoints:[/b]\n"
        for i, wp in enumerate(route.waypoints):
            marker = " <<<" if i == route.current_waypoint_index else ""
            text += f"  {i+1}. {wp.system_id}{marker}\n"
            for rule in wp.cargo_rules:
                text += f"     {rule.action} {rule.resource_id}"
                if rule.amount > 0:
                    text += f" (max {rule.amount})"
                text += "\n"
        self.route_detail_label.text = text

        # Ship status
        ship_text = ""
        if route.assigned_ship_id:
            ship = self.game_state.fleet.ships.get(route.assigned_ship_id)
            if ship:
                ship_text = f"[b]Assigned Ship: {ship.name}[/b]\n"
                ship_text += f"Location: {ship.location}\n"
                ship_text += f"Destination: {ship.destination or '(none)'}\n"
                ship_text += f"Cargo: {ship.cargo_used}/{ship.stats.cargo_capacity}\n"
                if ship.cargo:
                    for res, amt in ship.cargo.items():
                        if amt > 0:
                            ship_text += f"  {res}: {amt}\n"
            else:
                ship_text = "Assigned ship not found"
        else:
            ship_text = "No ship assigned to this route"
        self.ship_status_label.text = ship_text

    def _new_route(self, instance):
        """Navigate to trade screen for route creation (logistics uses trade routes)."""
        from kivy.app import App
        app = App.get_running_app()
        if app:
            app.switch_screen("trade_screen")

    def _cancel_route(self, instance):
        if not self.game_state or not self.selected_route_id:
            return
        self.game_state.logistics.cancel_route(self.selected_route_id)
        self.selected_route_id = None
        self.refresh()

    def _go_back(self, instance):
        self.manager.current = "galaxy_map"
