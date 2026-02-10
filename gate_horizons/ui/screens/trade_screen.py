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
        self.auto_policy = "manual"

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
        manifest_grid = GridLayout(cols=2, size_hint_y=None, height=dp(100), spacing=dp(4))
        for res in ["energy", "metals", "exotics", "credits", "pop"]:
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

        # Step 3b: Automation toggle
        content.add_widget(Label(
            text="Automation:",
            font_size="12sp",
            bold=True,
            color=(0.6, 0.8, 1, 1),
            size_hint_y=None,
            height=dp(22),
            halign="left",
            text_size=(dp(400), None),
        ))

        self.auto_toggle_btn = Button(
            text="Auto Deficit: OFF",
            font_size="11sp",
            size_hint_y=None,
            height=dp(30),
            background_color=(0.2, 0.2, 0.35, 0.9),
            color=(0.85, 0.95, 1, 1),
        )
        self.auto_toggle_btn.bind(on_release=self._toggle_auto)
        content.add_widget(self.auto_toggle_btn)

        content.add_widget(Label(
            text="Auto mode ships toward destination deficits. Resource inputs act as per-turn caps.",
            font_size="10sp",
            color=(0.5, 0.7, 0.9, 0.8),
            size_hint_y=None,
            height=dp(18),
            halign="left",
            text_size=(dp(420), None),
        ))

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

    def _toggle_auto(self, *args):
        if self.auto_policy == "manual":
            self.auto_policy = "auto_deficit"
            self.auto_toggle_btn.text = "Auto Deficit: ON"
            self.auto_toggle_btn.background_color = (0.15, 0.35, 0.2, 0.9)
            self.auto_toggle_btn.color = (0.3, 1, 0.5, 1)
        else:
            self.auto_policy = "manual"
            self.auto_toggle_btn.text = "Auto Deficit: OFF"
            self.auto_toggle_btn.background_color = (0.2, 0.2, 0.35, 0.9)
            self.auto_toggle_btn.color = (0.85, 0.95, 1, 1)

    def _populate_freighters(self):
        self.ship_layout.clear_widgets()
        if not self.game_state:
            return

        freighter_classes = {"freighter", "small_freighter", "medium_freighter", "large_freighter"}
        for ship in self.game_state.fleet.ships.values():
            ship_class = ship.ship_class or ""
            if ship_class not in freighter_classes and "freighter" not in ship_class:
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
        tech_effects = self.game_state.tech.get_effects()
        trade_routes_unlocked = tech_effects.get("unlock_trade_routes")
        if trade_routes_unlocked is None:
            tech = self.game_state.tech.techs.get("logistics_1")
            trade_routes_unlocked = bool(tech and tech.researched)
        if not trade_routes_unlocked:
            self.status_label.text = "Trade routes require Logistics I research."
            self.status_label.color = (1, 0.3, 0.2, 1)
            return
        if not self.selected_source or not self.selected_dest:
            return
        if self.selected_source not in self.game_state.colonies.colonies:
            self.status_label.text = "Source must be a colonized system."
            self.status_label.color = (1, 0.3, 0.2, 1)
            return
        if self.selected_dest not in self.game_state.colonies.colonies:
            self.status_label.text = "Destination must be a colonized system."
            self.status_label.color = (1, 0.3, 0.2, 1)
            return
        if self.selected_source == self.selected_dest:
            return
        if not self.selected_ships:
            return

        auto_allowlist = []
        auto_max_per_resource = {}
        manifest = {"outbound": {}, "inbound": {}}

        if self.auto_policy != "manual":
            for res, inp in self.manifest_inputs.items():
                try:
                    val = int(inp.text)
                except ValueError:
                    val = 0
                if val > 0:
                    auto_allowlist.append(res)
                    auto_max_per_resource[res] = val
            if not auto_allowlist:
                auto_allowlist = list(self.manifest_inputs.keys())
        else:
            outbound = {}
            invalid_fields = []
            for res, inp in self.manifest_inputs.items():
                try:
                    val = int(inp.text)
                    if val > 0:
                        outbound[res] = val
                except ValueError:
                    if inp.text.strip():
                        invalid_fields.append(res)
            if invalid_fields:
                self.status_label.text = (
                    f"Invalid number for: {', '.join(invalid_fields)}. "
                    "Use whole numbers only."
                )
                self.status_label.color = (1, 0.3, 0.2, 1)
                return
            manifest = {"outbound": outbound, "inbound": {}}

        route, message = self.game_state.create_trade_route(
            source=self.selected_source,
            dest=self.selected_dest,
            assigned_ships=self.selected_ships,
            manifest=manifest,
            auto_policy=self.auto_policy,
            auto_allowlist=auto_allowlist,
            auto_max_per_resource=auto_max_per_resource,
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
            self.status_label.text = message
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
            tech_effects = self.game_state.tech.get_effects() if self.game_state.tech else {}
            effective_capacity = route.get_effective_capacity(
                fleet=self.game_state.fleet,
                tech_effects=tech_effects,
            )
            in_transit = [
                s for s in self.game_state.trade.in_transit if s.route_id == route_id
            ]
            queue_len = len(in_transit)
            next_arrival = (
                min(s.turns_remaining for s in in_transit) if in_transit else None
            )
            cargo_summary = {}
            for shipment in in_transit:
                for res, amt in shipment.resources.items():
                    cargo_summary[res] = cargo_summary.get(res, 0) + amt

            card = BoxLayout(
                orientation="vertical",
                size_hint_y=None,
                height=dp(150),
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
            status = "ACTIVE" if route.enabled else "PAUSED"
            status_color = (0.3, 1, 0.5, 1) if route.enabled else (1, 0.5, 0.3, 1)
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

            policy_label = "Manual"
            if route.auto_policy and route.auto_policy != "manual":
                policy_label = "Auto (deficit)"
            card.add_widget(Label(
                text=f"Policy: {policy_label} | Capacity: {effective_capacity}/turn | Latency: {route.latency_turns}t",
                font_size="10sp",
                color=(0.6, 0.8, 1, 0.75),
                size_hint_y=None,
                height=dp(16),
                halign="left",
                text_size=(dp(500), None),
            ))

            eta_text = "N/A" if next_arrival is None else f"{next_arrival}t"
            card.add_widget(Label(
                text=f"Queue: {queue_len} | Next arrival ETA: {eta_text}",
                font_size="10sp",
                color=(0.5, 0.75, 0.95, 0.75),
                size_hint_y=None,
                height=dp(16),
                halign="left",
                text_size=(dp(500), None),
            ))

            if cargo_summary:
                cargo_text = ", ".join(
                    f"{amt} {res}" for res, amt in cargo_summary.items() if amt > 0
                )
                card.add_widget(Label(
                    text=f"In transit: {cargo_text}",
                    font_size="10sp",
                    color=(0.7, 0.85, 1, 0.85),
                    size_hint_y=None,
                    height=dp(16),
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
            manifest_override = None
            if route.auto_policy and route.auto_policy != "manual":
                manifest_override = self.game_state.trade._build_auto_manifest(
                    route,
                    colonies=self.game_state.colonies,
                    capacity=effective_capacity,
                    production=self.game_state.production if hasattr(self.game_state, "production") else None,
                )
            throughput = route.calculate_throughput(
                fleet=self.game_state.fleet,
                manifest_override=manifest_override,
            )
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

            toggle_text = "Pause" if route.enabled else "Resume"
            toggle_btn = Button(
                text=toggle_text,
                font_size="11sp",
                background_color=(0.3, 0.3, 0.1, 0.8) if route.enabled else (0.1, 0.3, 0.2, 0.8),
                color=(1, 0.8, 0.3, 1) if route.enabled else (0.3, 1, 0.5, 1),
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

    def _trade_routes_unlocked(self):
        if not self.game_state:
            return False
        tech_effects = self.game_state.tech.get_effects()
        trade_routes_unlocked = tech_effects.get("unlock_trade_routes")
        if trade_routes_unlocked is None:
            tech = self.game_state.tech.techs.get("logistics_1")
            trade_routes_unlocked = bool(tech and tech.researched)
        return bool(trade_routes_unlocked)

    def _on_create_route(self, *args):
        if not self.game_state:
            return
        if not self._trade_routes_unlocked():
            Popup(
                title="Trade Routes Locked",
                content=Label(
                    text="Research Logistics I to unlock trade routes.",
                    font_size="12sp",
                    color=(1, 0.6, 0.4, 1),
                ),
                size_hint=(0.6, 0.3),
            ).open()
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
            route.enabled = not route.enabled
            if getattr(route, "active", None) is not None:
                route.active = route.enabled
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
