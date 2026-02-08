"""Reusable camera controller for pan/zoom map widgets.

Provides pinch-to-zoom, wheel zoom, and drag pan behaviour that can be
shared by the Galaxy Map, System Map, and Body Detail views.
"""

import math

from kivy.uix.widget import Widget
from kivy.core.window import Window
from kivy.metrics import dp

# Keyboard constants
_PAN_SPEED = 20  # pixels per key press


class MapCameraWidget(Widget):
    """Base widget that provides pan/zoom camera behaviour.

    Subclasses must implement ``_redraw()`` to render content.
    They should call ``_apply_transform(base_x, base_y)`` to convert
    base (content) coordinates into screen coordinates.

    Keyboard shortcuts (active when widget is visible):
      Arrow keys / WASD — pan
      +/= — zoom in
      -   — zoom out
      Home / 0 — reset camera
      Escape — go back (if callback provided)
    """

    def __init__(self, on_view_change=None, on_back=None, **kwargs):
        super().__init__(**kwargs)
        self.on_view_change = on_view_change
        self.on_back = on_back
        self._pan_offset = [0.0, 0.0]
        self._scale = 1.0
        self._min_scale = 0.3
        self._max_scale = 4.0
        self._active_touches = {}
        self._pinch_start_distance = None
        self._pinch_start_scale = None
        self._pinch_start_offset = None
        self._keyboard_bound = False

    def on_parent(self, widget, parent):
        """Bind/unbind keyboard when attached/detached."""
        if parent and not self._keyboard_bound:
            Window.bind(on_key_down=self._on_key_down)
            self._keyboard_bound = True
        elif not parent and self._keyboard_bound:
            Window.unbind(on_key_down=self._on_key_down)
            self._keyboard_bound = False

    def _on_key_down(self, window, key, scancode, codepoint, modifiers):
        """Handle keyboard shortcuts for pan/zoom."""
        if not self.parent:
            return False

        # Arrow keys / WASD for pan
        if key in (273, 119):  # Up / W
            self._pan_offset[1] -= _PAN_SPEED
        elif key in (274, 115):  # Down / S
            self._pan_offset[1] += _PAN_SPEED
        elif key in (276, 97):  # Left / A
            self._pan_offset[0] += _PAN_SPEED
        elif key in (275, 100):  # Right / D
            self._pan_offset[0] -= _PAN_SPEED
        elif key in (61, 270):  # = / numpad+
            self._zoom_at((self.center_x, self.center_y), 1.15)
        elif key in (45, 269):  # - / numpad-
            self._zoom_at((self.center_x, self.center_y), 0.87)
        elif key in (278, 48):  # Home / 0
            self.reset_camera()
        elif key == 27 or codepoint == "\x1b":  # Escape
            if self.on_back:
                self.on_back()
                return True
            return False
        else:
            return False

        self._redraw()
        if self.on_view_change:
            self.on_view_change()
        return True

    # ------------------------------------------------------------------
    # Transform helpers
    # ------------------------------------------------------------------

    def _apply_transform(self, x, y):
        """Convert base coordinates to screen coordinates."""
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

    def reset_camera(self):
        """Reset to default view."""
        self._pan_offset = [0.0, 0.0]
        self._scale = 1.0
        self._redraw()

    # ------------------------------------------------------------------
    # Touch handling — identical for every map level
    # ------------------------------------------------------------------

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
        touch.ud["map_cam"] = {"moved": False}

        if len(self._active_touches) == 2:
            touches = list(self._active_touches.values())
            self._pinch_start_distance = self._distance(touches[0], touches[1])
            self._pinch_start_scale = self._scale
            self._pinch_start_offset = list(self._pan_offset)
        return True

    def on_touch_move(self, touch):
        if touch.uid not in self._active_touches:
            return False

        touch.ud.get("map_cam", {})["moved"] = True

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

        moved = touch.ud.get("map_cam", {}).get("moved", False)
        self._active_touches.pop(touch.uid, None)

        if len(self._active_touches) < 2:
            self._pinch_start_distance = None
            self._pinch_start_scale = None
            self._pinch_start_offset = None

        if not moved:
            return self._handle_tap(touch)
        return True

    # ------------------------------------------------------------------
    # Override points
    # ------------------------------------------------------------------

    def _redraw(self, *args):
        """Subclasses must override to render content."""
        pass

    def _handle_tap(self, touch):
        """Subclasses override to handle taps on content."""
        return True

    @staticmethod
    def _distance(touch_a, touch_b):
        return ((touch_a.x - touch_b.x) ** 2 + (touch_a.y - touch_b.y) ** 2) ** 0.5
