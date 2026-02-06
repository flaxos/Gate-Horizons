"""Galaxy map screen — the primary game screen for Gate Horizons."""

from kivy.uix.screenmanager import Screen
from kivy.uix.floatlayout import FloatLayout
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.button import Button
from kivy.uix.label import Label
from kivy.uix.scatter import Scatter
from kivy.uix.widget import Widget
from kivy.graphics import Color, Ellipse, Line, Rectangle, InstructionGroup
from kivy.clock import Clock
from kivy.metrics import dp
from kivy.properties import ObjectProperty

from ..widgets.resource_bar import TopBar
from ..widgets.context_menu import ContextMenu, DestinationMenu
from ..widgets.notification import TurnReportPopup
from ..widgets.save_load import SaveGamePopup, LoadGamePopup


class NavButton(Button):
    pass


class EndTurnButton(Button):
    pass


class StarMapWidget(Widget):
    """Canvas-based star map rendering widget."""

    def __init__(self, game_state=None, on_system_tap=None, on_ship_tap=None, **kwargs):
        super().__init__(**kwargs)
        self.game_state = game_state
        self.on_system_tap = on_system_tap
        self.on_ship_tap = on_ship_tap
        self.selected_system = None
        self.selected_ship = None
        self._node_positions = {}  # system_id -> (screen_x, screen_y)
        self.bind(size=self._redraw, pos=self._redraw)

    def set_game_state(self, game_state):
        self.game_state = game_state
        self._redraw()

    def _redraw(self, *args):
        self.canvas.clear()
        if not self.game_state:
            return

        galaxy = self.game_state.galaxy
        self._node_positions.clear()

        # Padding
        pad = dp(40)
        w = self.width - 2 * pad
        h = self.height - 2 * pad

        # Calculate screen positions
        for sid, system in galaxy.systems.items():
            sx = self.x + pad + system.x * w
            sy = self.y + pad + system.y * h
            self._node_positions[sid] = (sx, sy)

        with self.canvas:
            # Draw gate connections (lines)
            drawn_edges = set()
            for sid, system in galaxy.systems.items():
                if not system.discovered:
                    continue
                sx, sy = self._node_positions[sid]
                for conn_id in system.gate_connections:
                    edge_key = tuple(sorted([sid, conn_id]))
                    if edge_key in drawn_edges:
                        continue
                    drawn_edges.add(edge_key)

                    conn = galaxy.systems.get(conn_id)
                    if not conn:
                        continue

                    cx, cy = self._node_positions[conn_id]

                    # Color by gate status
                    if system.gate_active and conn.gate_active:
                        Color(0.15, 0.6, 0.8, 0.6)  # Cyan for active
                    else:
                        Color(0.3, 0.3, 0.3, 0.4)  # Gray for dormant

                    Line(points=[sx, sy, cx, cy], width=1.2)

            # Draw system nodes
            node_size = dp(18)
            for sid, system in galaxy.systems.items():
                sx, sy = self._node_positions[sid]

                if not system.discovered:
                    # Undiscovered: dim question mark
                    Color(0.3, 0.3, 0.4, 0.3)
                    Ellipse(pos=(sx - node_size / 2, sy - node_size / 2),
                            size=(node_size, node_size))
                    continue

                # Color by tier
                tier_colors = {
                    1: (0.2, 0.8, 0.3, 1),    # Green: core
                    2: (0.2, 0.6, 1, 1),       # Blue: developing
                    3: (0.7, 0.7, 0.8, 0.8),   # Silver: frontier
                    0: (0.5, 0.5, 0.5, 0.5),   # Gray: unexplored
                }
                color = tier_colors.get(system.tier, tier_colors[3])

                # Selection highlight
                if sid == self.selected_system:
                    Color(1, 1, 1, 0.3)
                    Ellipse(pos=(sx - node_size * 0.8, sy - node_size * 0.8),
                            size=(node_size * 1.6, node_size * 1.6))

                Color(*color)
                Ellipse(pos=(sx - node_size / 2, sy - node_size / 2),
                        size=(node_size, node_size))

                # Colony indicator (inner dot)
                if sid in self.game_state.colonies.colonies:
                    Color(1, 1, 0.3, 0.9)
                    small = node_size * 0.35
                    Ellipse(pos=(sx - small / 2, sy - small / 2),
                            size=(small, small))

                # Dormant gate indicator
                if not system.gate_active:
                    Color(1, 0.3, 0.2, 0.7)
                    Line(circle=(sx, sy, node_size * 0.7), width=1.2)

            # Draw ship icons
            ship_offset = {}  # Count ships per location for stacking
            for ship in self.game_state.fleet.ships.values():
                loc = ship.location
                if loc not in self._node_positions:
                    continue

                system = galaxy.systems.get(loc)
                if not system or not system.discovered:
                    continue

                offset_count = ship_offset.get(loc, 0)
                ship_offset[loc] = offset_count + 1

                sx, sy = self._node_positions[loc]
                # Offset ships below the node
                ship_x = sx - dp(6) + offset_count * dp(14)
                ship_y = sy - node_size - dp(8)

                # Ship class colors
                class_colors = {
                    "scout": (0.3, 1, 0.7, 0.9),
                    "freighter": (1, 0.8, 0.2, 0.9),
                    "miner": (0.8, 0.5, 0.2, 0.9),
                    "corvette": (1, 0.3, 0.3, 0.9),
                }
                scolor = class_colors.get(ship.ship_class, (0.7, 0.7, 0.7, 0.9))

                if ship.id == self.selected_ship:
                    Color(1, 1, 1, 0.4)
                    Ellipse(pos=(ship_x - dp(2), ship_y - dp(2)),
                            size=(dp(16), dp(16)))

                Color(*scolor)
                # Small triangle/diamond for ships
                ship_size = dp(10)
                Ellipse(pos=(ship_x, ship_y), size=(ship_size, ship_size))

            # Draw system labels
            # Labels are drawn as canvas instructions (text not directly available on canvas)
            # We use a simple approach with positioned labels instead

    def on_touch_down(self, touch):
        if not self.collide_point(*touch.pos):
            return False

        # Check ship taps first (they're smaller, more specific)
        ship_offset = {}
        node_size = dp(18)
        for ship in (self.game_state.fleet.ships.values() if self.game_state else []):
            loc = ship.location
            if loc not in self._node_positions:
                continue
            system = self.game_state.galaxy.systems.get(loc)
            if not system or not system.discovered:
                continue

            offset_count = ship_offset.get(loc, 0)
            ship_offset[loc] = offset_count + 1

            sx, sy = self._node_positions[loc]
            ship_x = sx - dp(6) + offset_count * dp(14)
            ship_y = sy - node_size - dp(8)

            dist = ((touch.x - ship_x - dp(5))**2 + (touch.y - ship_y - dp(5))**2) ** 0.5
            if dist < dp(18):
                self.selected_ship = ship.id
                self.selected_system = None
                self._redraw()
                if self.on_ship_tap:
                    self.on_ship_tap(ship.id)
                return True

        # Check system node taps
        for sid, (sx, sy) in self._node_positions.items():
            dist = ((touch.x - sx)**2 + (touch.y - sy)**2) ** 0.5
            if dist < dp(24):
                system = self.game_state.galaxy.systems.get(sid)
                if system and system.discovered:
                    self.selected_system = sid
                    self.selected_ship = None
                    self._redraw()
                    if self.on_system_tap:
                        self.on_system_tap(sid)
                    return True

        # Tap on empty space — deselect
        self.selected_system = None
        self.selected_ship = None
        self._redraw()
        return True


class GalaxyMapScreen(Screen):
    """The primary game screen with star map, resource bar, and navigation."""

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.name = "galaxy_map"
        self.game_state = None
        self._side_panel = None
        self._build_ui()

    def _build_ui(self):
        root = FloatLayout()

        # Background
        with root.canvas.before:
            Color(0.02, 0.03, 0.08, 1)
            self._bg_rect = Rectangle(pos=root.pos, size=root.size)
        root.bind(size=self._update_bg, pos=self._update_bg)

        # Main vertical layout
        main_layout = BoxLayout(orientation="vertical", size_hint=(1, 1))

        # Top bar
        self.top_bar = TopBar()
        main_layout.add_widget(self.top_bar)

        # Middle area: map + optional side panel
        middle = BoxLayout(orientation="horizontal", size_hint=(1, 1))

        # Star map
        self.star_map = StarMapWidget(
            on_system_tap=self._on_system_tap,
            on_ship_tap=self._on_ship_tap,
        )
        middle.add_widget(self.star_map)

        # Side panel (initially empty, filled on selection)
        self.side_panel_container = BoxLayout(
            orientation="vertical",
            size_hint_x=None,
            width=dp(0),
        )
        middle.add_widget(self.side_panel_container)

        main_layout.add_widget(middle)

        # Bottom bar
        bottom_bar = BoxLayout(
            orientation="horizontal",
            size_hint_y=None,
            height=dp(56),
            padding=[dp(8), dp(6)],
            spacing=dp(8),
        )
        with bottom_bar.canvas.before:
            Color(0.05, 0.08, 0.15, 1)
            self._bottom_bg = Rectangle(pos=bottom_bar.pos, size=bottom_bar.size)
        bottom_bar.bind(
            size=lambda w, v: setattr(self._bottom_bg, 'size', v),
            pos=lambda w, v: setattr(self._bottom_bg, 'pos', v),
        )

        nav_buttons = [
            ("Map", "galaxy_map"),
            ("Fleet", "fleet_screen"),
            ("Tech", "tech_screen"),
            ("Colonies", "colony_screen"),
            ("Trade", "trade_screen"),
        ]

        for text, screen_name in nav_buttons:
            btn = Button(
                text=text,
                size_hint=(None, 1),
                width=dp(72),
                font_size="12sp",
                background_color=(0.08, 0.15, 0.25, 0.6),
                color=(0.7, 0.85, 1, 1),
            )
            btn.screen_name = screen_name
            btn.bind(on_release=self._on_nav)
            bottom_bar.add_widget(btn)

        # Save button
        save_btn = Button(
            text="Save",
            size_hint=(None, 1),
            width=dp(64),
            font_size="12sp",
            background_color=(0.15, 0.15, 0.35, 0.8),
            color=(0.7, 0.7, 1, 1),
        )
        save_btn.bind(on_release=self._on_save)
        bottom_bar.add_widget(save_btn)

        # Load button
        load_btn = Button(
            text="Load",
            size_hint=(None, 1),
            width=dp(64),
            font_size="12sp",
            background_color=(0.15, 0.15, 0.35, 0.8),
            color=(0.7, 0.7, 1, 1),
        )
        load_btn.bind(on_release=self._on_load)
        bottom_bar.add_widget(load_btn)

        # Spacer
        bottom_bar.add_widget(Widget())

        # End turn button
        end_turn_btn = Button(
            text="END TURN",
            size_hint=(None, 1),
            width=dp(110),
            font_size="14sp",
            bold=True,
            background_color=(0.2, 0.6, 0.3, 1),
            color=(1, 1, 1, 1),
        )
        end_turn_btn.bind(on_release=self._on_end_turn)
        bottom_bar.add_widget(end_turn_btn)

        main_layout.add_widget(bottom_bar)
        root.add_widget(main_layout)

        # System name labels overlay
        self.label_layout = FloatLayout(size_hint=(1, 1))
        root.add_widget(self.label_layout)

        self.add_widget(root)
        self.root = root

    def _update_bg(self, *args):
        self._bg_rect.pos = self.root.pos
        self._bg_rect.size = self.root.size

    def set_game_state(self, game_state):
        self.game_state = game_state
        self.star_map.set_game_state(game_state)
        self.top_bar.update(game_state)
        self._update_labels()

    def refresh(self):
        if self.game_state:
            self.star_map.set_game_state(self.game_state)
            self.top_bar.update(self.game_state)
            self._update_labels()

    def _update_labels(self):
        """Update floating system name labels."""
        self.label_layout.clear_widgets()
        if not self.game_state:
            return

        Clock.schedule_once(self._place_labels, 0.1)

    def _place_labels(self, dt):
        """Place labels after layout is computed."""
        self.label_layout.clear_widgets()
        if not self.star_map._node_positions:
            return

        for sid, (sx, sy) in self.star_map._node_positions.items():
            system = self.game_state.galaxy.systems.get(sid)
            if not system or not system.discovered:
                continue

            lbl = Label(
                text=system.name,
                font_size="10sp",
                color=(0.6, 0.75, 0.9, 0.8),
                size_hint=(None, None),
                size=(dp(100), dp(16)),
                pos=(sx - dp(50), sy + dp(12)),
            )
            self.label_layout.add_widget(lbl)

    def _on_system_tap(self, system_id):
        """Handle system node tap — show side panel."""
        self._show_system_panel(system_id)

    def _on_ship_tap(self, ship_id):
        """Handle ship icon tap — show ship actions."""
        self._show_ship_panel(ship_id)

    def _show_system_panel(self, system_id):
        system = self.game_state.galaxy.systems.get(system_id)
        if not system:
            return

        self.side_panel_container.clear_widgets()
        self.side_panel_container.width = dp(260)

        panel = BoxLayout(
            orientation="vertical",
            spacing=dp(4),
            padding=dp(8),
        )
        with panel.canvas.before:
            Color(0.04, 0.06, 0.12, 0.95)
            panel_bg = Rectangle(pos=panel.pos, size=panel.size)
        panel.bind(
            size=lambda w, v: setattr(panel_bg, 'size', v),
            pos=lambda w, v: setattr(panel_bg, 'pos', v),
        )

        # System name
        panel.add_widget(Label(
            text=system.name,
            font_size="16sp",
            bold=True,
            color=(0.3, 0.85, 1, 1),
            size_hint_y=None,
            height=dp(32),
        ))

        # Tier badge
        tier_names = {1: "Core World", 2: "Developing", 3: "Frontier"}
        panel.add_widget(Label(
            text=f"Tier {system.tier} - {tier_names.get(system.tier, 'Unknown')}",
            font_size="12sp",
            color=(0.5, 0.7, 0.9, 0.8),
            size_hint_y=None,
            height=dp(22),
        ))

        # Gate status
        gate_text = "Gate: Active" if system.gate_active else "Gate: Dormant"
        if not system.gate_active and system.gate_activation_cost:
            costs = ", ".join(f"{v} {k}" for k, v in system.gate_activation_cost.items())
            gate_text += f"\nActivation: {costs}"
        panel.add_widget(Label(
            text=gate_text,
            font_size="11sp",
            color=(0.15, 0.6, 0.8, 1) if system.gate_active else (1, 0.4, 0.2, 1),
            size_hint_y=None,
            height=dp(30),
        ))

        # Planets
        if system.planets:
            panel.add_widget(Label(
                text="Planets:",
                font_size="12sp",
                bold=True,
                color=(0.6, 0.8, 1, 1),
                size_hint_y=None,
                height=dp(22),
                halign="left",
                text_size=(dp(240), None),
            ))
            for planet in system.planets:
                col_tag = " [colonizable]" if planet.colonizable else ""
                panel.add_widget(Label(
                    text=f"  {planet.name} ({planet.type}){col_tag}",
                    font_size="11sp",
                    color=(0.7, 0.85, 1, 0.9),
                    size_hint_y=None,
                    height=dp(20),
                    halign="left",
                    text_size=(dp(240), None),
                ))

        # Ships present
        ships_here = self.game_state.fleet.get_ships_at(system_id)
        if ships_here:
            panel.add_widget(Label(
                text=f"Ships ({len(ships_here)}):",
                font_size="12sp",
                bold=True,
                color=(0.6, 0.8, 1, 1),
                size_hint_y=None,
                height=dp(22),
                halign="left",
                text_size=(dp(240), None),
            ))
            for ship in ships_here:
                btn = Button(
                    text=f"  {ship.name} ({ship.ship_class})",
                    size_hint_y=None,
                    height=dp(32),
                    font_size="11sp",
                    background_color=(0.12, 0.25, 0.4, 0.6),
                    color=(0.85, 0.95, 1, 1),
                    halign="left",
                )
                btn.ship_id = ship.id
                btn.bind(on_release=lambda b: self._show_ship_panel(b.ship_id))
                panel.add_widget(btn)

        # Colony info
        colony = self.game_state.colonies.colonies.get(system_id)
        if colony:
            panel.add_widget(Label(
                text=f"Colony: {colony.name} (pop: {colony.population})",
                font_size="12sp",
                color=(1, 1, 0.3, 0.9),
                size_hint_y=None,
                height=dp(22),
                halign="left",
                text_size=(dp(240), None),
            ))
            view_colony_btn = Button(
                text="View Colony",
                size_hint_y=None,
                height=dp(36),
                font_size="12sp",
                background_color=(0.15, 0.35, 0.2, 0.9),
                color=(0.3, 1, 0.5, 1),
            )
            view_colony_btn.colony_id = system_id
            view_colony_btn.bind(on_release=self._on_view_colony)
            panel.add_widget(view_colony_btn)

        # Actions
        if not system.gate_active and system.gate_activation_cost:
            activate_btn = Button(
                text="Activate Gate",
                size_hint_y=None,
                height=dp(40),
                font_size="13sp",
                background_color=(0.15, 0.4, 0.2, 0.9),
                color=(0.3, 1, 0.5, 1),
            )
            activate_btn.system_id = system_id
            activate_btn.bind(on_release=self._on_activate_gate)
            panel.add_widget(activate_btn)

        # View system detail
        detail_btn = Button(
            text="View System",
            size_hint_y=None,
            height=dp(40),
            font_size="13sp",
            background_color=(0.12, 0.25, 0.4, 0.8),
            color=(0.85, 0.95, 1, 1),
        )
        detail_btn.system_id = system_id
        detail_btn.bind(on_release=self._on_view_system)
        panel.add_widget(detail_btn)

        # Close button
        close_btn = Button(
            text="Close",
            size_hint_y=None,
            height=dp(36),
            font_size="12sp",
            background_color=(0.2, 0.1, 0.1, 0.6),
            color=(0.8, 0.6, 0.6, 1),
        )
        close_btn.bind(on_release=self._close_panel)
        panel.add_widget(close_btn)

        # Spacer
        panel.add_widget(Widget())

        self.side_panel_container.add_widget(panel)

    def _show_ship_panel(self, ship_id):
        ship = self.game_state.fleet.ships.get(ship_id)
        if not ship:
            return

        actions = self.game_state.fleet.get_contextual_actions(
            ship_id,
            galaxy=self.game_state.galaxy,
            colonies=self.game_state.colonies,
        )

        menu = ContextMenu(
            title_text=f"{ship.name} ({ship.ship_class})",
            actions=actions,
            callback=lambda action: self._execute_action(ship_id, action),
        )
        menu.open()

    def _execute_action(self, ship_id, action):
        """Execute a ship action."""
        ship = self.game_state.fleet.ships.get(ship_id)
        if not ship:
            return

        if action.name == "Move To":
            self._show_destination_menu(ship_id)
        elif action.name == "Scan System":
            system = self.game_state.galaxy.systems.get(ship.location)
            if system:
                system.surveyed = True
                self.refresh()
        elif action.name == "Begin Mining":
            ship.mining = True
            ship.mission = "mining"
            self.refresh()
        elif action.name == "Continue Mining":
            pass  # Already mining
        elif action.name in ("Patrol", "Deploy Probe"):
            ship.mission = action.name.lower().replace(" ", "_")
            self.refresh()
        elif action.name == "Repair":
            cost = action.cost
            if self.game_state.resources.can_afford(cost):
                self.game_state.resources.spend_dict(cost)
                ship.hull = ship.stats.max_hull
                self.refresh()
        elif action.name == "Refuel":
            cost = action.cost
            if self.game_state.resources.can_afford(cost):
                self.game_state.resources.spend_dict(cost)
                ship.fuel = ship.stats.fuel_capacity
                self.refresh()
        elif action.name == "Unload Cargo":
            for resource, amount in list(ship.cargo.items()):
                self.game_state.resources.add(resource, amount, ship.location)
                ship.cargo.clear()
            self.refresh()
        elif action.name == "Load Cargo":
            # Load available resources up to capacity
            self.refresh()
        elif action.name == "Emergency Stop":
            ship.path.clear()
            ship.destination = None
            ship.mission = None
            self.refresh()
        elif action.name == "Return Home":
            self.game_state.fleet.move_ship(ship_id, "sol", self.game_state.galaxy)
            self.refresh()

    def _show_destination_menu(self, ship_id):
        """Show destination selection menu."""
        ship = self.game_state.fleet.ships.get(ship_id)
        if not ship:
            return

        # Get reachable systems
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
            callback=lambda dest_id: self._move_ship_to(ship_id, dest_id),
        )
        menu.open()

    def _move_ship_to(self, ship_id, dest_id):
        result = self.game_state.fleet.move_ship(ship_id, dest_id, self.game_state.galaxy)
        self.refresh()

    def _on_activate_gate(self, btn):
        system_id = btn.system_id
        result = self.game_state.galaxy.activate_gate(
            system_id, self.game_state.resources
        )
        if result:
            self.refresh()
            self._show_system_panel(system_id)

    def _on_view_system(self, btn):
        from kivy.app import App
        app = App.get_running_app()
        if app:
            app.show_system_view(btn.system_id)

    def _close_panel(self, *args):
        self.side_panel_container.clear_widgets()
        self.side_panel_container.width = dp(0)
        self.star_map.selected_system = None
        self.star_map.selected_ship = None
        self.star_map._redraw()

    def _on_nav(self, btn):
        from kivy.app import App
        app = App.get_running_app()
        if app and hasattr(btn, "screen_name"):
            app.switch_screen(btn.screen_name)

    def _on_end_turn(self, *args):
        if not self.game_state:
            return

        report = self.game_state.process_turn()
        self.refresh()

        # Show turn report
        popup = TurnReportPopup(
            report=report,
            on_continue=self._after_turn_report,
        )
        popup.open()

        # Show events if any
        self._pending_events = list(self.game_state.events.event_queue)

    def _after_turn_report(self):
        """Handle post-turn-report, show pending events."""
        if hasattr(self, "_pending_events") and self._pending_events:
            self._show_next_event()
        else:
            # Auto-save
            from kivy.app import App
            app = App.get_running_app()
            if app and hasattr(app, "auto_save"):
                app.auto_save()

    def _on_view_colony(self, btn):
        from kivy.app import App
        app = App.get_running_app()
        if app:
            colony_screen = app.sm.get_screen("colony_screen")
            colony_screen.selected_colony = btn.colony_id
            app.switch_screen("colony_screen")

    def _on_save(self, *args):
        from kivy.app import App
        app = App.get_running_app()
        if app and hasattr(app, "save_manager") and self.game_state:
            popup = SaveGamePopup(
                save_manager=app.save_manager,
                game_state=self.game_state,
                on_saved=lambda: None,
            )
            popup.open()

    def _on_load(self, *args):
        from kivy.app import App
        app = App.get_running_app()
        if app and hasattr(app, "save_manager"):
            popup = LoadGamePopup(
                save_manager=app.save_manager,
                on_load=self._do_load,
            )
            popup.open()

    def _do_load(self, save_id):
        from kivy.app import App
        app = App.get_running_app()
        if app and hasattr(app, "save_manager"):
            from game.state import GameState
            loaded = app.save_manager.load_game(save_id, GameState)
            if loaded:
                app.game_state = loaded
                self.game_state = loaded
                app._push_state_to_screens()
                self.refresh()

    def _show_next_event(self):
        if not self._pending_events:
            return

        event = self._pending_events.pop(0)

        from kivy.app import App
        app = App.get_running_app()
        if app:
            app.show_event(event)
