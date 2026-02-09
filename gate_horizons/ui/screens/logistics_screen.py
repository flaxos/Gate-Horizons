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
from kivy.uix.gridlayout import GridLayout
from kivy.uix.label import Label
from kivy.uix.popup import Popup
from kivy.uix.scrollview import ScrollView
from kivy.uix.textinput import TextInput
from kivy.uix.widget import Widget
from kivy.graphics import Color, Rectangle
from kivy.metrics import dp

from ..widgets.resource_bar import TopBar


class CreateFreightRoutePopup(Popup):
    """Popup for creating a freighter logistics route."""

    def __init__(self, game_state=None, on_create=None, **kwargs):
        self.game_state = game_state
        self.create_callback = on_create
        self.selected_source = None
        self.selected_dest = None
        self.selected_ship_id = None
        self.selected_resource = None

        content = BoxLayout(orientation="vertical", spacing=dp(6), padding=dp(10))

        content.add_widget(Label(
            text="Route Name:",
            font_size="12sp",
            bold=True,
            color=(0.6, 0.8, 1, 1),
            size_hint_y=None,
            height=dp(20),
        ))
        self.name_input = TextInput(
            text="",
            font_size="11sp",
            multiline=False,
            size_hint_y=None,
            height=dp(30),
            background_color=(0.1, 0.12, 0.18, 0.9),
            foreground_color=(0.8, 0.9, 1, 1),
        )
        content.add_widget(self.name_input)

        content.add_widget(Label(
            text="Source System:",
            font_size="12sp",
            bold=True,
            color=(0.6, 0.8, 1, 1),
            size_hint_y=None,
            height=dp(20),
        ))
        self.source_layout = BoxLayout(
            orientation="horizontal",
            size_hint_y=None,
            height=dp(32),
            spacing=dp(4),
        )
        self._populate_colony_buttons(self.source_layout, "source")
        content.add_widget(self.source_layout)

        content.add_widget(Label(
            text="Destination System:",
            font_size="12sp",
            bold=True,
            color=(0.6, 0.8, 1, 1),
            size_hint_y=None,
            height=dp(20),
        ))
        self.dest_layout = BoxLayout(
            orientation="horizontal",
            size_hint_y=None,
            height=dp(32),
            spacing=dp(4),
        )
        self._populate_colony_buttons(self.dest_layout, "dest")
        content.add_widget(self.dest_layout)

        content.add_widget(Label(
            text="Resource to Transfer:",
            font_size="12sp",
            bold=True,
            color=(0.6, 0.8, 1, 1),
            size_hint_y=None,
            height=dp(20),
        ))
        self.resource_grid = GridLayout(cols=2, spacing=dp(4), size_hint_y=None)
        self.resource_grid.bind(minimum_height=self.resource_grid.setter("height"))
        resource_scroll = ScrollView(size_hint=(1, None), height=dp(140))
        resource_scroll.add_widget(self.resource_grid)
        content.add_widget(resource_scroll)
        self._populate_resource_buttons()

        content.add_widget(Label(
            text="Amount per stop (0 = as much as possible):",
            font_size="11sp",
            color=(0.6, 0.75, 0.9, 0.9),
            size_hint_y=None,
            height=dp(18),
        ))
        self.amount_input = TextInput(
            text="0",
            font_size="11sp",
            multiline=False,
            input_filter="int",
            size_hint_y=None,
            height=dp(28),
            background_color=(0.1, 0.12, 0.18, 0.9),
            foreground_color=(0.8, 0.9, 1, 1),
        )
        content.add_widget(self.amount_input)

        content.add_widget(Label(
            text="Assign Freighter:",
            font_size="12sp",
            bold=True,
            color=(0.6, 0.8, 1, 1),
            size_hint_y=None,
            height=dp(20),
        ))
        self.ship_layout = BoxLayout(orientation="vertical", spacing=dp(2), size_hint_y=None)
        self.ship_layout.bind(minimum_height=self.ship_layout.setter("height"))
        ship_scroll = ScrollView(size_hint=(1, None), height=dp(90))
        ship_scroll.add_widget(self.ship_layout)
        content.add_widget(ship_scroll)
        self._populate_freighters()

        self.status_label = Label(
            text="Select source, destination, resource, and freighter",
            font_size="11sp",
            color=(0.5, 0.7, 0.9, 0.8),
            size_hint_y=None,
            height=dp(20),
        )
        content.add_widget(self.status_label)

        btn_row = BoxLayout(orientation="horizontal", size_hint_y=None, height=dp(40), spacing=dp(8))
        create_btn = Button(
            text="Create Route",
            font_size="13sp",
            background_color=(0.15, 0.4, 0.2, 0.9),
            color=(0.3, 1, 0.5, 1),
        )
        create_btn.bind(on_release=self._on_create)
        btn_row.add_widget(create_btn)

        cancel_btn = Button(
            text="Cancel",
            font_size="13sp",
            background_color=(0.3, 0.1, 0.1, 0.8),
            color=(1, 0.7, 0.7, 1),
        )
        cancel_btn.bind(on_release=lambda x: self.dismiss())
        btn_row.add_widget(cancel_btn)
        content.add_widget(btn_row)

        super().__init__(
            title="Create Freight Route",
            content=content,
            size_hint=(0.7, 0.85),
            title_color=(0.3, 0.85, 1, 1),
            separator_color=(0.15, 0.6, 0.8, 0.6),
            background_color=(0.04, 0.06, 0.12, 0.95),
            **kwargs,
        )

    def _populate_colony_buttons(self, layout, target):
        layout.clear_widgets()
        if not self.game_state:
            return
        for sid, colony in self.game_state.colonies.colonies.items():
            system = self.game_state.galaxy.systems.get(sid)
            label = system.name if system else colony.name
            btn = Button(
                text=label,
                size_hint_x=None,
                width=dp(120),
                font_size="10sp",
                background_color=(0.12, 0.25, 0.4, 0.8),
                color=(0.85, 0.95, 1, 1),
            )
            btn.system_id = sid
            btn.target = target
            btn.bind(on_release=self._on_select_system)
            layout.add_widget(btn)

    def _resource_options(self):
        options = []
        if not self.game_state:
            return options
        definitions = self.game_state.production.config.resource_definitions
        for resource_id, data in definitions.items():
            options.append((resource_id, data.get("name", resource_id.replace("_", " ").title())))
        for resource_id in self.game_state.resources.global_resources.keys():
            if resource_id not in definitions:
                options.append((resource_id, resource_id.replace("_", " ").title()))
        options.append(("pop", "POP (Population)"))
        return sorted(options, key=lambda item: item[1])

    def _populate_resource_buttons(self):
        self.resource_grid.clear_widgets()
        for resource_id, label in self._resource_options():
            btn = Button(
                text=label,
                size_hint_y=None,
                height=dp(32),
                font_size="10sp",
                background_color=(0.12, 0.25, 0.4, 0.8),
                color=(0.85, 0.95, 1, 1),
            )
            btn.resource_id = resource_id
            btn.bind(on_release=self._on_select_resource)
            self.resource_grid.add_widget(btn)

        if not self.resource_grid.children:
            self.resource_grid.add_widget(Label(
                text="No resources available",
                font_size="11sp",
                color=(0.5, 0.5, 0.5, 1),
                size_hint_y=None,
                height=dp(24),
            ))

    def _populate_freighters(self):
        self.ship_layout.clear_widgets()
        if not self.game_state:
            return
        for ship in self.game_state.fleet.ships.values():
            if ship.ship_class != "freighter":
                continue
            if ship.trade_route or self.game_state.logistics.get_route_for_ship(ship.id):
                continue
            btn = Button(
                text=f"{ship.name} @ {ship.location} (cargo: {ship.stats.cargo_capacity})",
                size_hint_y=None,
                height=dp(30),
                font_size="10sp",
                background_color=(0.12, 0.25, 0.4, 0.8),
                color=(0.85, 0.95, 1, 1),
            )
            btn.ship_id = ship.id
            btn.bind(on_release=self._on_select_ship)
            self.ship_layout.add_widget(btn)

        if not self.ship_layout.children:
            self.ship_layout.add_widget(Label(
                text="No available freighters",
                font_size="11sp",
                color=(0.5, 0.5, 0.5, 1),
                size_hint_y=None,
                height=dp(24),
            ))

    def _on_select_system(self, btn):
        if btn.target == "source":
            self.selected_source = btn.system_id
            for child in self.source_layout.children:
                if hasattr(child, "system_id"):
                    child.background_color = (
                        (0.2, 0.4, 0.6, 0.9)
                        if child.system_id == self.selected_source
                        else (0.12, 0.25, 0.4, 0.8)
                    )
        else:
            self.selected_dest = btn.system_id
            for child in self.dest_layout.children:
                if hasattr(child, "system_id"):
                    child.background_color = (
                        (0.2, 0.4, 0.6, 0.9)
                        if child.system_id == self.selected_dest
                        else (0.12, 0.25, 0.4, 0.8)
                    )
        self._update_status()

    def _on_select_resource(self, btn):
        self.selected_resource = btn.resource_id
        for child in self.resource_grid.children:
            if hasattr(child, "resource_id"):
                child.background_color = (
                    (0.2, 0.4, 0.6, 0.9)
                    if child.resource_id == self.selected_resource
                    else (0.12, 0.25, 0.4, 0.8)
                )
        self._update_status()

    def _on_select_ship(self, btn):
        self.selected_ship_id = btn.ship_id
        for child in self.ship_layout.children:
            if hasattr(child, "ship_id"):
                child.background_color = (
                    (0.2, 0.4, 0.6, 0.9)
                    if child.ship_id == self.selected_ship_id
                    else (0.12, 0.25, 0.4, 0.8)
                )
        self._update_status()

    def _update_status(self):
        parts = []
        if not self.selected_source:
            parts.append("Select source")
        if not self.selected_dest:
            parts.append("Select destination")
        if self.selected_source and self.selected_dest and self.selected_source == self.selected_dest:
            parts.append("Source and destination must differ")
        if not self.selected_resource:
            parts.append("Select resource")
        if not self.selected_ship_id:
            parts.append("Assign freighter")

        self.status_label.text = ", ".join(parts) if parts else "Ready to create route"
        self.status_label.color = (1, 0.5, 0.3, 0.9) if parts else (0.3, 1, 0.5, 0.9)

    def _on_create(self, *args):
        if not self.game_state:
            return
        if not self.selected_source or not self.selected_dest:
            return
        if self.selected_source == self.selected_dest:
            return
        if not self.selected_resource or not self.selected_ship_id:
            return

        try:
            amount = int(self.amount_input.text)
        except ValueError:
            amount = 0

        route_name = self.name_input.text.strip() or None
        success, message = self.game_state.create_freighter_route(
            source_system_id=self.selected_source,
            dest_system_id=self.selected_dest,
            ship_id=self.selected_ship_id,
            resource_id=self.selected_resource,
            amount=amount,
            name=route_name,
        )

        if success:
            self.dismiss()
            if self.create_callback:
                self.create_callback()
        else:
            self.status_label.text = message
            self.status_label.color = (1, 0.3, 0.2, 1)


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
            markup=True,
            halign="left", valign="top",
            size_hint_y=None, height=dp(300),
        )
        self.route_detail_label.bind(size=self.route_detail_label.setter("text_size"))

        self.ship_status_label = Label(
            text="", font_size="12sp", color=(0.7, 0.9, 0.7, 1),
            markup=True,
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
        if not self.game_state:
            return
        popup = CreateFreightRoutePopup(
            game_state=self.game_state,
            on_create=self.refresh,
        )
        popup.open()

    def _cancel_route(self, instance):
        if not self.game_state or not self.selected_route_id:
            return
        self.game_state.logistics.cancel_route(self.selected_route_id)
        self.selected_route_id = None
        self.refresh()

    def _go_back(self, instance):
        self.manager.current = "galaxy_map"
