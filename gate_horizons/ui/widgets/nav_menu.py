"""Dropdown navigation menu widgets for the bottom command bar.

Provides categorised dropdown menus that replace the flat button strip,
keeping the bottom bar compact while giving access to all screens.
"""

from kivy.uix.boxlayout import BoxLayout
from kivy.uix.button import Button
from kivy.uix.label import Label
from kivy.uix.widget import Widget
from kivy.uix.dropdown import DropDown
from kivy.graphics import Color, Rectangle, RoundedRectangle
from kivy.metrics import dp


class NavDropDown(DropDown):
    """Styled dropdown that matches the Gate Horizons theme."""

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.auto_width = False
        self.width = dp(180)

    def open(self, widget):
        super().open(widget)
        # Style the dropdown container after it opens
        if self.container:
            self.container.spacing = dp(2)
            self.container.padding = [dp(4), dp(4)]


class NavDropDownItem(Button):
    """A single item inside a NavDropDown."""

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.size_hint_y = None
        self.height = dp(44)
        self.font_size = "13sp"
        self.background_color = (0.06, 0.1, 0.2, 0.95)
        self.color = (0.75, 0.88, 1, 1)
        self.halign = "left"
        self.valign = "middle"
        self.padding = [dp(12), 0]
        self.text_size = (dp(160), None)


class NavCategoryButton(Button):
    """A category button in the bottom bar that opens a dropdown."""

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.size_hint = (None, 1)
        self.font_size = "12sp"
        self.background_color = (0, 0, 0, 0)
        self.color = (0.7, 0.85, 1, 1)
        self._dropdown = None
        self._bg_color = (0.08, 0.15, 0.25, 0.6)

    def _update_bg(self, *args):
        self.canvas.before.clear()
        with self.canvas.before:
            Color(*self._bg_color)
            RoundedRectangle(pos=self.pos, size=self.size, radius=[dp(4)])

    def on_size(self, *args):
        self._update_bg()

    def on_pos(self, *args):
        self._update_bg()


def build_command_bar(nav_callback, end_turn_callback, save_callback,
                      load_callback, flow_toggle_callback, settings_callback=None):
    """Build the redesigned bottom command bar.

    Returns (bar_widget, flow_toggle_btn) so the caller can update
    the flow toggle text.

    Layout:
      [Menu] [Empire ▾] [Military ▾] [Intel ▾] [Map ▾]  <spacer>  [END TURN]
    """
    bar = BoxLayout(
        orientation="horizontal",
        size_hint_y=None,
        height=dp(52),
        padding=[dp(6), dp(4)],
        spacing=dp(6),
    )
    with bar.canvas.before:
        Color(0.04, 0.07, 0.14, 1)
        bar_bg = Rectangle(pos=bar.pos, size=bar.size)
        Color(0.15, 0.6, 0.8, 0.5)
        bar_line = Rectangle(pos=bar.pos, size=(bar.width, 1))
    bar.bind(
        size=lambda w, v: (
            setattr(bar_bg, "size", v),
            setattr(bar_line, "size", (v[0], 1)),
        ),
        pos=lambda w, v: (
            setattr(bar_bg, "pos", v),
            setattr(bar_line, "pos", (v[0], v[1] + bar.height - 1)),
        ),
    )

    # -- Menu button (Save/Load) --
    menu_items = [
        ("Save Game", "_save"),
        ("Load Game", "_load"),
    ]
    special_callbacks = {
        "_save": save_callback,
        "_load": load_callback,
    }
    if settings_callback:
        menu_items.append(("Settings", "_settings"))
        special_callbacks["_settings"] = settings_callback
    menu_btn = _make_dropdown_btn(
        "Menu", dp(64), menu_items, nav_callback,
        special_callbacks=special_callbacks,
    )
    bar.add_widget(menu_btn)

    # Separator
    bar.add_widget(_separator())

    # -- Galaxy Map (direct button, always go to map) --
    map_btn = Button(
        text="Galaxy",
        size_hint=(None, 1),
        width=dp(62),
        font_size="12sp",
        background_color=(0.08, 0.15, 0.25, 0.6),
        color=(0.7, 0.85, 1, 1),
    )
    map_btn.screen_name = "galaxy_map"
    map_btn.bind(on_release=lambda b: nav_callback(b.screen_name))
    bar.add_widget(map_btn)

    # Separator
    bar.add_widget(_separator())

    # -- Empire dropdown --
    empire_items = [
        ("Colonies", "colony_screen"),
        ("Trade", "trade_screen"),
        ("Production", "production_screen"),
        ("Logistics", "logistics_screen"),
        ("Shipyard", "shipyard_screen"),
    ]
    empire_btn = _make_dropdown_btn("Empire", dp(72), empire_items, nav_callback)
    bar.add_widget(empire_btn)

    # -- Military dropdown --
    military_items = [
        ("Fleet", "fleet_screen"),
        ("Encounters", "encounter_screen"),
        ("Relations", "relations_screen"),
    ]
    military_btn = _make_dropdown_btn("Military", dp(72), military_items, nav_callback)
    bar.add_widget(military_btn)

    # -- Intel dropdown --
    intel_items = [
        ("Technology", "tech_screen"),
        ("Missions", "mission_screen"),
    ]
    intel_btn = _make_dropdown_btn("Intel", dp(62), intel_items, nav_callback)
    bar.add_widget(intel_btn)

    # Separator
    bar.add_widget(_separator())

    # -- Map Options dropdown --
    flow_toggle_btn = [None]  # mutable reference

    def _build_map_options_dropdown():
        dropdown = NavDropDown()
        dropdown.width = dp(160)

        flow_item = NavDropDownItem(text="Toggle Flows")
        flow_item.bind(on_release=lambda b: (
            dropdown.dismiss(),
            flow_toggle_callback(),
        ))
        dropdown.add_widget(flow_item)

        flow_toggle_btn[0] = flow_item
        return dropdown

    map_opt_btn = Button(
        text="View",
        size_hint=(None, 1),
        width=dp(56),
        font_size="12sp",
        background_color=(0.08, 0.15, 0.25, 0.6),
        color=(0.7, 0.85, 1, 1),
    )
    map_options_dd = _build_map_options_dropdown()
    map_opt_btn._dropdown = map_options_dd
    map_opt_btn.bind(on_release=map_options_dd.open)
    bar.add_widget(map_opt_btn)

    # Spacer pushes END TURN to the right
    bar.add_widget(Widget())

    # -- END TURN button (always visible, prominent) --
    end_turn_btn = Button(
        text="END TURN",
        size_hint=(None, 1),
        width=dp(120),
        font_size="15sp",
        bold=True,
        background_color=(0, 0, 0, 0),
        color=(1, 1, 1, 1),
    )
    with end_turn_btn.canvas.before:
        Color(0.2, 0.6, 0.3, 1)
        et_bg = RoundedRectangle(
            pos=end_turn_btn.pos,
            size=end_turn_btn.size,
            radius=[dp(6)],
        )
    end_turn_btn.bind(
        pos=lambda w, v: setattr(et_bg, "pos", v),
        size=lambda w, v: setattr(et_bg, "size", v),
    )
    end_turn_btn.bind(on_release=lambda b: end_turn_callback())
    bar.add_widget(end_turn_btn)

    return bar, flow_toggle_btn[0]


def _make_dropdown_btn(label, width, items, nav_callback, special_callbacks=None):
    """Create a category button with a dropdown of screen navigation items."""
    dropdown = NavDropDown()
    dropdown.width = dp(180)

    for item_text, screen_name in items:
        item = NavDropDownItem(text=item_text)
        if special_callbacks and screen_name in special_callbacks:
            cb = special_callbacks[screen_name]
            item.bind(on_release=lambda b, c=cb: (dropdown.dismiss(), c()))
        else:
            item.bind(on_release=lambda b, sn=screen_name: (
                dropdown.dismiss(),
                nav_callback(sn),
            ))
        dropdown.add_widget(item)

    btn = Button(
        text=label,
        size_hint=(None, 1),
        width=width,
        font_size="12sp",
        background_color=(0.08, 0.15, 0.25, 0.6),
        color=(0.7, 0.85, 1, 1),
    )
    btn._dropdown = dropdown
    btn.bind(on_release=dropdown.open)
    return btn


def _separator():
    """Thin vertical separator line."""
    sep = Widget(size_hint=(None, 1), width=dp(1))
    with sep.canvas:
        Color(0.15, 0.25, 0.4, 0.5)
        sep_rect = Rectangle(pos=sep.pos, size=sep.size)
    sep.bind(
        pos=lambda w, v: setattr(sep_rect, "pos", v),
        size=lambda w, v: setattr(sep_rect, "size", v),
    )
    return sep
