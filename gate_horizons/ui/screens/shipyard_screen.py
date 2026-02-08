"""Shipyard management screen for Gate Horizons.

Provides UI for:
- Building/upgrading orbital facilities (Spaceport, Drydock, Orbital Yard)
- Queuing ship builds with component costs
- Viewing build queue progress
- Viewing orbital facility status per colony
"""

from kivy.uix.screenmanager import Screen
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.gridlayout import GridLayout
from kivy.uix.button import Button
from kivy.uix.label import Label
from kivy.uix.scrollview import ScrollView
from kivy.graphics import Color, Rectangle
from kivy.metrics import dp

from ..widgets.resource_bar import TopBar


class ShipyardScreen(Screen):
    """Orbital shipyard management screen.

    Left: system/colony list
    Right: facilities at selected system, build queue, ship blueprint buttons
    """

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.name = "shipyard_screen"
        self.game_state = None
        self.selected_system_id = None
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

        # --- Left: system list ---
        left = BoxLayout(orientation="vertical", size_hint_x=0.25, padding=dp(8), spacing=dp(4))
        left.add_widget(Label(
            text="Systems", font_size="16sp", bold=True,
            color=(0.3, 0.85, 1, 1), size_hint_y=None, height=dp(36),
        ))
        self.system_list = BoxLayout(
            orientation="vertical", spacing=dp(4), size_hint_y=None,
        )
        self.system_list.bind(minimum_height=self.system_list.setter("height"))
        scroll = ScrollView(size_hint=(1, 1))
        scroll.add_widget(self.system_list)
        left.add_widget(scroll)

        back_btn = Button(
            text="< Back to Map", size_hint_y=None, height=dp(36),
            font_size="12sp", background_color=(0.08, 0.15, 0.25, 0.8),
            color=(0.7, 0.85, 1, 1),
        )
        back_btn.bind(on_release=self._go_back)
        left.add_widget(back_btn)
        root.add_widget(left)

        # --- Right: shipyard details ---
        right = BoxLayout(orientation="vertical", size_hint_x=0.75, padding=dp(8), spacing=dp(8))
        right.add_widget(Label(
            text="Orbital Shipyard", font_size="16sp", bold=True,
            color=(1, 0.8, 0.3, 1), size_hint_y=None, height=dp(36),
        ))

        # Facilities section
        self.facilities_label = Label(
            text="Select a system to view orbital facilities",
            font_size="12sp", color=(0.8, 0.8, 0.8, 1),
            markup=True,
            halign="left", valign="top",
            size_hint_y=None, height=dp(120),
        )
        self.facilities_label.bind(size=self.facilities_label.setter("text_size"))

        # Build queue section
        self.queue_label = Label(
            text="", font_size="12sp", color=(0.9, 0.7, 0.3, 1),
            markup=True,
            halign="left", valign="top",
            size_hint_y=None, height=dp(120),
        )
        self.queue_label.bind(size=self.queue_label.setter("text_size"))
        self.queue_actions = BoxLayout(
            orientation="horizontal", size_hint_y=None, height=dp(36), spacing=dp(4),
        )
        cancel_btn = Button(
            text="Cancel Oldest", font_size="10sp",
            background_color=(0.35, 0.1, 0.1, 0.9),
            color=(1, 0.6, 0.6, 1),
        )
        cancel_btn.bind(on_release=self._cancel_oldest_build)
        rush_btn = Button(
            text="Rush Active", font_size="10sp",
            background_color=(0.2, 0.2, 0.35, 0.9),
            color=(0.8, 0.85, 1, 1),
        )
        rush_btn.bind(on_release=self._rush_active_build)
        self.queue_actions.add_widget(cancel_btn)
        self.queue_actions.add_widget(rush_btn)

        # Facility build buttons
        self.facility_buttons = BoxLayout(
            orientation="horizontal", size_hint_y=None, height=dp(40), spacing=dp(4),
        )
        for ftype in ["spaceport", "drydock", "orbital_yard"]:
            btn = Button(
                text=f"Build\n{ftype.replace('_', ' ').title()}", font_size="10sp",
                background_color=(0.15, 0.25, 0.15, 0.9),
                color=(0.7, 1, 0.7, 1),
            )
            btn.facility_type = ftype
            btn.bind(on_release=self._build_facility)
            self.facility_buttons.add_widget(btn)

        # Ship build buttons
        self.ship_buttons_label = Label(
            text="[b]Build Ships (component-based):[/b]",
            font_size="12sp", color=(0.8, 0.8, 0.8, 1),
            markup=True,
            size_hint_y=None, height=dp(24),
            halign="left",
        )
        self.ship_buttons_label.bind(size=self.ship_buttons_label.setter("text_size"))

        self.ship_buttons = BoxLayout(
            orientation="horizontal", size_hint_y=None, height=dp(40), spacing=dp(4),
        )
        for blueprint in [
            "scout", "miner", "small_freighter", "medium_freighter",
            "corvette", "colony_ship", "large_freighter",
        ]:
            btn = Button(
                text=blueprint.replace("_", "\n").title(), font_size="10sp",
                background_color=(0.2, 0.15, 0.3, 0.9),
                color=(0.8, 0.7, 1, 1),
            )
            btn.blueprint_id = blueprint
            btn.bind(on_release=self._build_ship)
            self.ship_buttons.add_widget(btn)

        details_scroll = ScrollView(size_hint=(1, 1))
        details_box = BoxLayout(orientation="vertical", size_hint_y=None, spacing=dp(4))
        details_box.bind(minimum_height=details_box.setter("height"))
        details_box.add_widget(self.facilities_label)
        details_box.add_widget(self.facility_buttons)
        details_box.add_widget(self.queue_label)
        details_box.add_widget(self.queue_actions)
        details_box.add_widget(self.ship_buttons_label)
        details_box.add_widget(self.ship_buttons)
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
        self._refresh_system_list()
        self._refresh_details()

    def _refresh_system_list(self):
        self.system_list.clear_widgets()
        if not self.game_state:
            return
        # Show systems that have colonies
        for system_id, colony in self.game_state.colonies.colonies.items():
            facilities = self.game_state.shipyard.get_facilities(system_id)
            fac_count = len(facilities)
            btn = Button(
                text=f"{colony.name}\n{fac_count} orbital facility(s)",
                font_size="10sp", size_hint_y=None, height=dp(48),
                background_color=(0.1, 0.2, 0.35, 0.9),
                color=(0.8, 0.9, 1, 1),
            )
            btn.system_id = system_id
            btn.bind(on_release=self._select_system)
            self.system_list.add_widget(btn)

    def _select_system(self, instance):
        self.selected_system_id = instance.system_id
        self._refresh_details()

    def _refresh_details(self):
        if not self.game_state or not self.selected_system_id:
            return
        system_id = self.selected_system_id
        facilities = self.game_state.shipyard.get_facilities(system_id)

        fac_text = f"[b]Orbital Facilities at {system_id}[/b]\n\n"
        if facilities:
            for f in facilities:
                status = "BUILDING" if f.building else "OPERATIONAL"
                fac_text += (
                    f"  {f.facility_type.replace('_', ' ').title()} "
                    f"(level {f.level}) [{status}]"
                )
                if f.building:
                    fac_text += f" — {f.build_turns_remaining} turns left"
                fac_text += "\n"
        else:
            fac_text += "  (no orbital facilities)\n"
        self.facilities_label.text = fac_text

        # Build queue
        facilities = self.game_state.shipyard.facilities.get(system_id, [])
        facility_ids = {f.id for f in facilities}
        queue = [
            o for o in self.game_state.shipyard.get_build_queue_summary()
            if o.get("facility_id") in facility_ids
        ]
        queue_text = "[b]Build Queue:[/b]\n"
        if queue:
            for o in queue:
                status = o.get("status", "active")
                progress = o.get("progress", 0.0)
                queue_text += (
                    f"  {o.get('name')} ({o.get('blueprint')}) — "
                    f"{o.get('turns_left')} turns [{status}] ({progress:.0f}%)\n"
                )
        else:
            queue_text += "  (empty)\n"
        self.queue_label.text = queue_text

    def _build_facility(self, instance):
        if not self.game_state or not self.selected_system_id:
            return
        colony = self.game_state.colonies.colonies.get(self.selected_system_id)
        if not colony:
            return
        self.game_state.shipyard.build_facility(
            self.selected_system_id,
            instance.facility_type,
            self.game_state.production.config.to_dict(),
            colony.production_inventory,
            self.game_state.resources,
        )
        self.refresh()

    def _build_ship(self, instance):
        if not self.game_state or not self.selected_system_id:
            return
        self.game_state.build_ship_orbital(
            self.selected_system_id,
            instance.blueprint_id,
        )
        self.refresh()

    def _cancel_oldest_build(self, instance):
        if not self.game_state or not self.selected_system_id:
            return
        colony = self.game_state.colonies.colonies.get(self.selected_system_id)
        if not colony:
            return
        queue = self.game_state.shipyard.get_build_queue_summary()
        if not queue:
            return
        order_id = queue[0].get("id")
        if not order_id:
            return
        self.game_state.shipyard.cancel_build(
            order_id,
            config=self.game_state.production.config.to_dict(),
            inventory=colony.production_inventory,
            resources=self.game_state.resources,
        )
        self.refresh()

    def _rush_active_build(self, instance):
        if not self.game_state or not self.selected_system_id:
            return
        queue = [
            o for o in self.game_state.shipyard.get_build_queue_summary()
            if o.get("status") == "active"
        ]
        if not queue:
            return
        order_id = queue[0].get("id")
        if not order_id:
            return
        self.game_state.shipyard.rush_build(
            order_id,
            config=self.game_state.production.config.to_dict(),
            resources=self.game_state.resources,
        )
        self.refresh()

    def _go_back(self, instance):
        self.manager.current = "galaxy_map"
