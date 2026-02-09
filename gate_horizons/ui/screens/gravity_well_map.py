"""Gravity Well Map — hierarchical 3-level map view.

Levels:
  1) System level  — bodies orbiting a star, jump points, ships
  2) Planet level  — planet-centric view with moons/details
  3) Body level    — surface regions / local body detail

Shares the same pinch-to-zoom + pan behaviour as the Galaxy Map via
the MapCameraWidget base class.
"""

import math
import time

from kivy.uix.screenmanager import Screen
from kivy.uix.floatlayout import FloatLayout
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.button import Button
from kivy.uix.togglebutton import ToggleButton
from kivy.uix.label import Label
from kivy.uix.widget import Widget
from kivy.uix.scrollview import ScrollView
from kivy.uix.gridlayout import GridLayout
from kivy.uix.popup import Popup
from kivy.graphics import Color, Ellipse, Line, Rectangle, Triangle
from kivy.clock import Clock
from kivy.metrics import dp

from ..widgets.resource_bar import TopBar
from ..widgets.map_camera import MapCameraWidget
from gate_horizons.game.planet_comparison import build_comparison_data


# ======================================================================
# Body-type icon drawing helpers
# ======================================================================

# Colour palettes for body types
BODY_TYPE_COLORS = {
    "rocky": (0.6, 0.5, 0.3, 1),
    "gas_giant": (0.8, 0.6, 0.2, 1),
    "ice": (0.6, 0.8, 1, 1),
    "volcanic": (1, 0.3, 0.1, 1),
    "oceanic": (0.2, 0.5, 0.9, 1),
    "barren": (0.5, 0.5, 0.5, 1),
    "desert": (0.85, 0.7, 0.3, 1),
    "toxic": (0.5, 0.8, 0.2, 1),
    "garden": (0.3, 0.7, 0.3, 1),
    "artificial": (0.4, 0.9, 0.9, 1),
    "asteroid_belt": (0.55, 0.45, 0.35, 1),
    "moon": (0.7, 0.7, 0.8, 1),
}

SPECTRAL_COLORS = {
    "O": (0.6, 0.8, 1, 1),
    "B": (0.7, 0.8, 1, 1),
    "A": (0.8, 0.85, 1, 1),
    "F": (1, 1, 0.9, 1),
    "G": (1, 0.9, 0.3, 1),
    "K": (1, 0.75, 0.4, 1),
    "M": (1, 0.5, 0.4, 1),
    "D": (0.9, 0.9, 0.95, 1),
}


def _draw_star_icon(canvas, cx, cy, size, color):
    """Draw a star glyph — glowing circle with four corona rays."""
    # Glow halo
    Color(color[0], color[1], color[2], 0.25)
    halo = size * 2
    Ellipse(pos=(cx - halo / 2, cy - halo / 2), size=(halo, halo))
    # Core
    Color(*color)
    Ellipse(pos=(cx - size / 2, cy - size / 2), size=(size, size))
    # Corona rays
    Color(color[0], color[1], color[2], 0.5)
    ray_len = size * 0.6
    for angle_deg in (0, 45, 90, 135):
        a = math.radians(angle_deg)
        dx, dy = math.cos(a) * ray_len, math.sin(a) * ray_len
        Line(points=[cx - dx, cy - dy, cx + dx, cy + dy], width=1)


def _draw_planet_icon(canvas, cx, cy, size, color, has_atmosphere=False):
    """Draw a planet — circle with optional atmosphere haze."""
    if has_atmosphere:
        Color(color[0] * 0.6, color[1] * 0.6, color[2] * 1.2, 0.2)
        atmo = size * 1.35
        Ellipse(pos=(cx - atmo / 2, cy - atmo / 2), size=(atmo, atmo))
    Color(*color)
    Ellipse(pos=(cx - size / 2, cy - size / 2), size=(size, size))


def _draw_moon_icon(canvas, cx, cy, size, color=(0.7, 0.7, 0.8, 0.9)):
    """Draw a moon — smaller dot with crescent shadow."""
    Color(*color)
    Ellipse(pos=(cx - size / 2, cy - size / 2), size=(size, size))
    # Crescent shadow
    Color(0, 0, 0, 0.4)
    offset = size * 0.2
    Ellipse(
        pos=(cx - size / 2 + offset, cy - size / 2),
        size=(size * 0.8, size),
    )


def _draw_asteroid_icon(canvas, cx, cy, size, color=(0.55, 0.45, 0.35, 0.9)):
    """Draw asteroid/belt — cluster of small irregular dots."""
    Color(*color)
    offsets = [(-0.3, 0.2), (0.25, -0.15), (0, 0.3), (-0.2, -0.25), (0.3, 0.1)]
    for ox, oy in offsets:
        s = size * 0.25
        Ellipse(
            pos=(cx + ox * size - s / 2, cy + oy * size - s / 2),
            size=(s, s),
        )


def _draw_station_icon(canvas, cx, cy, size, color=(0.3, 0.85, 0.9, 0.9)):
    """Draw station — diamond shape."""
    Color(*color)
    half = size / 2
    Line(
        points=[
            cx, cy + half,
            cx + half, cy,
            cx, cy - half,
            cx - half, cy,
            cx, cy + half,
        ],
        width=1.4,
    )


# ======================================================================
# System Map Widget (Level 1)
# ======================================================================

class SystemMapWidget(MapCameraWidget):
    """Renders a star system: star at centre, planets in orbits, ships."""

    def __init__(self, game_state=None, system_id=None,
                 on_body_tap=None, on_ship_tap=None, **kwargs):
        super().__init__(**kwargs)
        self.game_state = game_state
        self.system_id = system_id
        self.on_body_tap = on_body_tap
        self.on_ship_tap = on_ship_tap
        self.selected_body_id = None
        self.selected_ship_id = None
        self._body_positions = {}  # body_id -> (sx, sy, size)
        self._ship_positions = {}  # ship_id -> (sx, sy)
        self._min_scale = 0.4
        self._max_scale = 3.5
        self._pulse_t = 0.0
        self._dash_offset = 0.0
        Clock.schedule_interval(self._tick, 1 / 30)
        self.bind(size=self._redraw, pos=self._redraw)

    def _tick(self, dt):
        self._pulse_t += dt * 1.5
        self._dash_offset = (self._dash_offset + dp(2.5)) % dp(120)
        self._redraw()

    def set_data(self, game_state, system_id):
        self.game_state = game_state
        self.system_id = system_id
        self.selected_body_id = None
        self.selected_ship_id = None
        self.reset_camera()

    # ------------------------------------------------------------------
    # Orbital spacing helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _log_orbit_radius(index, total, max_radius):
        """Compute orbital radius using logarithmic spacing.

        Inner planets are packed closer together while outer planets
        get progressively more room — mimicking Titius-Bode spacing.
        """
        if total <= 1:
            return max_radius * 0.5
        # Map index [0..total-1] to a log-spaced value in [0.18 .. 1.0]
        t = index / (total - 1)  # 0 → 1
        # Use a logarithmic curve: log(1 + t*k) / log(1 + k)
        k = 6.0  # Controls how compressed the inner orbits are
        norm = math.log(1 + t * k) / math.log(1 + k)
        return max_radius * (0.18 + 0.80 * norm)

    @staticmethod
    def _classify_planet_zone(index, total):
        """Return 'inner', 'habitable', or 'outer' zone for a planet.

        Uses a simple heuristic: first ~30% inner, next ~20% habitable,
        rest outer.  Gas giants are always outer regardless of index.
        """
        if total <= 1:
            return "habitable"
        frac = index / (total - 1)
        if frac <= 0.3:
            return "inner"
        elif frac <= 0.5:
            return "habitable"
        return "outer"

    # ------------------------------------------------------------------
    # Main draw
    # ------------------------------------------------------------------

    def _redraw(self, *args):
        self.canvas.clear()
        if not self.game_state or not self.system_id:
            return

        system = self.game_state.galaxy.systems.get(self.system_id)
        if not system:
            return

        self._body_positions.clear()
        self._ship_positions.clear()

        cx_base = self.center_x
        cy_base = self.center_y
        max_radius = min(self.width, self.height) * 0.40
        is_surveyed = bool(system.surveyed)
        ring_cx, ring_cy = self._apply_transform(cx_base, cy_base)
        num_planets = len(system.planets)

        # Pre-compute orbit radii (log-spaced)
        orbit_radii = []
        for i in range(num_planets):
            orbit_radii.append(self._log_orbit_radius(i, num_planets, max_radius))

        # Determine zone boundaries for habitable zone band
        hab_inner_r = None
        hab_outer_r = None
        for i in range(num_planets):
            zone = self._classify_planet_zone(i, num_planets)
            r = orbit_radii[i] if i < len(orbit_radii) else max_radius * 0.5
            if zone == "habitable":
                if hab_inner_r is None:
                    hab_inner_r = r
                hab_outer_r = r

        with self.canvas:
            # ============================================================
            # Layer 1: Background zones (drawn first, behind everything)
            # ============================================================

            # -- Stellar gravity well (radial gradient around star) --
            gw_r = max_radius * 0.22 * self._scale
            for step in range(5, 0, -1):
                alpha = 0.025 * step
                r = gw_r * (step / 5.0)
                Color(1, 0.9, 0.5, alpha)
                Ellipse(
                    pos=(ring_cx - r, ring_cy - r),
                    size=(r * 2, r * 2),
                )

            # -- Habitable zone band (subtle green ring) --
            if hab_inner_r is not None and hab_outer_r is not None:
                hz_inner = (hab_inner_r - max_radius * 0.06) * self._scale
                hz_outer = (hab_outer_r + max_radius * 0.06) * self._scale
                # Draw as concentric filled rings
                Color(0.15, 0.45, 0.2, 0.08)
                Ellipse(
                    pos=(ring_cx - hz_outer, ring_cy - hz_outer),
                    size=(hz_outer * 2, hz_outer * 2),
                )
                # Punch out the inner part with background colour
                Color(0.02, 0.03, 0.08, 1)
                Ellipse(
                    pos=(ring_cx - hz_inner, ring_cy - hz_inner),
                    size=(hz_inner * 2, hz_inner * 2),
                )
                # Dashed boundary lines for the zone
                Color(0.2, 0.55, 0.25, 0.2)
                Line(
                    circle=(ring_cx, ring_cy, hz_inner),
                    width=0.7,
                    dash_length=dp(4),
                    dash_offset=dp(4),
                )
                Line(
                    circle=(ring_cx, ring_cy, hz_outer),
                    width=0.7,
                    dash_length=dp(4),
                    dash_offset=dp(4),
                )

            # -- Frost line indicator (dashed ring at ~60% of max radius) --
            frost_r = max_radius * 0.58 * self._scale
            Color(0.3, 0.5, 0.8, 0.12)
            Line(
                circle=(ring_cx, ring_cy, frost_r),
                width=0.6,
                dash_length=dp(6),
                dash_offset=dp(3),
            )

            # ============================================================
            # Layer 2: Stars
            # ============================================================
            stars = system.stars if system.stars else [{"name": system.name}]
            star_orbit_r = dp(20) if len(stars) > 1 else 0
            star_sizes = [dp(36), dp(26), dp(20)]

            for i, star in enumerate(stars):
                angle = (i * (360 / max(1, len(stars)))) * math.pi / 180
                sx_base = cx_base + star_orbit_r * math.cos(angle)
                sy_base = cy_base + star_orbit_r * math.sin(angle)
                sx, sy = self._apply_transform(sx_base, sy_base)

                spectral = str(star.get("spectral", "G")).upper()
                color = star.get("color",
                                 SPECTRAL_COLORS.get(spectral[:1], (1, 0.9, 0.3, 1)))
                raw_size = star.get("size")
                size = dp(raw_size) if raw_size is not None else star_sizes[min(i, len(star_sizes) - 1)]
                size *= self._scale

                _draw_star_icon(self.canvas, sx, sy, size, color)

            # ============================================================
            # Layer 3: Orbital rings + Planets
            # ============================================================
            planet_positions = {}  # planet.id -> (px, py) base coords

            for i, planet in enumerate(system.planets):
                orbit_r = orbit_radii[i]
                orbit_r_scaled = orbit_r * self._scale

                # Orbital ring (lighter in habitable zone)
                zone = self._classify_planet_zone(i, num_planets)
                if zone == "habitable":
                    Color(0.25, 0.4, 0.35, 0.3)
                else:
                    Color(0.2, 0.3, 0.4, 0.2)
                Line(circle=(ring_cx, ring_cy, orbit_r_scaled), width=0.8)

                # Planet position — spread using golden angle for nice distribution
                angle = (i * 137.508 + 30) * math.pi / 180
                px_base = cx_base + orbit_r * math.cos(angle)
                py_base = cy_base + orbit_r * math.sin(angle)
                px, py = self._apply_transform(px_base, py_base)
                planet_positions[planet.id] = (px_base, py_base)

                color = BODY_TYPE_COLORS.get(planet.type, (0.5, 0.5, 0.5, 1))
                is_gas = planet.type == "gas_giant"
                is_asteroid = "asteroid" in planet.type.lower()
                has_atmo = planet.type in ("oceanic", "garden", "toxic", "gas_giant")

                # Gas giants get a subtle gravity well of their own
                if is_gas and is_surveyed:
                    gj_well_r = dp(22) * self._scale
                    for step in range(3, 0, -1):
                        ga = 0.02 * step
                        gr = gj_well_r * (step / 3.0)
                        Color(color[0], color[1], color[2], ga)
                        Ellipse(
                            pos=(px - gr, py - gr),
                            size=(gr * 2, gr * 2),
                        )

                if not is_surveyed:
                    silhouette = (0.15, 0.18, 0.25, 0.85)
                    if is_asteroid:
                        p_size = dp(20) * self._scale
                        _draw_asteroid_icon(self.canvas, px, py, p_size, color=silhouette)
                    elif is_gas:
                        p_size = dp(28) * self._scale
                        _draw_planet_icon(self.canvas, px, py, p_size, silhouette, has_atmosphere=False)
                    else:
                        p_size = dp(18) * self._scale
                        _draw_planet_icon(self.canvas, px, py, p_size, silhouette,
                                          has_atmosphere=False)
                else:
                    if is_asteroid:
                        p_size = dp(20) * self._scale
                        _draw_asteroid_icon(self.canvas, px, py, p_size)
                    elif is_gas:
                        p_size = dp(28) * self._scale
                        _draw_planet_icon(self.canvas, px, py, p_size, color, has_atmosphere=True)
                        # Ring for gas giants
                        Color(color[0], color[1], color[2], 0.3)
                        Line(
                            ellipse=(px - p_size * 0.9, py - p_size * 0.2,
                                     p_size * 1.8, p_size * 0.4),
                            width=1,
                        )
                    else:
                        p_size = dp(18) * self._scale
                        _draw_planet_icon(self.canvas, px, py, p_size, color,
                                          has_atmosphere=has_atmo)

                self._body_positions[planet.id] = (px, py, p_size)

                # Selection highlight
                if planet.id == self.selected_body_id:
                    pulse = 0.5 + 0.5 * math.sin(self._pulse_t)
                    glow_alpha = 0.2 + 0.4 * pulse
                    sel_r = p_size * (0.9 + 0.2 * pulse)
                    Color(0.7, 0.9, 1.0, glow_alpha)
                    Line(circle=(px, py, sel_r), width=1.4)

                # Colony indicator
                if self.system_id in self.game_state.colonies.colonies:
                    colony = self.game_state.colonies.colonies[self.system_id]
                    if colony.planet_id == planet.id:
                        pulse = math.sin(self._pulse_t) * 0.05
                        Color(1, 1, 0.3, 0.85 + pulse)
                        c_s = dp(7) * self._scale
                        Ellipse(pos=(px - c_s / 2, py + p_size * 0.5),
                                size=(c_s, c_s))

            # ============================================================
            # Layer 4: Gate indicator (edge of system)
            # ============================================================
            gate_x, gate_y = self._apply_transform(
                cx_base + max_radius * 0.95,
                cy_base + max_radius * 0.95,
            )
            gate_anchor = (gate_x, gate_y)
            gate_size = dp(14) * self._scale
            if system.gate_active:
                # Subtle gate field glow
                Color(0.2, 0.7, 0.8, 0.08)
                gf_r = dp(24) * self._scale
                Ellipse(
                    pos=(gate_x - gf_r, gate_y - gf_r),
                    size=(gf_r * 2, gf_r * 2),
                )
                _draw_station_icon(self.canvas, gate_x, gate_y, gate_size,
                                   color=(0.2, 0.8, 0.9, 0.9))
            else:
                _draw_station_icon(self.canvas, gate_x, gate_y, gate_size,
                                   color=(0.9, 0.4, 0.2, 0.7))
            self._body_positions["__gate__"] = (gate_x, gate_y, gate_size)

            # ============================================================
            # Layer 5: Ships — positioned near their context
            # ============================================================
            ships = self.game_state.fleet.get_ships_at(self.system_id)
            class_colors = {
                "scout": (0.3, 1, 0.7, 0.9),
                "freighter": (1, 0.8, 0.2, 0.9),
                "miner": (0.8, 0.5, 0.2, 0.9),
                "corvette": (1, 0.3, 0.3, 0.9),
            }

            # Group ships by context: mining ships near colony planet,
            # travelling ships near the gate, idle ships orbit the star.
            gate_ships = []
            orbit_ships = []
            colony_planet_id = None
            if self.system_id in self.game_state.colonies.colonies:
                colony_planet_id = self.game_state.colonies.colonies[self.system_id].planet_id

            for ship in ships:
                if ship.path or ship.destination:
                    gate_ships.append(ship)
                elif ship.mining and colony_planet_id and colony_planet_id in planet_positions:
                    orbit_ships.append((ship, colony_planet_id))
                elif colony_planet_id and colony_planet_id in planet_positions:
                    orbit_ships.append((ship, colony_planet_id))
                else:
                    gate_ships.append(ship)

            # Draw ships near gate
            for idx, ship in enumerate(gate_ships):
                # Fan out around the gate in a small arc
                spread_angle = (idx - len(gate_ships) / 2.0) * 25 * math.pi / 180
                offset_r = dp(28 + idx * 6)
                gx_base = cx_base + max_radius * 0.95 - offset_r * math.cos(
                    math.pi / 4 + spread_angle)
                gy_base = cy_base + max_radius * 0.95 - offset_r * math.sin(
                    math.pi / 4 + spread_angle)
                sx, sy = self._apply_transform(gx_base, gy_base)
                self._draw_ship(ship, sx, sy, gate_anchor, class_colors)

            # Draw ships orbiting a body
            for idx, (ship, body_id) in enumerate(orbit_ships):
                bx_base, by_base = planet_positions[body_id]
                # Small orbit around the planet
                orbit_angle = (idx * 90 + 45) * math.pi / 180
                offset_r = dp(20 + idx * 5)
                ox_base = bx_base + offset_r * math.cos(orbit_angle)
                oy_base = by_base + offset_r * math.sin(orbit_angle)
                sx, sy = self._apply_transform(ox_base, oy_base)
                self._draw_ship(ship, sx, sy, gate_anchor, class_colors)

    def _draw_ship(self, ship, sx, sy, gate_anchor, class_colors):
        """Draw a single ship icon at screen position (sx, sy)."""
        s_size = dp(12) * self._scale
        scolor = class_colors.get(ship.ship_class, (0.7, 0.7, 0.7, 0.9))

        with self.canvas:
            # Travel path line to gate
            if ship.path:
                is_selected = ship.id == self.selected_ship_id
                if is_selected:
                    Color(0.4, 0.8, 1.0, 0.55)
                    width = 1.5
                    dash_length = dp(6)
                else:
                    Color(0.35, 0.65, 0.9, 0.35)
                    width = 1.1
                    dash_length = dp(4)
                Line(
                    points=[sx, sy, gate_anchor[0], gate_anchor[1]],
                    width=width,
                    dash_length=dash_length,
                    dash_offset=self._dash_offset,
                )

            # Selection ring
            if ship.id == self.selected_ship_id:
                pulse = 0.5 + 0.5 * math.sin(self._pulse_t * 1.4)
                ring_alpha = 0.35 + 0.45 * pulse
                ring_radius = s_size * (1.1 + 0.25 * pulse)
                Color(0.9, 0.95, 1.0, ring_alpha)
                Line(circle=(sx, sy, ring_radius), width=1.2)
                scolor = (
                    min(1.0, scolor[0] + 0.15 * pulse),
                    min(1.0, scolor[1] + 0.15 * pulse),
                    min(1.0, scolor[2] + 0.15 * pulse),
                    min(1.0, scolor[3] + 0.2 * pulse),
                )

            Color(*scolor)
            # Diamond shape for ships
            half = s_size * 0.6
            Line(
                points=[sx, sy + half, sx + half, sy,
                        sx, sy - half, sx - half, sy, sx, sy + half],
                width=1.3,
            )
        self._ship_positions[ship.id] = (sx, sy)

    def _handle_tap(self, touch):
        # Check ship taps first
        for ship_id, (sx, sy) in self._ship_positions.items():
            dist = ((touch.x - sx) ** 2 + (touch.y - sy) ** 2) ** 0.5
            if dist < dp(22):
                self.selected_ship_id = ship_id
                self.selected_body_id = None
                self._redraw()
                if self.on_ship_tap:
                    self.on_ship_tap(ship_id)
                return True

        # Check body taps
        for body_id, (bx, by, bsize) in self._body_positions.items():
            dist = ((touch.x - bx) ** 2 + (touch.y - by) ** 2) ** 0.5
            if dist < max(dp(24), bsize):
                self.selected_body_id = body_id
                self.selected_ship_id = None
                self._redraw()
                if self.on_body_tap:
                    self.on_body_tap(body_id)
                return True

        # Deselect
        self.selected_body_id = None
        self.selected_ship_id = None
        self._redraw()
        return True


# ======================================================================
# Body Detail Widget (Level 2/3)
# ======================================================================

class BodyDetailWidget(MapCameraWidget):
    """Renders a single planet/body with surface detail view."""

    def __init__(self, game_state=None, system_id=None, body_id=None,
                 on_region_tap=None, **kwargs):
        super().__init__(**kwargs)
        self.game_state = game_state
        self.system_id = system_id
        self.body_id = body_id
        self.on_region_tap = on_region_tap
        self._min_scale = 0.5
        self._max_scale = 3.0
        self._pulse_t = 0.0
        Clock.schedule_interval(self._tick, 1 / 30)
        self.bind(size=self._redraw, pos=self._redraw)

    def _tick(self, dt):
        self._pulse_t += dt * 1.5
        self._redraw()

    def set_data(self, game_state, system_id, body_id):
        self.game_state = game_state
        self.system_id = system_id
        self.body_id = body_id
        self.reset_camera()

    def _redraw(self, *args):
        self.canvas.clear()
        if not self.game_state or not self.system_id or not self.body_id:
            return

        system = self.game_state.galaxy.systems.get(self.system_id)
        if not system:
            return

        planet = None
        for p in system.planets:
            if p.id == self.body_id:
                planet = p
                break
        if not planet:
            return

        cx_base = self.center_x
        cy_base = self.center_y
        cx, cy = self._apply_transform(cx_base, cy_base)

        color = BODY_TYPE_COLORS.get(planet.type, (0.5, 0.5, 0.5, 1))
        is_asteroid = "asteroid" in planet.type.lower()
        is_surveyed = bool(system.surveyed)

        with self.canvas:
            if not is_surveyed:
                silhouette = (0.15, 0.18, 0.25, 0.85)
                if is_asteroid:
                    body_size = dp(80) * self._scale
                    _draw_asteroid_icon(self.canvas, cx, cy, body_size, color=silhouette)
                else:
                    body_size = dp(100) * self._scale
                    _draw_planet_icon(self.canvas, cx, cy, body_size, silhouette,
                                      has_atmosphere=False)
                return
            if is_asteroid:
                body_size = dp(80) * self._scale
                _draw_asteroid_icon(self.canvas, cx, cy, body_size)
            else:
                body_size = dp(100) * self._scale
                has_atmo = planet.type in ("oceanic", "garden", "toxic", "gas_giant")
                _draw_planet_icon(self.canvas, cx, cy, body_size, color,
                                  has_atmosphere=has_atmo)

                if planet.type == "gas_giant":
                    # Draw ring
                    Color(color[0], color[1], color[2], 0.3)
                    Line(
                        ellipse=(cx - body_size * 0.9, cy - body_size * 0.15,
                                 body_size * 1.8, body_size * 0.3),
                        width=1.2,
                    )

                # Surface grid for colonised bodies
                colony = self.game_state.colonies.colonies.get(self.system_id)
                if colony and colony.planet_id == planet.id:
                    self._draw_colony_overlay(cx, cy, body_size, colony)

            # Resource indicators around the body
            if planet.resources:
                self._draw_resource_ring(cx, cy, body_size, planet.resources)

    def _draw_colony_overlay(self, cx, cy, size, colony):
        """Draw colony indicator and infrastructure ring."""
        pulse = math.sin(self._pulse_t) * 0.05
        Color(1, 1, 0.3, 0.6 + pulse)
        col_size = size * 0.15
        Ellipse(pos=(cx - col_size / 2, cy + size * 0.35),
                size=(col_size, col_size))

        # Infrastructure arcs
        infra_colors = {
            "housing": (0.3, 0.8, 0.3, 0.6),
            "industry": (0.8, 0.6, 0.2, 0.6),
            "defense": (0.8, 0.3, 0.3, 0.6),
            "research": (0.3, 0.5, 0.9, 0.6),
            "spaceport": (0.3, 0.8, 0.8, 0.6),
        }
        ring_r = size * 0.65
        angle_step = 360 / max(1, len(infra_colors))
        for i, (infra_type, icolor) in enumerate(infra_colors.items()):
            level = colony.infrastructure.get(infra_type, {}).get("level", 0)
            if level <= 0:
                continue
            start_angle = i * angle_step
            sweep = angle_step * 0.8 * min(1.0, level / 5.0)
            Color(*icolor)
            Line(
                ellipse=(cx - ring_r, cy - ring_r, ring_r * 2, ring_r * 2,
                         start_angle, start_angle + sweep),
                width=dp(3) * self._scale,
            )

    def _draw_resource_ring(self, cx, cy, size, resources):
        """Draw small resource indicators around the body."""
        res_colors = {
            "energy": (1, 0.9, 0.2, 0.8),
            "metals": (0.6, 0.6, 0.7, 0.8),
            "exotics": (0.8, 0.4, 1, 0.8),
            "credits": (0.3, 0.8, 0.3, 0.8),
            "intel": (0.3, 0.6, 1, 0.8),
            "food": (0.4, 0.8, 0.4, 0.8),
            "fuel": (0.9, 0.5, 0.2, 0.8),
        }
        valid = [(k, v) for k, v in resources.items() if v > 0]
        if not valid:
            return

        ring_r = size * 0.75
        for i, (res, amount) in enumerate(valid):
            angle = (i * 360 / len(valid) + 90) * math.pi / 180
            rx = cx + ring_r * math.cos(angle)
            ry = cy + ring_r * math.sin(angle)
            rcolor = res_colors.get(res, (0.7, 0.7, 0.7, 0.8))
            Color(*rcolor)
            dot_size = dp(6) * self._scale * min(1.5, 0.5 + amount / 20.0)
            Ellipse(pos=(rx - dot_size / 2, ry - dot_size / 2),
                    size=(dot_size, dot_size))

    def _handle_tap(self, touch):
        if self.on_region_tap:
            self.on_region_tap(self.body_id)
        return True


# ======================================================================
# Mini-map overlay (galaxy context)
# ======================================================================

class MiniMapWidget(Widget):
    """Compact galaxy overview with current system highlighted."""

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.game_state = None
        self.system_id = None
        self.bind(size=self._redraw, pos=self._redraw)

    def set_data(self, game_state, system_id):
        self.game_state = game_state
        self.system_id = system_id
        self._redraw()

    def _redraw(self, *args):
        self.canvas.clear()
        if not self.game_state:
            return

        systems = list(self.game_state.galaxy.systems.values())
        if not systems:
            return

        min_x = min(s.x for s in systems)
        max_x = max(s.x for s in systems)
        min_y = min(s.y for s in systems)
        max_y = max(s.y for s in systems)

        span_x = max(1.0, max_x - min_x)
        span_y = max(1.0, max_y - min_y)
        pad = dp(6)
        width = max(1.0, self.width - pad * 2)
        height = max(1.0, self.height - pad * 2)

        with self.canvas:
            Color(0.03, 0.05, 0.1, 0.9)
            Rectangle(pos=self.pos, size=self.size)

            for system in systems:
                nx = (system.x - min_x) / span_x
                ny = (system.y - min_y) / span_y
                sx = self.x + pad + nx * width
                sy = self.y + pad + ny * height

                if system.id == self.system_id:
                    Color(0.3, 0.9, 1, 1)
                    Ellipse(pos=(sx - dp(4), sy - dp(4)), size=(dp(8), dp(8)))
                    Color(0.3, 0.9, 1, 0.5)
                    Ellipse(pos=(sx - dp(7), sy - dp(7)), size=(dp(14), dp(14)))
                else:
                    if system.discovered:
                        Color(0.6, 0.8, 1, 0.8)
                    else:
                        Color(0.2, 0.3, 0.4, 0.6)
                    Ellipse(pos=(sx - dp(2), sy - dp(2)), size=(dp(4), dp(4)))


class PlanetComparisonPopup(Popup):
    """Popup showing side-by-side planet comparison."""

    def __init__(self, comparison_data: list[dict], **kwargs):
        content = BoxLayout(orientation="vertical", spacing=dp(8), padding=dp(8))

        header = Label(
            text="Planet Comparison",
            font_size="16sp",
            bold=True,
            color=(0.3, 0.85, 1, 1),
            size_hint_y=None,
            height=dp(28),
        )
        content.add_widget(header)

        grid = GridLayout(
            cols=max(1, len(comparison_data)),
            spacing=dp(8),
            size_hint_y=None,
        )
        grid.bind(minimum_height=grid.setter("height"))

        for body in comparison_data:
            col = BoxLayout(
                orientation="vertical",
                size_hint_y=None,
                spacing=dp(4),
                padding=[dp(6), dp(6), dp(6), dp(6)],
            )
            col.bind(minimum_height=col.setter("height"))
            with col.canvas.before:
                Color(0.05, 0.08, 0.15, 0.9)
                bg = Rectangle(pos=col.pos, size=col.size)
            col.bind(
                pos=lambda w, v, b=bg: setattr(b, "pos", v),
                size=lambda w, v, b=bg: setattr(b, "size", v),
            )

            col.add_widget(Label(
                text=body.get("name", "Unknown"),
                font_size="13sp",
                bold=True,
                color=(0.7, 0.9, 1, 0.95),
                size_hint_y=None,
                height=dp(22),
            ))
            col.add_widget(Label(
                text=f"Type: {body.get('type', 'unknown').replace('_', ' ').title()}",
                font_size="11sp",
                color=(0.7, 0.85, 1, 0.9),
                size_hint_y=None,
                height=dp(18),
            ))
            col.add_widget(Label(
                text=f"Habitability: {body.get('habitability', 0):.0%}",
                font_size="11sp",
                color=(0.7, 0.85, 1, 0.9),
                size_hint_y=None,
                height=dp(18),
            ))
            col.add_widget(Label(
                text=f"Gravity: {body.get('gravity', 0):.1f}g",
                font_size="11sp",
                color=(0.7, 0.85, 1, 0.9),
                size_hint_y=None,
                height=dp(18),
            ))

            traits = body.get("traits") or []
            traits_text = ", ".join(traits) if traits else "None"
            col.add_widget(Label(
                text=f"Traits: {traits_text}",
                font_size="10sp",
                color=(0.6, 0.8, 1, 0.85),
                size_hint_y=None,
                height=dp(18),
            ))

            resources = body.get("resources") or {}
            if resources:
                for resource, amount in resources.items():
                    col.add_widget(Label(
                        text=f"{resource}: {amount}",
                        font_size="10sp",
                        color=(0.6, 0.8, 1, 0.85),
                        size_hint_y=None,
                        height=dp(16),
                    ))
            else:
                col.add_widget(Label(
                    text="Resources: None",
                    font_size="10sp",
                    color=(0.6, 0.8, 1, 0.85),
                    size_hint_y=None,
                    height=dp(16),
                ))

            grid.add_widget(col)

        scroll = ScrollView(size_hint=(1, 1))
        scroll.add_widget(grid)
        content.add_widget(scroll)

        close_btn = Button(
            text="Close",
            size_hint_y=None,
            height=dp(40),
            font_size="12sp",
            background_color=(0.12, 0.2, 0.35, 0.8),
            color=(0.7, 0.85, 1, 1),
        )
        close_btn.bind(on_release=lambda *_: self.dismiss())
        content.add_widget(close_btn)

        super().__init__(
            title="Planet Comparison",
            content=content,
            size_hint=(0.9, 0.85),
            auto_dismiss=True,
            **kwargs,
        )


# ======================================================================
# Gravity Well Screen — the container with breadcrumb + level switching
# ======================================================================

class GravityWellScreen(Screen):
    """Three-level hierarchical map view for a single star system.

    Levels:
      1 — System (star + all bodies)
      2 — Body detail (single planet/moon/asteroid)
    """

    # Breadcrumb level constants
    LEVEL_SYSTEM = 1
    LEVEL_BODY = 2
    AUTO_SWITCH_ZOOM_IN = 2.5
    AUTO_SWITCH_ZOOM_OUT = 0.5
    AUTO_SWITCH_DEBOUNCE_S = 0.35

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.name = "gravity_well"
        self.game_state = None
        self.system_id = None
        self._current_level = self.LEVEL_SYSTEM
        self._selected_body_id = None
        self._comparison_selection = []
        self._comparison_button = None
        self._last_auto_switch = 0.0
        self._build_ui()

    def _build_ui(self):
        root = FloatLayout()

        with root.canvas.before:
            Color(0.02, 0.03, 0.08, 1)
            self._bg = Rectangle(pos=root.pos, size=root.size)
        root.bind(
            size=lambda w, v: setattr(self._bg, "size", v),
            pos=lambda w, v: setattr(self._bg, "pos", v),
        )

        main_v = BoxLayout(orientation="vertical", size_hint=(1, 1))

        # Top bar (resources)
        self.top_bar = TopBar()
        main_v.add_widget(self.top_bar)

        # Breadcrumb bar
        self.breadcrumb_bar = BoxLayout(
            orientation="horizontal",
            size_hint_y=None,
            height=dp(32),
            padding=[dp(8), dp(2)],
            spacing=dp(4),
        )
        with self.breadcrumb_bar.canvas.before:
            Color(0.05, 0.08, 0.15, 0.9)
            self._bc_bg = Rectangle(
                pos=self.breadcrumb_bar.pos,
                size=self.breadcrumb_bar.size,
            )
        self.breadcrumb_bar.bind(
            size=lambda w, v: setattr(self._bc_bg, "size", v),
            pos=lambda w, v: setattr(self._bc_bg, "pos", v),
        )
        main_v.add_widget(self.breadcrumb_bar)

        # Middle: map + side info panel
        middle = BoxLayout(orientation="horizontal", size_hint=(1, 1))

        # Map container (swaps between system and body widgets)
        self.map_container = FloatLayout(size_hint=(0.65, 1))
        middle.add_widget(self.map_container)

        # Info panel
        self.info_scroll = ScrollView(size_hint=(0.35, 1))
        self.info_panel = BoxLayout(
            orientation="vertical",
            spacing=dp(4),
            padding=dp(8),
            size_hint_y=None,
        )
        self.info_panel.bind(minimum_height=self.info_panel.setter("height"))
        with self.info_panel.canvas.before:
            Color(0.04, 0.06, 0.12, 0.95)
            self._ip_bg = Rectangle(
                pos=self.info_panel.pos,
                size=self.info_panel.size,
            )
        self.info_panel.bind(
            size=lambda w, v: setattr(self._ip_bg, "size", v),
            pos=lambda w, v: setattr(self._ip_bg, "pos", v),
        )
        self.info_scroll.add_widget(self.info_panel)
        middle.add_widget(self.info_scroll)

        main_v.add_widget(middle)

        # Legend bar at bottom
        legend = self._build_legend()
        main_v.add_widget(legend)

        root.add_widget(main_v)
        self.add_widget(root)

        # Create map widgets (lazy init)
        self.system_map = SystemMapWidget(
            on_body_tap=self._on_body_tap,
            on_ship_tap=self._on_ship_tap,
            on_back=self._go_to_galaxy,
            on_view_change=self._on_system_view_change,
        )
        self.mini_map = MiniMapWidget(
            size_hint=(None, None),
            size=(dp(160), dp(120)),
            pos_hint={"x": 0.02, "y": 0.02},
        )
        self.body_detail = BodyDetailWidget(
            on_region_tap=self._on_region_tap,
            on_back=self._switch_to_system_level,
            on_view_change=self._on_body_view_change,
        )

    def _build_legend(self):
        """Build a compact icon legend bar."""
        bar = BoxLayout(
            orientation="horizontal",
            size_hint_y=None,
            height=dp(28),
            padding=[dp(8), dp(2)],
            spacing=dp(12),
        )
        with bar.canvas.before:
            Color(0.04, 0.06, 0.12, 0.8)
            bar_bg = Rectangle(pos=bar.pos, size=bar.size)
        bar.bind(
            size=lambda w, v: setattr(bar_bg, "size", v),
            pos=lambda w, v: setattr(bar_bg, "pos", v),
        )

        legend_items = [
            ("Star", (1, 0.9, 0.3, 1)),
            ("Planet", (0.6, 0.5, 0.3, 1)),
            ("Gas Giant", (0.8, 0.6, 0.2, 1)),
            ("Asteroid", (0.55, 0.45, 0.35, 1)),
            ("Gate", (0.3, 0.85, 0.9, 1)),
            ("Colony", (1, 1, 0.3, 1)),
            ("Hab Zone", (0.2, 0.55, 0.25, 0.6)),
            ("Frost Line", (0.3, 0.5, 0.8, 0.5)),
        ]
        for label_text, color in legend_items:
            item = BoxLayout(orientation="horizontal", size_hint_x=None, width=dp(90))
            # Dot
            dot_widget = Widget(size_hint=(None, None), size=(dp(10), dp(10)))
            with dot_widget.canvas:
                Color(*color)
                Ellipse(pos=dot_widget.pos, size=dot_widget.size)
            dot_widget.bind(pos=lambda w, v: w.canvas.clear() or None)
            item.add_widget(dot_widget)
            item.add_widget(Label(
                text=label_text,
                font_size="9sp",
                color=(0.6, 0.75, 0.9, 0.8),
                halign="left",
                size_hint_x=None,
                width=dp(76),
            ))
            bar.add_widget(item)

        bar.add_widget(Widget())  # Spacer
        return bar

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def set_system(self, game_state, system_id):
        """Enter this screen showing a specific system."""
        self.game_state = game_state
        self.system_id = system_id
        self._current_level = self.LEVEL_SYSTEM
        self._selected_body_id = None
        self._comparison_selection = []
        self.top_bar.update(game_state)
        self.mini_map.set_data(game_state, system_id)
        self._switch_to_system_level()

    def set_game_state(self, game_state):
        """Refresh with updated game state."""
        self.game_state = game_state
        self.top_bar.update(game_state)
        if self._current_level == self.LEVEL_SYSTEM:
            self.system_map.game_state = game_state
            self.system_map._redraw()
            self.mini_map.set_data(game_state, self.system_id)
        elif self._current_level == self.LEVEL_BODY:
            self.body_detail.game_state = game_state
            self.body_detail._redraw()
        self._update_info_panel()

    # ------------------------------------------------------------------
    # Level switching
    # ------------------------------------------------------------------

    def _switch_to_system_level(self):
        self._current_level = self.LEVEL_SYSTEM
        self.map_container.clear_widgets()
        self.system_map.set_data(self.game_state, self.system_id)
        self.system_map.size_hint = (1, 1)
        self.map_container.add_widget(self.system_map)
        self.mini_map.set_data(self.game_state, self.system_id)
        self.map_container.add_widget(self.mini_map)
        self._update_breadcrumb()
        self._update_info_panel()

    def _switch_to_body_level(self, body_id):
        self._current_level = self.LEVEL_BODY
        self._selected_body_id = body_id
        self.map_container.clear_widgets()
        self.body_detail.set_data(self.game_state, self.system_id, body_id)
        self.body_detail.size_hint = (1, 1)
        self.map_container.add_widget(self.body_detail)
        self._update_breadcrumb()
        self._update_info_panel()

    def _can_auto_switch(self) -> bool:
        now = time.monotonic()
        if now - self._last_auto_switch < self.AUTO_SWITCH_DEBOUNCE_S:
            return False
        self._last_auto_switch = now
        return True

    def _on_system_view_change(self):
        if self._current_level != self.LEVEL_SYSTEM or not self.game_state or not self.system_id:
            return
        system = self.game_state.galaxy.systems.get(self.system_id)
        if not system or not system.surveyed:
            return
        if self.system_map._scale >= self.AUTO_SWITCH_ZOOM_IN and self._selected_body_id:
            if self._can_auto_switch():
                self._switch_to_body_level(self._selected_body_id)

    def _on_body_view_change(self):
        if self._current_level != self.LEVEL_BODY:
            return
        if self.body_detail._scale <= self.AUTO_SWITCH_ZOOM_OUT:
            if self._can_auto_switch():
                self._switch_to_system_level()

    # ------------------------------------------------------------------
    # Breadcrumb
    # ------------------------------------------------------------------

    def _update_breadcrumb(self):
        self.breadcrumb_bar.clear_widgets()

        system = self.game_state.galaxy.systems.get(self.system_id) if self.game_state else None
        system_name = system.name if system else "Unknown"

        # Back to Galaxy
        galaxy_btn = Button(
            text="< Galaxy",
            size_hint=(None, 1),
            width=dp(80),
            font_size="11sp",
            background_color=(0.08, 0.15, 0.25, 0.8),
            color=(0.7, 0.85, 1, 1),
        )
        galaxy_btn.bind(on_release=self._go_to_galaxy)
        self.breadcrumb_bar.add_widget(galaxy_btn)

        sep1 = Label(text="/", font_size="11sp", color=(0.4, 0.5, 0.6, 0.7),
                      size_hint=(None, 1), width=dp(14))
        self.breadcrumb_bar.add_widget(sep1)

        if self._current_level == self.LEVEL_SYSTEM:
            # Current: system name (not clickable)
            self.breadcrumb_bar.add_widget(Label(
                text=system_name,
                font_size="12sp",
                bold=True,
                color=(0.3, 0.85, 1, 1),
                size_hint=(None, 1),
                width=dp(140),
                halign="left",
                text_size=(dp(140), None),
            ))
        elif self._current_level == self.LEVEL_BODY:
            # System name — clickable
            sys_btn = Button(
                text=system_name,
                size_hint=(None, 1),
                width=dp(100),
                font_size="11sp",
                background_color=(0.08, 0.15, 0.25, 0.8),
                color=(0.7, 0.85, 1, 1),
            )
            sys_btn.bind(on_release=lambda b: self._switch_to_system_level())
            self.breadcrumb_bar.add_widget(sys_btn)

            sep2 = Label(text="/", font_size="11sp", color=(0.4, 0.5, 0.6, 0.7),
                          size_hint=(None, 1), width=dp(14))
            self.breadcrumb_bar.add_widget(sep2)

            # Body name
            body_name = self._get_body_name(self._selected_body_id)
            self.breadcrumb_bar.add_widget(Label(
                text=body_name,
                font_size="12sp",
                bold=True,
                color=(0.3, 0.85, 1, 1),
                size_hint=(None, 1),
                width=dp(140),
                halign="left",
                text_size=(dp(140), None),
            ))

        # Level indicator + reset button
        level_names = {
            self.LEVEL_SYSTEM: "System View",
            self.LEVEL_BODY: "Body Detail",
        }
        self.breadcrumb_bar.add_widget(Widget())  # Spacer
        self.breadcrumb_bar.add_widget(Label(
            text=level_names.get(self._current_level, ""),
            font_size="10sp",
            color=(0.5, 0.6, 0.7, 0.7),
            size_hint=(None, 1),
            width=dp(90),
            halign="right",
            text_size=(dp(90), None),
        ))

        # Camera reset button
        reset_btn = Button(
            text="Reset View",
            size_hint=(None, 1),
            width=dp(70),
            font_size="10sp",
            background_color=(0.1, 0.2, 0.3, 0.7),
            color=(0.5, 0.8, 1, 0.8),
        )
        reset_btn.bind(on_release=self._reset_camera)
        self.breadcrumb_bar.add_widget(reset_btn)

    def _get_body_name(self, body_id):
        if not self.game_state or not self.system_id:
            return body_id or ""
        system = self.game_state.galaxy.systems.get(self.system_id)
        if not system:
            return body_id or ""
        for p in system.planets:
            if p.id == body_id:
                return p.name
        return body_id or ""

    # ------------------------------------------------------------------
    # Info panel
    # ------------------------------------------------------------------

    def _update_info_panel(self):
        self.info_panel.clear_widgets()
        if not self.game_state or not self.system_id:
            return

        system = self.game_state.galaxy.systems.get(self.system_id)
        if not system:
            return

        if self._current_level == self.LEVEL_SYSTEM:
            self._build_system_info(system)
        elif self._current_level == self.LEVEL_BODY:
            self._build_body_info(system, self._selected_body_id)

    def _build_system_info(self, system):
        """Build info panel for system level."""
        valid_body_ids = {planet.id for planet in system.planets}
        self._comparison_selection = [
            body_id for body_id in self._comparison_selection if body_id in valid_body_ids
        ]
        system_surveyed = bool(system.surveyed)
        self.info_panel.add_widget(Label(
            text=system.name,
            font_size="16sp",
            bold=True,
            color=(0.3, 0.85, 1, 1),
            size_hint_y=None,
            height=dp(32),
        ))

        tier_names = {1: "Core World", 2: "Developing", 3: "Frontier"}
        self.info_panel.add_widget(Label(
            text=f"Tier {system.tier} - {tier_names.get(system.tier, 'Unknown')}",
            font_size="12sp",
            color=(0.5, 0.7, 0.9, 0.8),
            size_hint_y=None,
            height=dp(22),
        ))

        # Gate status
        gate_text = "Gate: Active" if system.gate_active else "Gate: Dormant"
        self.info_panel.add_widget(Label(
            text=gate_text,
            font_size="11sp",
            color=(0.15, 0.6, 0.8, 1) if system.gate_active else (1, 0.4, 0.2, 1),
            size_hint_y=None,
            height=dp(22),
            halign="left",
            text_size=(dp(240), None),
        ))

        # Planets list
        self.info_panel.add_widget(Label(
            text=f"Bodies ({len(system.planets)}):",
            font_size="12sp",
            bold=True,
            color=(0.6, 0.8, 1, 1),
            size_hint_y=None,
            height=dp(24),
            halign="left",
            text_size=(dp(240), None),
        ))
        if not system_surveyed:
            self.info_panel.add_widget(Label(
                text="Survey required to reveal body details.",
                font_size="10sp",
                color=(0.7, 0.75, 0.9, 0.85),
                size_hint_y=None,
                height=dp(18),
                halign="left",
                text_size=(dp(240), None),
            ))

        for planet in system.planets:
            type_icon = self._body_type_icon(planet.type)
            display_name = planet.name if system_surveyed else "Unknown Body"
            display_type = planet.type if system_surveyed else "unknown"
            col_tag = " [colonizable]" if system_surveyed and planet.colonizable else ""
            row = BoxLayout(
                orientation="horizontal",
                size_hint_y=None,
                height=dp(30),
                spacing=dp(4),
            )
            compare_btn = ToggleButton(
                text="Compare",
                size_hint_x=None,
                width=dp(72),
                font_size="10sp",
                background_color=(0.1, 0.18, 0.3, 0.7),
                color=(0.7, 0.85, 1, 0.9),
            )
            compare_btn.body_id = planet.id
            compare_btn.state = "down" if planet.id in self._comparison_selection else "normal"
            compare_btn.disabled = not system_surveyed
            compare_btn.bind(on_release=self._on_compare_toggle)
            row.add_widget(compare_btn)

            view_btn = Button(
                text=f"{type_icon} {display_name} ({display_type}){col_tag}",
                size_hint_y=None,
                height=dp(30),
                font_size="11sp",
                background_color=(0.08, 0.15, 0.25, 0.6),
                color=(0.75, 0.88, 1, 0.9),
                halign="left",
            )
            view_btn.body_id = planet.id
            view_btn.disabled = not system_surveyed
            view_btn.bind(on_release=lambda b: self._switch_to_body_level(b.body_id))
            row.add_widget(view_btn)
            self.info_panel.add_widget(row)

        self._comparison_button = Button(
            text="Compare Selected (0/3)",
            size_hint_y=None,
            height=dp(32),
            font_size="11sp",
            background_color=(0.12, 0.2, 0.35, 0.8),
            color=(0.7, 0.85, 1, 1),
            disabled=True,
        )
        self._comparison_button.bind(on_release=self._open_comparison_view)
        self.info_panel.add_widget(self._comparison_button)
        self._update_compare_button()

        # Ships at system
        ships = self.game_state.fleet.get_ships_at(self.system_id)
        if ships:
            self.info_panel.add_widget(Label(
                text=f"Ships ({len(ships)}):",
                font_size="12sp",
                bold=True,
                color=(0.6, 0.8, 1, 1),
                size_hint_y=None,
                height=dp(24),
                halign="left",
                text_size=(dp(240), None),
            ))
            for ship in ships:
                self.info_panel.add_widget(Label(
                    text=f"  {ship.name} ({ship.ship_class})",
                    font_size="11sp",
                    color=(0.7, 0.85, 1, 0.9),
                    size_hint_y=None,
                    height=dp(20),
                    halign="left",
                    text_size=(dp(240), None),
                ))

        # Colony
        colony = self.game_state.colonies.colonies.get(self.system_id)
        if colony:
            self.info_panel.add_widget(Label(
                text=f"Colony: {colony.name} (pop: {colony.population})",
                font_size="12sp",
                color=(1, 1, 0.3, 0.9),
                size_hint_y=None,
                height=dp(22),
                halign="left",
                text_size=(dp(240), None),
            ))

        self.info_panel.add_widget(Widget(size_hint_y=None, height=dp(8)))

    def _build_body_info(self, system, body_id):
        """Build info panel for body level."""
        planet = None
        for p in system.planets:
            if p.id == body_id:
                planet = p
                break
        if not planet:
            return
        if not system.surveyed:
            self.info_panel.add_widget(Label(
                text="Survey data unavailable. Complete a survey to reveal details.",
                font_size="11sp",
                color=(0.7, 0.75, 0.9, 0.9),
                size_hint_y=None,
                height=dp(36),
                halign="left",
                text_size=(dp(240), None),
            ))
            self.info_panel.add_widget(Widget(size_hint_y=None, height=dp(8)))
            return

        type_icon = self._body_type_icon(planet.type)
        self.info_panel.add_widget(Label(
            text=f"{type_icon} {planet.name}",
            font_size="16sp",
            bold=True,
            color=(0.3, 0.85, 1, 1),
            size_hint_y=None,
            height=dp(32),
        ))

        self.info_panel.add_widget(Label(
            text=f"Type: {planet.type.replace('_', ' ').title()}",
            font_size="12sp",
            color=(0.5, 0.7, 0.9, 0.8),
            size_hint_y=None,
            height=dp(20),
        ))

        if planet.description:
            self.info_panel.add_widget(Label(
                text=planet.description,
                font_size="10sp",
                color=(0.5, 0.65, 0.8, 0.8),
                size_hint_y=None,
                height=dp(48),
                halign="left",
                text_size=(dp(240), None),
            ))

        # Properties
        self.info_panel.add_widget(Label(
            text=f"Habitability: {planet.habitability:.0%}",
            font_size="11sp",
            color=(0.6, 0.8, 0.6, 0.9),
            size_hint_y=None,
            height=dp(20),
            halign="left",
            text_size=(dp(240), None),
        ))
        self.info_panel.add_widget(Label(
            text=f"Gravity: {planet.gravity:.1f}g",
            font_size="11sp",
            color=(0.6, 0.8, 0.6, 0.9),
            size_hint_y=None,
            height=dp(20),
            halign="left",
            text_size=(dp(240), None),
        ))

        if planet.colonizable:
            self.info_panel.add_widget(Label(
                text="[Colonizable]",
                font_size="11sp",
                bold=True,
                color=(0.3, 1, 0.5, 0.9),
                size_hint_y=None,
                height=dp(20),
            ))

        # Resources
        if planet.resources:
            self.info_panel.add_widget(Label(
                text="Resources:",
                font_size="12sp",
                bold=True,
                color=(0.6, 0.8, 1, 1),
                size_hint_y=None,
                height=dp(22),
                halign="left",
                text_size=(dp(240), None),
            ))
            for res, amount in planet.resources.items():
                if amount > 0:
                    self.info_panel.add_widget(Label(
                        text=f"  {res.title()}: {amount}/turn",
                        font_size="11sp",
                        color=(0.7, 0.85, 1, 0.9),
                        size_hint_y=None,
                        height=dp(18),
                        halign="left",
                        text_size=(dp(240), None),
                    ))

        # Traits
        if planet.traits:
            self.info_panel.add_widget(Label(
                text=f"Traits: {', '.join(planet.traits)}",
                font_size="11sp",
                color=(0.8, 0.7, 0.3, 0.9),
                size_hint_y=None,
                height=dp(20),
                halign="left",
                text_size=(dp(240), None),
            ))

        # Colony info
        colony = self.game_state.colonies.colonies.get(self.system_id)
        if colony and colony.planet_id == planet.id:
            self.info_panel.add_widget(Widget(size_hint_y=None, height=dp(8)))
            self.info_panel.add_widget(Label(
                text=f"Colony: {colony.name}",
                font_size="13sp",
                bold=True,
                color=(1, 1, 0.3, 1),
                size_hint_y=None,
                height=dp(24),
                halign="left",
                text_size=(dp(240), None),
            ))
            self.info_panel.add_widget(Label(
                text=f"Population: {colony.population}  Level: {colony.level}",
                font_size="11sp",
                color=(0.8, 0.9, 1, 0.9),
                size_hint_y=None,
                height=dp(20),
                halign="left",
                text_size=(dp(240), None),
            ))
            self.info_panel.add_widget(Label(
                text=f"Happiness: {colony.happiness}%  Stability: {colony.stability}%",
                font_size="11sp",
                color=(0.8, 0.9, 1, 0.9),
                size_hint_y=None,
                height=dp(20),
                halign="left",
                text_size=(dp(240), None),
            ))

            view_colony_btn = Button(
                text="View Colony Details",
                size_hint_y=None,
                height=dp(36),
                font_size="12sp",
                background_color=(0.15, 0.35, 0.2, 0.9),
                color=(0.3, 1, 0.5, 1),
            )
            view_colony_btn.bind(on_release=self._on_view_colony)
        self.info_panel.add_widget(view_colony_btn)

        self.info_panel.add_widget(Widget(size_hint_y=None, height=dp(8)))

    def _update_compare_button(self):
        if not self._comparison_button:
            return
        count = len(self._comparison_selection)
        self._comparison_button.text = f"Compare Selected ({count}/3)"
        self._comparison_button.disabled = count < 2

    @staticmethod
    def _body_type_icon(body_type):
        """Return a text icon for a body type."""
        icons = {
            "rocky": "O",       # Circle
            "gas_giant": "G",   # Gas
            "ice": "I",
            "volcanic": "V",
            "oceanic": "~",
            "barren": ".",
            "desert": "D",
            "toxic": "!",
            "garden": "*",
            "artificial": "#",
            "asteroid_belt": ":",
        }
        return icons.get(body_type, "?")

    # ------------------------------------------------------------------
    # Callbacks
    # ------------------------------------------------------------------

    def _on_compare_toggle(self, button):
        body_id = getattr(button, "body_id", None)
        if not body_id:
            return
        if button.state == "down":
            if body_id in self._comparison_selection:
                self._update_compare_button()
                return
            if len(self._comparison_selection) >= 3:
                button.state = "normal"
                return
            self._comparison_selection.append(body_id)
        else:
            if body_id in self._comparison_selection:
                self._comparison_selection.remove(body_id)
        self._update_compare_button()

    def _open_comparison_view(self, *args):
        if not self.game_state or not self.system_id:
            return
        if len(self._comparison_selection) < 2:
            return
        system = self.game_state.galaxy.systems.get(self.system_id)
        comparison_data = build_comparison_data(system, self._comparison_selection)
        if not comparison_data:
            return
        popup = PlanetComparisonPopup(comparison_data)
        popup.open()

    def _on_body_tap(self, body_id):
        if body_id == "__gate__":
            # Tapped the gate — could show gate info
            return
        self._selected_body_id = body_id
        self._update_info_panel()
        # Double-tap logic: if already selected, zoom in
        # For now, single tap shows info; button in panel zooms in.

    def _on_ship_tap(self, ship_id):
        self._show_ship_context(ship_id)

    def _on_region_tap(self, body_id):
        pass  # Future: surface region interaction

    def _show_ship_context(self, ship_id):
        """Show ship context menu (reuse Galaxy Map's pattern)."""
        from kivy.app import App
        app = App.get_running_app()
        if not app or not self.game_state:
            return
        ship = self.game_state.fleet.ships.get(ship_id)
        if not ship:
            return

        from ..widgets.context_menu import ContextMenu
        actions = self.game_state.fleet.get_contextual_actions(
            ship_id,
            galaxy=self.game_state.galaxy,
            colonies=self.game_state.colonies,
        )
        menu = ContextMenu(
            title_text=f"{ship.name} ({ship.ship_class})",
            actions=actions,
            callback=lambda action: self._execute_ship_action(ship_id, action),
        )
        menu.open()

    def _execute_ship_action(self, ship_id, action):
        """Delegate to GalaxyMapScreen's action handler."""
        from kivy.app import App
        app = App.get_running_app()
        if app and hasattr(app, "galaxy_map_screen"):
            app.galaxy_map_screen._execute_action(ship_id, action)
            # Refresh our view
            if self.game_state:
                self.set_game_state(self.game_state)

    def _on_view_colony(self, *args):
        from kivy.app import App
        app = App.get_running_app()
        if app:
            colony_screen = app.sm.get_screen("colony_screen")
            colony_screen.selected_colony = self.system_id
            app.switch_screen("colony_screen")

    def _reset_camera(self, *args):
        """Reset the active map widget's camera to default view."""
        if self._current_level == self.LEVEL_SYSTEM:
            self.system_map.reset_camera()
        elif self._current_level == self.LEVEL_BODY:
            self.body_detail.reset_camera()

    def _go_to_galaxy(self, *args):
        from kivy.app import App
        app = App.get_running_app()
        if app:
            app.switch_screen("galaxy_map")
