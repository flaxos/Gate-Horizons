"""Trade route management screen for Gate Horizons."""

from kivy.uix.screenmanager import Screen
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.gridlayout import GridLayout
from kivy.uix.button import Button
from kivy.uix.label import Label
from kivy.uix.widget import Widget
from kivy.uix.scrollview import ScrollView
from kivy.uix.popup import Popup
from kivy.uix.textinput import TextInput
from kivy.graphics import Color, Rectangle
from kivy.metrics import dp

from ..widgets.resource_bar import TopBar


class CreateRoutePopup(Popup):
    """Popup for creating a new trade route."""

    def __init__(self, game_state=None, on_create=None, **kwargs):
        self.game_state = game_state
        self.create_callback = on_create
        self.selected_source = None
        self.selected_dest = None
        self.selected_ships = []
        self.manifest = {"outbound": {}, "inbound": {}}

        content = BoxLayout(orientation="vertical", spacing=dp(6), padding=dp(10))

        # Step 1: Source system
        content.add_widget(Label(
            text="Source System:",
            font_size="13sp",
            bold=True,
            color=(0.6, 0.8, 1, 1),
            size_hint_y=None,
            height=dp(24),
            halign="left",
            text_size=(dp(400), None),
        ))

        self.source_layout = BoxLayout(
            orientation="horizontal",
            size_hint_y=None,
            height=dp(36),
            spacing=dp(4),
        )
        self._populate_system_buttons(self.source_layout, "source")
        content.add_widget(self.source_layout)

        # Step 2: Destination system
        content.add_widget(Label(
            text="Destination System:",
            font_size="13sp",
            bold=True,
            color=(0.6, 0.8, 1, 1),
            size_hint_y=None,
            height=dp(24),
            halign="left",
            text_size=(dp(400), None),
        ))

        self.dest_layout = BoxLayout(
            orientation="horizontal",
            size_hint_y=None,
            height=dp(36),
            spacing=dp(4),
        )
        self._populate_system_buttons(self.dest_layout, "dest")
        content.add_widget(self.dest_layout)

        # Step 3: Resource manifest
        content.add_widget(Label(
            text="Outbound Resources (per turn):",
            font_size="12sp",
            bold=True,
            color=(0.6, 0.8, 1, 1),
            size_hint_y=None,
            height=dp(22),
            halign="left",
            text_size=(dp(400), None),
        ))

        self.manifest_inputs = {}
        manifest_grid = GridLayout(cols=2, size_hint_y=None, height=dp(80), spacing=dp(4))
        for res in ["energy", "metals", "exotics", "credits"]:
            manifest_grid.add_widget(Label(
                text=f"{res.title()}:",
                font_size="11sp",
                color=(0.7, 0.8, 0.9, 0.9),
                size_hint_x=0.4,
            ))
            inp = TextInput(
                text="0",
                font_size="11sp",
                input_filter="int",
                multiline=False,
                size_hint_x=0.6,
                background_color=(0.1, 0.12, 0.18, 0.9),
                foreground_color=(0.8, 0.9, 1, 1),
            )
            self.manifest_inputs[res] = inp
            manifest_grid.add_widget(inp)
        content.add_widget(manifest_grid)

        # Step 4: Available freighters
        content.add_widget(Label(
            text="Assign Freighters:",
            font_size="12sp",
            bold=True,
            color=(0.6, 0.8, 1, 1),
            size_hint_y=None,
            height=dp(22),
            halign="left",
            text_size=(dp(400), None),
        ))

        self.ship_layout = BoxLayout(
            orientation="vertical",
            spacing=dp(2),
            size_hint_y=None,
        )
        self.ship_layout.bind(minimum_height=self.ship_layout.setter("height"))
        self._populate_freighters()

        ship_scroll = ScrollView(size_hint=(1, None), height=dp(80))
        ship_scroll.add_widget(self.ship_layout)
        content.add_widget(ship_scroll)

        # Status label
        self.status_label = Label(
            text="Select source, destination, and assign freighters",
            font_size="11sp",
            color=(0.5, 0.7, 0.9, 0.8),
            size_hint_y=None,
            height=dp(20),
        )
        content.add_widget(self.status_label)

        # Buttons
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
            title="Create Trade Route",
            content=content,
            size_hint=(0.6, 0.8),
            title_color=(0.3, 0.85, 1, 1),
            separator_color=(0.15, 0.6, 0.8, 0.6),
            background_color=(0.04, 0.06, 0.12, 0.95),
            **kwargs,
        )

    def _populate_system_buttons(self, layout, target):
        if not self.game_state:
            return
        for sid, colony in self.game_state.colonies.colonies.items():
            system = self.game_state.galaxy.systems.get(sid)
            if not system:
                continue
            btn = Button(
                text=system.name,
                size_hint_x=None,
                width=dp(100),
                font_size="10sp",
                background_color=(0.12, 0.25, 0.4, 0.8),
                color=(0.85, 0.95, 1, 1),
            )
            btn.system_id = sid
            btn.target = target
            btn.bind(on_release=self._on_select_system)
            layout.add_widget(btn)

        # Also show discovered systems without colonies
        for sid, system in self.game_state.galaxy.systems.items():
            if sid in self.game_state.colonies.colonies:
                continue
            if not system.discovered or not system.gate_active:
                continue
            btn = Button(
                text=f"{system.name}",
                size_hint_x=None,
                width=dp(100),
                font_size="10sp",
                background_color=(0.08, 0.15, 0.25, 0.6),
                color=(0.6, 0.7, 0.8, 0.8),
            )
            btn.system_id = sid
            btn.target = target
            btn.bind(on_release=self._on_select_system)
            layout.add_widget(btn)

    def _on_select_system(self, btn):
        if btn.target == "source":
            self.selected_source = btn.system_id
            for child in self.source_layout.children:
                if hasattr(child, 'system_id'):
                    child.background_color = (
                        (0.2, 0.4, 0.6, 0.9)
                        if child.system_id == self.selected_source
                        else (0.12, 0.25, 0.4, 0.8)
                    )
        else:
            self.selected_dest = btn.system_id
            for child in self.dest_layout.children:
                if hasattr(child, 'system_id'):
                    child.background_color = (
                        (0.2, 0.4, 0.6, 0.9)
                        if child.system_id == self.selected_dest
                        else (0.12, 0.25, 0.4, 0.8)
                    )
        self._update_status()

    def _populate_freighters(self):
        self.ship_layout.clear_widgets()
        if not self.game_state:
            return

        for ship in self.game_state.fleet.ships.values():
            if ship.ship_class != "freighter":
                continue
            if ship.trade_route:
                continue  # Already assigned

            btn = Button(
                text=f"{ship.name} @ {ship.location} (cargo: {ship.stats.cargo_capacity})",
                size_hint_y=None,
                height=dp(30),
                font_size="10sp",
                background_color=(0.12, 0.25, 0.4, 0.8),
                color=(0.85, 0.95, 1, 1),
            )
            btn.ship_id = ship.id
            btn.bind(on_release=self._toggle_ship)
            self.ship_layout.add_widget(btn)

    def _toggle_ship(self, btn):
        if btn.ship_id in self.selected_ships:
            self.selected_ships.remove(btn.ship_id)
            btn.background_color = (0.12, 0.25, 0.4, 0.8)
        else:
            self.selected_ships.append(btn.ship_id)
            btn.background_color = (0.2, 0.4, 0.6, 0.9)
        self._update_status()

    def _update_status(self):
        parts = []
        if not self.selected_source:
            parts.append("Select source")
        if not self.selected_dest:
            parts.append("Select destination")
        if not self.selected_ships:
            parts.append("Assign freighters")
        if self.selected_source and self.selected_dest and self.selected_source == self.selected_dest:
            parts.append("Source and destination must differ")

        self.status_label.text = ", ".join(parts) if parts else "Ready to create route"
        self.status_label.color = (1, 0.5, 0.3, 0.9) if parts else (0.3, 1, 0.5, 0.9)

    def _on_create(self, *args):
        if not self.game_state:
            return
        if not self.selected_source or not self.selected_dest:
            return
        if self.selected_source == self.selected_dest:
            return
        if not self.selected_ships:
            return

        # Build manifest from inputs
        outbound = {}
        for res, inp in self.manifest_inputs.items():
            try:
                val = int(inp.text)
                if val > 0:
                    outbound[res] = val
            except ValueError:
                pass

        manifest = {"outbound": outbound, "inbound": {}}

        route = self.game_state.trade.create_route(
            source=self.selected_source,
            dest=self.selected_dest,
            capacity_per_turn=0,
            latency_turns=0,
            ships=self.selected_ships,
            manifest=manifest,
            galaxy=self.game_state.galaxy,
            colonies=self.game_state.colonies,
        )

        if route:
            # Assign trade route to ships
            for ship_id in self.selected_ships:
                ship = self.game_state.fleet.ships.get(ship_id)
                if ship:
                    ship.trade_route = route.id
                    ship.mission = "trade"

            self.dismiss()
            if self.create_callback:
                self.create_callback()
        else:
            self.status_label.text = "No path between systems!"
            self.status_label.color = (1, 0.3, 0.2, 1)


class TradeScreen(Screen):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.name = "trade_screen"
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
            text="Trade Routes",
            font_size="16sp",
            bold=True,
            color=(0.3, 0.85, 1, 1),
            size_hint_x=0.4,
            halign="left",
            text_size=(None, None),
        ))

        create_btn = Button(
            text="+ New Route",
            size_hint_x=0.3,
            font_size="12sp",
            background_color=(0.15, 0.4, 0.2, 0.9),
            color=(0.3, 1, 0.5, 1),
        )
        create_btn.bind(on_release=self._on_create_route)
        header.add_widget(create_btn)

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

        # Route list
        scroll = ScrollView(size_hint=(1, 1))
        self.route_list = BoxLayout(
            orientation="vertical",
            spacing=dp(6),
            size_hint_y=None,
            padding=[dp(8), dp(4)],
        )
        self.route_list.bind(minimum_height=self.route_list.setter("height"))
        scroll.add_widget(self.route_list)
        root.add_widget(scroll)

        self.add_widget(root)

    def set_game_state(self, game_state):
        self.game_state = game_state
        self.top_bar.update(game_state)
        self._update_routes()

    def _update_routes(self):
        self.route_list.clear_widgets()
        if not self.game_state:
            return

        if not self.game_state.trade.routes:
            self.route_list.add_widget(Label(
                text="No trade routes established.\nCreate a route to start moving resources between systems.",
                font_size="13sp",
                color=(0.5, 0.6, 0.7, 0.7),
                size_hint_y=None,
                height=dp(60),
                halign="center",
                text_size=(dp(500), None),
            ))
            return

        for route_id, route in self.game_state.trade.routes.items():
            src = self.game_state.galaxy.systems.get(route.source_system)
            dst = self.game_state.galaxy.systems.get(route.destination_system)
            src_name = src.name if src else route.source_system
            dst_name = dst.name if dst else route.destination_system

            card = BoxLayout(
                orientation="vertical",
                size_hint_y=None,
                height=dp(120),
                padding=dp(8),
                spacing=dp(3),
            )
            with card.canvas.before:
                Color(0.06, 0.1, 0.18, 0.9)
                card_bg = Rectangle(pos=card.pos, size=card.size)
            card.bind(
                size=lambda w, v, bg=card_bg: setattr(bg, 'size', v),
                pos=lambda w, v, bg=card_bg: setattr(bg, 'pos', v),
            )

            # Route header
            status = "ACTIVE" if route.active else "PAUSED"
            status_color = (0.3, 1, 0.5, 1) if route.active else (1, 0.5, 0.3, 1)
            card.add_widget(Label(
                text=f"{src_name} -> {dst_name} [{status}]",
                font_size="13sp",
                bold=True,
                color=status_color,
                size_hint_y=None,
                height=dp(22),
                halign="left",
                text_size=(dp(500), None),
            ))

            # Efficiency and ships
            card.add_widget(Label(
                text=f"Efficiency: {route.efficiency:.0%} | Ships: {len(route.assigned_ships)}",
                font_size="11sp",
                color=(0.5, 0.7, 0.9, 0.8),
                size_hint_y=None,
                height=dp(18),
                halign="left",
                text_size=(dp(500), None),
            ))

            # Manifest
            outbound = route.resource_manifest.get("outbound", {})
            if outbound:
                ob_text = ", ".join(f"{v} {k}" for k, v in outbound.items() if v > 0)
                card.add_widget(Label(
                    text=f"Outbound: {ob_text}",
                    font_size="11sp",
                    color=(0.7, 0.85, 1, 0.9),
                    size_hint_y=None,
                    height=dp(18),
                    halign="left",
                    text_size=(dp(500), None),
                ))

            # Throughput
            throughput = route.calculate_throughput(self.game_state.fleet)
            ob_tp = throughput.get("outbound", {})
            if ob_tp:
                tp_text = ", ".join(f"{v} {k}/turn" for k, v in ob_tp.items() if v > 0)
                card.add_widget(Label(
                    text=f"Actual transfer: {tp_text}",
                    font_size="10sp",
                    color=(0.3, 1, 0.5, 0.8),
                    size_hint_y=None,
                    height=dp(16),
                    halign="left",
                    text_size=(dp(500), None),
                ))

            # Controls
            ctrl_row = BoxLayout(orientation="horizontal", size_hint_y=None, height=dp(32), spacing=dp(4))

            toggle_text = "Pause" if route.active else "Resume"
            toggle_btn = Button(
                text=toggle_text,
                font_size="11sp",
                background_color=(0.3, 0.3, 0.1, 0.8) if route.active else (0.1, 0.3, 0.2, 0.8),
                color=(1, 0.8, 0.3, 1) if route.active else (0.3, 1, 0.5, 1),
            )
            toggle_btn.route_id = route_id
            toggle_btn.bind(on_release=self._toggle_route)
            ctrl_row.add_widget(toggle_btn)

            cancel_btn = Button(
                text="Cancel Route",
                font_size="11sp",
                background_color=(0.3, 0.1, 0.1, 0.8),
                color=(1, 0.5, 0.5, 1),
            )
            cancel_btn.route_id = route_id
            cancel_btn.bind(on_release=self._cancel_route)
            ctrl_row.add_widget(cancel_btn)

            card.add_widget(ctrl_row)
            self.route_list.add_widget(card)

    def _on_create_route(self, *args):
        if not self.game_state:
            return
        popup = CreateRoutePopup(
            game_state=self.game_state,
            on_create=self._on_route_created,
        )
        popup.open()

    def _on_route_created(self):
        self.top_bar.update(self.game_state)
        self._update_routes()

    def _toggle_route(self, btn):
        if not self.game_state:
            return
        route = self.game_state.trade.routes.get(btn.route_id)
        if route:
            route.active = not route.active
            self._update_routes()

    def _cancel_route(self, btn):
        if not self.game_state:
            return
        route = self.game_state.trade.routes.get(btn.route_id)
        if route:
            # Unassign ships
            for ship_id in route.assigned_ships:
                ship = self.game_state.fleet.ships.get(ship_id)
                if ship:
                    ship.trade_route = None
                    ship.mission = None
        self.game_state.trade.cancel_route(btn.route_id)
        self._update_routes()

    def _go_back(self, *args):
        from kivy.app import App
        app = App.get_running_app()
        if app:
            app.switch_screen("galaxy_map")
