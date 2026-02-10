"""Galaxy map screen — the primary game screen for Gate Horizons."""

import math

from kivy.uix.screenmanager import Screen
from kivy.uix.floatlayout import FloatLayout
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.gridlayout import GridLayout
from kivy.uix.button import Button
from kivy.uix.label import Label
from kivy.uix.widget import Widget
from kivy.uix.popup import Popup
from kivy.uix.scrollview import ScrollView
from kivy.graphics import Color, Ellipse, Line, Rectangle
from kivy.clock import Clock
from kivy.metrics import dp

from ..widgets.resource_bar import TopBar
from ..widgets.context_menu import ContextMenu, DestinationMenu
from ..widgets.save_load import SaveGamePopup, LoadGamePopup
from ..widgets.nav_menu import build_command_bar
from gate_horizons.game.resources import RESOURCE_TYPES

NAVIGATION_SCREENS = [
    "production_screen",
    "logistics_screen",
    "shipyard_screen",
]


class NavButton(Button):
    pass


class EndTurnButton(Button):
    pass


class StarMapWidget(Widget):
    """Canvas-based star map rendering widget."""

    def __init__(
        self,
        game_state=None,
        on_system_tap=None,
        on_ship_tap=None,
        on_view_change=None,
        **kwargs,
    ):
        super().__init__(**kwargs)
        self.game_state = game_state
        self.on_system_tap = on_system_tap
        self.on_ship_tap = on_ship_tap
        self.on_view_change = on_view_change
        self.selected_system = None
        self.selected_ship = None
        self._node_positions = {}  # system_id -> (screen_x, screen_y)
        self._base_node_positions = {}
        self._pan_offset = [0.0, 0.0]
        self._scale = 1.0
        self._min_scale = 0.6
        self._max_scale = 2.5
        self.show_trade_flows = False
        self.trade_flow_legend = {}
        self._flow_resource_colors = {
            "energy": (0.95, 0.8, 0.25, 0.75),
            "metals": (0.7, 0.7, 0.8, 0.75),
            "exotics": (0.7, 0.4, 0.9, 0.75),
            "credits": (0.25, 0.85, 0.5, 0.75),
            "intel": (0.35, 0.7, 1, 0.75),
        }
        self._active_touches = {}
        self._pinch_start_distance = None
        self._pinch_start_scale = None
        self._pinch_start_offset = None
        self._dash_offset = 0.0
        self._pulse_t = 0.0
        Clock.schedule_interval(self._advance_dash, 1 / 45)
        self.bind(size=self._redraw, pos=self._redraw)

    def set_game_state(self, game_state):
        self.game_state = game_state
        self._redraw()

    def set_trade_flows_enabled(self, enabled: bool):
        self.show_trade_flows = bool(enabled)
        self._redraw()

    def get_trade_flow_legend(self) -> dict:
        return dict(self.trade_flow_legend)

    def _redraw(self, *args):
        self.canvas.clear()
        if not self.game_state:
            return

        galaxy = self.game_state.galaxy
        self._node_positions.clear()
        self._base_node_positions.clear()

        # Padding
        pad = dp(40)
        w = self.width - 2 * pad
        h = self.height - 2 * pad

        # Calculate screen positions
        for sid, system in galaxy.systems.items():
            base_x = self.x + pad + system.x * w
            base_y = self.y + pad + system.y * h
            self._base_node_positions[sid] = (base_x, base_y)
            self._node_positions[sid] = self._apply_transform(base_x, base_y)

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
                        pulse = math.sin(self._pulse_t) * 0.08
                        Color(0.15, 0.6, 0.8, 0.6 + pulse)  # Cyan for active
                    else:
                        Color(0.3, 0.3, 0.3, 0.4)  # Gray for dormant

                    Line(points=[sx, sy, cx, cy], width=1.2)

            self._draw_trade_flows(galaxy)
            self._draw_ship_paths(galaxy)

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
                    pulse = math.sin(self._pulse_t) * 0.05
                    Color(1, 1, 0.3, 0.88 + pulse)
                    small = node_size * (0.35 + pulse)
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

    def _advance_dash(self, dt):
        self._dash_offset = (self._dash_offset + dp(2.5)) % dp(120)
        self._pulse_t += dt * 1.5
        self._redraw()

    def _draw_trade_flows(self, galaxy):
        segments = self._get_trade_flow_segments()
        if not segments:
            return

        flow_resources = {}
        for segment in segments:
            start_id = segment["source"]
            end_id = segment["destination"]
            if start_id not in self._node_positions or end_id not in self._node_positions:
                continue
            start_system = galaxy.systems.get(start_id)
            end_system = galaxy.systems.get(end_id)
            if not start_system or not end_system:
                continue
            if not start_system.discovered or not end_system.discovered:
                continue

            resource = segment["resource"]
            color = self._flow_resource_colors.get(resource, (0.6, 0.7, 0.85, 0.7))
            flow_resources[resource] = color

            x1, y1 = self._node_positions[start_id]
            x2, y2 = self._node_positions[end_id]
            dx = x2 - x1
            dy = y2 - y1
            distance = (dx * dx + dy * dy) ** 0.5
            if distance <= 0:
                continue

            perp_x = -dy / distance
            perp_y = dx / distance
            offset = dp(6)
            direction = segment["direction"]
            offset_sign = 1 if direction == "outbound" else -1
            x1 += perp_x * offset * offset_sign
            y1 += perp_y * offset * offset_sign
            x2 += perp_x * offset * offset_sign
            y2 += perp_y * offset * offset_sign

            Color(*color)
            Line(points=[x1, y1, x2, y2], width=1.1)
            self._draw_flow_arrow(x1, y1, x2, y2, color)

        self.trade_flow_legend = flow_resources

    def _draw_flow_arrow(self, x1, y1, x2, y2, color):
        dx = x2 - x1
        dy = y2 - y1
        distance = (dx * dx + dy * dy) ** 0.5
        if distance <= 0:
            return
        unit_x = dx / distance
        unit_y = dy / distance
        arrow_len = dp(10)
        arrow_width = dp(5)
        base_x = x1 + unit_x * (distance * 0.6)
        base_y = y1 + unit_y * (distance * 0.6)
        left_x = base_x - unit_x * arrow_len + (-unit_y) * arrow_width
        left_y = base_y - unit_y * arrow_len + unit_x * arrow_width
        right_x = base_x - unit_x * arrow_len - (-unit_y) * arrow_width
        right_y = base_y - unit_y * arrow_len - unit_x * arrow_width
        Color(*color)
        Line(points=[base_x, base_y, left_x, left_y], width=1.2)
        Line(points=[base_x, base_y, right_x, right_y], width=1.2)

    def _get_trade_flow_segments(self) -> list[dict]:
        self.trade_flow_legend = {}
        if not self.game_state or not self.show_trade_flows:
            return []
        tech_effects = self.game_state.tech.get_effects() if hasattr(self.game_state, "tech") else {}
        segments = self.game_state.trade.build_flow_segments(
            colonies=self.game_state.colonies,
            fleet=self.game_state.fleet,
            tech_effects=tech_effects,
            galaxy=self.game_state.galaxy,
        )
        return segments

    def _draw_ship_paths(self, galaxy):
        ships_in_transit = [
            ship for ship in self.game_state.fleet.ships.values()
            if ship.path
        ]
        if not ships_in_transit:
            return

        for ship in ships_in_transit:
            system_ids = [ship.location] + list(ship.path)
            for system_id in system_ids:
                system = galaxy.systems.get(system_id)
                if not system or not system.discovered:
                    break
                if system_id not in self._node_positions:
                    break
            else:
                points = []
                for system_id in system_ids:
                    sx, sy = self._node_positions[system_id]
                    points.extend([sx, sy])

                is_selected = ship.id == self.selected_ship
                if is_selected:
                    Color(0.4, 0.8, 1, 0.5)
                    width = 1.6
                    dash_length = dp(6)
                    marker_color = (0.7, 0.95, 1, 0.9)
                    marker_size = dp(8)
                else:
                    Color(0.35, 0.65, 0.9, 0.3)
                    width = 1.2
                    dash_length = dp(4)
                    marker_color = (0.6, 0.85, 1, 0.45)
                    marker_size = dp(6)

                Line(
                    points=points,
                    width=width,
                    dash_length=dash_length,
                    dash_offset=self._dash_offset,
                )

                next_waypoint = ship.path[0] if ship.path else None
                if next_waypoint:
                    wx, wy = self._node_positions[next_waypoint]
                    Color(*marker_color)
                    Ellipse(
                        pos=(wx - marker_size / 2, wy - marker_size / 2),
                        size=(marker_size, marker_size),
                    )

    def _apply_transform(self, x, y):
        return (
            x * self._scale + self._pan_offset[0],
            y * self._scale + self._pan_offset[1],
        )

    def _clamp_scale(self, value):
        return max(self._min_scale, min(self._max_scale, value))

    def _zoom_at(self, center, scale_factor):
        new_scale = self._clamp_scale(self._scale * scale_factor)
        if new_scale == self._scale:
            return

        cx, cy = center
        base_cx = (cx - self._pan_offset[0]) / self._scale
        base_cy = (cy - self._pan_offset[1]) / self._scale

        self._scale = new_scale
        self._pan_offset[0] = cx - base_cx * self._scale
        self._pan_offset[1] = cy - base_cy * self._scale

    def _handle_tap(self, touch):
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

    def on_touch_down(self, touch):
        if not self.collide_point(*touch.pos):
            return False
        if touch.is_mouse_scrolling:
            zoom_factor = 1.1 if touch.button == "scrolldown" else 0.9
            self._zoom_at(touch.pos, zoom_factor)
            self._redraw()
            if self.on_view_change:
                self.on_view_change()
            return True

        self._active_touches[touch.uid] = touch
        touch.ud["star_map"] = {"moved": False}

        if len(self._active_touches) == 2:
            touches = list(self._active_touches.values())
            self._pinch_start_distance = self._distance(touches[0], touches[1])
            self._pinch_start_scale = self._scale
            self._pinch_start_offset = list(self._pan_offset)
        return True

    def on_touch_move(self, touch):
        if touch.uid not in self._active_touches:
            return False

        touch.ud.get("star_map", {})["moved"] = True

        if len(self._active_touches) >= 2:
            touches = list(self._active_touches.values())[:2]
            current_distance = self._distance(touches[0], touches[1])
            if self._pinch_start_distance:
                scale_factor = current_distance / self._pinch_start_distance
                target_scale = self._clamp_scale(self._pinch_start_scale * scale_factor)
                mid_x = (touches[0].x + touches[1].x) / 2
                mid_y = (touches[0].y + touches[1].y) / 2
                base_mid_x = (mid_x - self._pinch_start_offset[0]) / self._pinch_start_scale
                base_mid_y = (mid_y - self._pinch_start_offset[1]) / self._pinch_start_scale
                self._scale = target_scale
                self._pan_offset[0] = mid_x - base_mid_x * self._scale
                self._pan_offset[1] = mid_y - base_mid_y * self._scale
        else:
            self._pan_offset[0] += touch.dx
            self._pan_offset[1] += touch.dy

        self._redraw()
        if self.on_view_change:
            self.on_view_change()
        return True

    def on_touch_up(self, touch):
        if touch.uid not in self._active_touches:
            return False

        moved = touch.ud.get("star_map", {}).get("moved", False)
        self._active_touches.pop(touch.uid, None)

        if len(self._active_touches) < 2:
            self._pinch_start_distance = None
            self._pinch_start_scale = None
            self._pinch_start_offset = None

        if not moved:
            return self._handle_tap(touch)
        return True

    @staticmethod
    def _distance(touch_a, touch_b):
        return ((touch_a.x - touch_b.x) ** 2 + (touch_a.y - touch_b.y) ** 2) ** 0.5


class GalaxyMapScreen(Screen):
    """The primary game screen with star map, resource bar, and navigation."""

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.name = "galaxy_map"
        self.game_state = None
        self._side_panel = None
        self.selected_system_id = None
        self._auto_selected = False
        self.flow_toggle_btn = None
        self.flow_legend = None
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
            on_view_change=self._refresh_labels_for_view,
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

        # Bottom command bar (categorised dropdowns + always-visible END TURN)
        bottom_bar, self.flow_toggle_btn = build_command_bar(
            nav_callback=self._on_nav_by_name,
            end_turn_callback=self._on_end_turn,
            save_callback=self._on_save,
            load_callback=self._on_load,
            flow_toggle_callback=self._on_toggle_trade_flows,
            settings_callback=self._on_settings,
        )

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
        self._auto_select_home_colony()
        self._refresh_side_panel()
        self._update_flow_legend()

    def refresh(self):
        if self.game_state:
            self.star_map.set_game_state(self.game_state)
            self.top_bar.update(self.game_state)
            self._update_labels()
            self._refresh_side_panel()
            self._update_flow_legend()

    def _auto_select_home_colony(self):
        if self._auto_selected or not self.game_state:
            return
        if not self.game_state.colonies.colonies:
            return
        first_colony_id = next(iter(self.game_state.colonies.colonies))
        self._auto_selected = True
        self._show_system_panel(first_colony_id)

    def _refresh_side_panel(self):
        if self.selected_system_id and self.side_panel_container.width > 0:
            self._show_system_panel(self.selected_system_id)

    def _update_labels(self):
        """Update floating system name labels."""
        self.label_layout.clear_widgets()
        if not self.game_state:
            return

        Clock.schedule_once(self._place_labels, 0.1)

    def _refresh_labels_for_view(self):
        if not self.game_state or not self.star_map._node_positions:
            return
        self._place_labels(0)

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

        self._update_flow_legend()

    def _on_toggle_trade_flows(self, *args):
        enabled = not self.star_map.show_trade_flows
        self.star_map.set_trade_flows_enabled(enabled)
        if self.flow_toggle_btn:
            self.flow_toggle_btn.text = "Flows: ON" if enabled else "Toggle Flows"
        self._update_flow_legend()

    def _update_flow_legend(self):
        if not self.star_map.show_trade_flows:
            if self.flow_legend and self.flow_legend.parent:
                self.label_layout.remove_widget(self.flow_legend)
            return
        legend_data = self.star_map.get_trade_flow_legend()
        if not legend_data:
            if self.flow_legend and self.flow_legend.parent:
                self.label_layout.remove_widget(self.flow_legend)
            return

        if not self.flow_legend:
            self.flow_legend = self._build_flow_legend()
        if not self.flow_legend.parent:
            self.label_layout.add_widget(self.flow_legend)

        self.flow_legend.clear_widgets()
        self.flow_legend.add_widget(Label(
            text="Flow Legend",
            font_size="11sp",
            bold=True,
            color=(0.7, 0.9, 1, 0.95),
            size_hint_y=None,
            height=dp(18),
        ))
        for resource, color in legend_data.items():
            row = BoxLayout(
                orientation="horizontal",
                size_hint_y=None,
                height=dp(18),
                spacing=dp(6),
            )
            swatch = Widget(size_hint=(None, None), size=(dp(10), dp(10)))
            with swatch.canvas:
                Color(*color)
                rect = Rectangle(pos=swatch.pos, size=swatch.size)
            swatch.bind(
                pos=lambda w, v, r=rect: setattr(r, "pos", v),
                size=lambda w, v, r=rect: setattr(r, "size", v),
            )
            row.add_widget(swatch)
            row.add_widget(Label(
                text=resource,
                font_size="10sp",
                color=(0.7, 0.85, 1, 0.9),
                halign="left",
                valign="middle",
            ))
            self.flow_legend.add_widget(row)

    def _build_flow_legend(self):
        legend = BoxLayout(
            orientation="vertical",
            size_hint=(None, None),
            size=(dp(140), dp(120)),
            padding=dp(6),
            spacing=dp(4),
            pos_hint={"right": 0.98, "top": 0.98},
        )
        with legend.canvas.before:
            Color(0.05, 0.08, 0.15, 0.9)
            legend_bg = Rectangle(pos=legend.pos, size=legend.size)
        legend.bind(
            pos=lambda w, v: setattr(legend_bg, "pos", v),
            size=lambda w, v: setattr(legend_bg, "size", v),
        )
        return legend

    def _on_system_tap(self, system_id):
        """Handle system node tap — show side panel."""
        self._show_system_panel(system_id)

    def _on_ship_tap(self, ship_id):
        """Handle ship icon tap — show ship actions."""
        self._show_ship_panel(ship_id)

    def _show_system_panel(self, system_id):
        system = self.game_state.galaxy.systems.get(system_id)
        if not system:
            self._close_panel()
            return
        self.selected_system_id = system_id

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
                text="🪐 Planets:",
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
                    text=f"  🪐 {planet.name} ({planet.type}){col_tag}",
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
                text=f"🚀 Ships ({len(ships_here)}):",
                font_size="12sp",
                bold=True,
                color=(0.6, 0.8, 1, 1),
                size_hint_y=None,
                height=dp(22),
                halign="left",
                text_size=(dp(240), None),
            ))
            for ship in ships_here:
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
                    ship_box = BoxLayout(
                        orientation="vertical",
                        size_hint_y=None,
                        height=dp(50),
                        spacing=dp(2),
                    )
                    btn = Button(
                        text=f"  🚀 {ship.name} ({ship.ship_class})",
                        size_hint_y=None,
                        height=dp(32),
                        font_size="11sp",
                        background_color=(0.12, 0.25, 0.4, 0.6),
                        color=(0.85, 0.95, 1, 1),
                        halign="left",
                    )
                    btn.ship_id = ship.id
                    btn.bind(on_release=lambda b: self._show_ship_panel(b.ship_id))
                    ship_box.add_widget(btn)
                    ship_box.add_widget(Label(
                        text=travel_status,
                        font_size="10sp",
                        color=(1, 0.85, 0.4, 0.9),
                        size_hint_y=None,
                        height=dp(16),
                        halign="left",
                        text_size=(dp(240), None),
                    ))
                    panel.add_widget(ship_box)
                else:
                    btn = Button(
                        text=f"  🚀 {ship.name} ({ship.ship_class})",
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
                text=f"🏠 Colony: {colony.name} (pop: {colony.population})",
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

            panel.add_widget(Label(
                text="📦 Stockpiles",
                font_size="12sp",
                bold=True,
                color=(0.6, 0.8, 1, 1),
                size_hint_y=None,
                height=dp(22),
                halign="left",
                text_size=(dp(240), None),
            ))

            storage_caps = colony.get_storage_caps()
            resource_labels = {
                "energy": "⚡ Energy",
                "metals": "⛏ Metals",
                "exotics": "💎 Exotics",
                "credits": "💰 Credits",
                "intel": "🛰 Intel",
            }
            stock_grid = GridLayout(
                cols=2,
                size_hint_y=None,
                row_default_height=dp(20),
                row_force_default=True,
                spacing=dp(4),
            )
            stock_grid.bind(minimum_height=stock_grid.setter("height"))
            for resource in RESOURCE_TYPES:
                current = colony.stockpiles.get(resource, 0)
                cap = storage_caps.get(resource, 0)
                stock_grid.add_widget(Label(
                    text=resource_labels.get(resource, resource.title()),
                    font_size="11sp",
                    color=(0.8, 0.9, 1, 1),
                    halign="left",
                    text_size=(dp(120), None),
                ))
                stock_grid.add_widget(Label(
                    text=f"{current} / {cap}",
                    font_size="11sp",
                    color=(0.6, 0.85, 1, 0.9),
                    halign="left",
                    text_size=(dp(80), None),
                ))
            panel.add_widget(stock_grid)

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
            game_state=self.game_state,
        )

        menu = ContextMenu(
            title_text=f"{ship.name} ({ship.ship_class})",
            actions=actions,
            callback=lambda action: self._execute_action(ship_id, action),
        )
        menu.open()

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

    def _execute_action(self, ship_id, action):
        """Execute a ship action."""
        ship = self.game_state.fleet.ships.get(ship_id)
        if not ship:
            return

        if action.name in ("Move To", "Reroute"):
            self._show_destination_menu(ship_id)
        elif action.name == "Reposition (Local)":
            success, message = self.game_state.execute_local_move(ship_id, ship.location)
            if not success:
                self._show_notice(message)
            self.refresh()
        elif action.name == "Continue":
            self.refresh()
        elif action.name in {
            "Scan System",
            "Deploy Probe",
            "Patrol",
            "Blockade",
            "Investigate Anomaly",
            "Establish Colony",
            "Repair",
            "Refuel",
            "Intercept",
            "Engage",
            "Retreat",
            "Hail",
        }:
            params = {}
            if action.name == "Deploy Probe":
                params = {"credits": action.cost.get("credits", 5)}
            self.game_state.issue_ship_order(ship_id, action.name, params=params)
            self.refresh()
        elif action.name == "Escort":
            self._show_escort_target_menu(ship_id)
        elif action.name == "Begin Mining":
            self.game_state.issue_ship_order(ship_id, "Begin Mining")
            self.refresh()
        elif action.name == "Continue Mining":
            self._show_notice(f"{ship.name} continues mining in {ship.location}.")
        elif action.name == "Unload Cargo":
            self.game_state.unload_ship_cargo_to_colony(ship_id)
            self.refresh()
        elif action.name == "Load Cargo":
            self.game_state.load_ship_cargo_from_colony(ship_id)
            self.refresh()
        elif action.name == "Load Colonists":
            self.game_state.load_colonists_to_ship(ship_id)
            self.refresh()
        elif action.name == "Unload Colonists":
            self.game_state.unload_colonists_to_colony(ship_id)
            self.refresh()
        elif action.name == "Emergency Jettison":
            ship.cargo.clear()
            self.refresh()
        elif action.name == "Deliver Cargo":
            if ship.cargo_used == 0:
                return
            colony_systems = list(self.game_state.colonies.colonies.keys())
            if ship.location in colony_systems:
                self.game_state.unload_ship_cargo_to_colony(ship_id)
                self.refresh()
                return
            shortest_path = None
            nearest_system = None
            for system_id in colony_systems:
                path = self.game_state.galaxy.get_path(ship.location, system_id)
                if not path:
                    continue
                if shortest_path is None or len(path) < len(shortest_path):
                    shortest_path = path
                    nearest_system = system_id
            if nearest_system:
                self.game_state.fleet.move_ship(
                    ship_id,
                    nearest_system,
                    self.game_state.galaxy,
                )
                self.refresh()
        elif action.name == "Emergency Stop":
            self.game_state.issue_ship_order(ship_id, "Emergency Stop")
            self.refresh()
        elif action.name == "Return Home":
            colony_systems = list(self.game_state.colonies.colonies.keys())
            shortest_path = None
            nearest_system = None
            for system_id in colony_systems:
                path = self.game_state.galaxy.get_path(ship.location, system_id)
                if not path:
                    continue
                if shortest_path is None or len(path) < len(shortest_path):
                    shortest_path = path
                    nearest_system = system_id
            if nearest_system:
                self.game_state.fleet.move_ship(
                    ship_id,
                    nearest_system,
                    self.game_state.galaxy,
                )
            else:
                self.game_state.log.append(
                    f"{ship.name} cannot return home: no reachable colony."
                )
            self.refresh()
        elif action.name in {"Set Trade Route", "Prospect", "Set Auto-Mine"}:
            self._show_notice(
                f"{action.name} is not implemented yet. Check other menus for updates."
            )
        else:
            self._show_notice(f"{action.name} is not available yet.")

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
        self.refresh()

    def _on_activate_gate(self, btn):
        system_id = btn.system_id
        result = self.game_state.activate_gate(system_id)
        if result:
            self.refresh()
            self._show_system_panel(system_id)
        else:
            self._show_notice("Unable to activate gate. Check resources or gate status.")

    def _on_view_system(self, btn):
        from kivy.app import App
        app = App.get_running_app()
        if app:
            app.show_system_view(btn.system_id)

    def _close_panel(self, *args):
        self.side_panel_container.clear_widgets()
        self.side_panel_container.width = dp(0)
        self.selected_system_id = None
        self.star_map.selected_system = None
        self.star_map.selected_ship = None
        self.star_map._redraw()

    def _on_nav(self, btn):
        from kivy.app import App
        app = App.get_running_app()
        if app and hasattr(btn, "screen_name"):
            app.switch_screen(btn.screen_name)

    def _on_nav_by_name(self, screen_name):
        """Navigate to a screen by name (used by the command bar dropdowns)."""
        from kivy.app import App
        app = App.get_running_app()
        if app:
            app.switch_screen(screen_name)

    def _on_end_turn(self, *args):
        if not self.game_state:
            return

        report = self.game_state.process_turn()
        self.refresh()

        # Show turn report
        from kivy.app import App
        app = App.get_running_app()
        if app and hasattr(app, "show_turn_report"):
            app.show_turn_report(
                report=report,
                pending_encounters=len(self.game_state.pending_encounters),
                on_continue=self._after_turn_report,
                on_view_encounters=self._open_encounters,
            )

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

    def _open_encounters(self):
        from kivy.app import App
        app = App.get_running_app()
        if app:
            app.switch_screen("encounter_screen")

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

    def _on_settings(self, *args):
        from kivy.app import App
        app = App.get_running_app()
        if not app:
            return
        from gate_horizons.ui.widgets.settings import SettingsPopup
        settings = getattr(app, "settings", None)
        if not settings:
            return
        encounter_mode = None
        on_mode_change = None
        if getattr(app, "game_state", None):
            encounter_mode = app.game_state.encounter_resolution_mode
            on_mode_change = app.game_state.set_encounter_resolution_mode
        popup = SettingsPopup(
            settings=settings,
            on_save=getattr(app, "apply_settings", None),
            encounter_mode=encounter_mode,
            on_encounter_mode_change=on_mode_change,
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
            from gate_horizons.game.state import GameState
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
