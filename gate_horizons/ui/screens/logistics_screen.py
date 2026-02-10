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
from kivy.uix.popup import Popup
from kivy.uix.scrollview import ScrollView
from kivy.uix.textinput import TextInput
from kivy.graphics import Color, Rectangle
from kivy.metrics import dp

from ..widgets.resource_bar import TopBar


class CreateFreightRoutePopup(Popup):
    """Popup for creating a freighter logistics route."""

    def __init__(self, game_state=None, on_create=None, **kwargs):
        self.game_state = game_state
        self.create_callback = on_create
        self.selected_ship_id = None
        self.selected_waypoint_index = 0
        self.input_error_message = None
        self.waypoints = [
            self._new_waypoint(default_action="load"),
            self._new_waypoint(default_action="unload"),
        ]

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
            text="Waypoints:",
            font_size="12sp",
            bold=True,
            color=(0.6, 0.8, 1, 1),
            size_hint_y=None,
            height=dp(20),
        ))
        waypoint_controls = BoxLayout(
            orientation="horizontal",
            size_hint_y=None,
            height=dp(32),
            spacing=dp(6),
        )
        add_wp_btn = Button(
            text="+ Add Waypoint",
            font_size="10sp",
            background_color=(0.12, 0.35, 0.2, 0.85),
            color=(0.7, 1, 0.7, 1),
        )
        add_wp_btn.bind(on_release=self._add_waypoint)
        waypoint_controls.add_widget(add_wp_btn)

        remove_wp_btn = Button(
            text="- Remove Waypoint",
            font_size="10sp",
            background_color=(0.35, 0.12, 0.12, 0.85),
            color=(1, 0.7, 0.7, 1),
        )
        remove_wp_btn.bind(on_release=self._remove_waypoint)
        waypoint_controls.add_widget(remove_wp_btn)

        move_up_btn = Button(
            text="Move Up",
            font_size="10sp",
            background_color=(0.15, 0.2, 0.35, 0.85),
            color=(0.8, 0.9, 1, 1),
        )
        move_up_btn.bind(on_release=lambda *_: self._move_waypoint(-1))
        waypoint_controls.add_widget(move_up_btn)

        move_down_btn = Button(
            text="Move Down",
            font_size="10sp",
            background_color=(0.15, 0.2, 0.35, 0.85),
            color=(0.8, 0.9, 1, 1),
        )
        move_down_btn.bind(on_release=lambda *_: self._move_waypoint(1))
        waypoint_controls.add_widget(move_down_btn)
        content.add_widget(waypoint_controls)

        waypoint_body = BoxLayout(orientation="horizontal", spacing=dp(8), size_hint_y=None, height=dp(260))

        self.waypoint_list = BoxLayout(orientation="vertical", size_hint_x=0.35, spacing=dp(4))
        self.waypoint_list.bind(minimum_height=self.waypoint_list.setter("height"))
        waypoint_scroll = ScrollView(size_hint=(1, 1))
        waypoint_scroll.add_widget(self.waypoint_list)
        waypoint_body.add_widget(waypoint_scroll)

        self.waypoint_editor = BoxLayout(orientation="vertical", spacing=dp(6), size_hint_x=0.65)
        waypoint_editor_scroll = ScrollView(size_hint=(1, 1))
        waypoint_editor_scroll.add_widget(self.waypoint_editor)
        waypoint_body.add_widget(waypoint_editor_scroll)
        content.add_widget(waypoint_body)

        self._refresh_waypoint_list()
        self._render_waypoint_editor()

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
            text="Select waypoint systems and a freighter",
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

        self._update_status()

        super().__init__(
            title="Create Freight Route",
            content=content,
            size_hint=(0.82, 0.92),
            title_color=(0.3, 0.85, 1, 1),
            separator_color=(0.15, 0.6, 0.8, 0.6),
            background_color=(0.04, 0.06, 0.12, 0.95),
            **kwargs,
        )

    def _new_rule(self, default_action="load"):
        return {
            "resource_id": "",
            "action": default_action,
            "amount": 0,
            "min_threshold": 0,
            "max_threshold": 0,
        }

    def _new_waypoint(self, default_action="load"):
        return {
            "system_id": None,
            "wait_turns": 0,
            "cargo_rules": [self._new_rule(default_action=default_action)],
        }

    def _refresh_waypoint_list(self):
        self.waypoint_list.clear_widgets()
        if not self.waypoints:
            self.waypoint_list.add_widget(Label(
                text="No waypoints",
                font_size="11sp",
                color=(0.5, 0.5, 0.5, 1),
                size_hint_y=None,
                height=dp(24),
            ))
            return
        for idx, wp in enumerate(self.waypoints):
            label = self._system_label(wp.get("system_id")) or "Select system"
            if wp.get("wait_turns", 0) > 0:
                label += f" (wait {wp['wait_turns']}t)"
            btn = Button(
                text=f"{idx + 1}. {label}",
                size_hint_y=None,
                height=dp(32),
                font_size="10sp",
                background_color=(0.2, 0.4, 0.6, 0.9)
                if idx == self.selected_waypoint_index
                else (0.12, 0.25, 0.4, 0.8),
                color=(0.85, 0.95, 1, 1),
            )
            btn.waypoint_index = idx
            btn.bind(on_release=self._select_waypoint)
            self.waypoint_list.add_widget(btn)

    def _render_waypoint_editor(self):
        self.waypoint_editor.clear_widgets()
        if not self.waypoints:
            return
        waypoint = self.waypoints[self.selected_waypoint_index]
        self.waypoint_editor.add_widget(Label(
            text=f"Waypoint {self.selected_waypoint_index + 1} Details",
            font_size="11sp",
            bold=True,
            color=(0.7, 0.85, 1, 1),
            size_hint_y=None,
            height=dp(20),
        ))

        self.waypoint_editor.add_widget(Label(
            text="System:",
            font_size="11sp",
            color=(0.6, 0.75, 0.9, 0.9),
            size_hint_y=None,
            height=dp(18),
        ))
        self.system_button_layout = BoxLayout(
            orientation="horizontal",
            size_hint_y=None,
            height=dp(32),
            spacing=dp(4),
        )
        self._populate_system_buttons(self.system_button_layout)
        self.waypoint_editor.add_widget(self.system_button_layout)

        self.waypoint_editor.add_widget(Label(
            text="Wait Turns:",
            font_size="11sp",
            color=(0.6, 0.75, 0.9, 0.9),
            size_hint_y=None,
            height=dp(18),
        ))
        self.wait_turns_input = TextInput(
            text=str(waypoint.get("wait_turns", 0)),
            font_size="11sp",
            multiline=False,
            input_filter="int",
            size_hint_y=None,
            height=dp(28),
            background_color=(0.1, 0.12, 0.18, 0.9),
            foreground_color=(0.8, 0.9, 1, 1),
        )
        self.wait_turns_input.bind(on_text_validate=self._update_wait_turns)
        self.wait_turns_input.bind(text=self._update_wait_turns)
        self.waypoint_editor.add_widget(self.wait_turns_input)

        self.waypoint_editor.add_widget(Label(
            text="Cargo Rules (resource id, amount, min/max thresholds):",
            font_size="11sp",
            color=(0.6, 0.75, 0.9, 0.9),
            size_hint_y=None,
            height=dp(18),
        ))
        rules_scroll = ScrollView(size_hint=(1, None), height=dp(120))
        self.cargo_rules_layout = BoxLayout(orientation="vertical", spacing=dp(4), size_hint_y=None)
        self.cargo_rules_layout.bind(minimum_height=self.cargo_rules_layout.setter("height"))
        rules_scroll.add_widget(self.cargo_rules_layout)
        self.waypoint_editor.add_widget(rules_scroll)

        add_rule_btn = Button(
            text="+ Add Cargo Rule",
            size_hint_y=None,
            height=dp(30),
            font_size="10sp",
            background_color=(0.12, 0.35, 0.2, 0.85),
            color=(0.7, 1, 0.7, 1),
        )
        add_rule_btn.bind(on_release=self._add_cargo_rule)
        self.waypoint_editor.add_widget(add_rule_btn)

        self._refresh_cargo_rules()

    def _populate_system_buttons(self, layout):
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
            btn.bind(on_release=self._on_select_system)
            layout.add_widget(btn)

    def _refresh_cargo_rules(self):
        self.cargo_rules_layout.clear_widgets()
        waypoint = self.waypoints[self.selected_waypoint_index]
        for rule in waypoint.get("cargo_rules", []):
            row = BoxLayout(
                orientation="horizontal",
                spacing=dp(4),
                size_hint_y=None,
                height=dp(30),
            )
            action_btn = Button(
                text=rule.get("action", "load").title(),
                size_hint_x=None,
                width=dp(68),
                font_size="9sp",
                background_color=(0.1, 0.25, 0.35, 0.9),
                color=(0.85, 0.95, 1, 1),
            )
            action_btn.bind(on_release=lambda btn, r=rule: self._toggle_rule_action(r, btn))
            row.add_widget(action_btn)

            resource_input = TextInput(
                text=rule.get("resource_id", ""),
                multiline=False,
                font_size="9sp",
                size_hint_x=None,
                width=dp(120),
                background_color=(0.1, 0.12, 0.18, 0.9),
                foreground_color=(0.8, 0.9, 1, 1),
            )
            resource_input.bind(text=lambda inst, value, r=rule: self._update_rule_text(r, "resource_id", value))
            row.add_widget(resource_input)

            amount_input = TextInput(
                text=str(rule.get("amount", 0)),
                multiline=False,
                font_size="9sp",
                input_filter="int",
                size_hint_x=None,
                width=dp(50),
                background_color=(0.1, 0.12, 0.18, 0.9),
                foreground_color=(0.8, 0.9, 1, 1),
            )
            amount_input.bind(text=lambda inst, value, r=rule: self._update_rule_int(r, "amount", value))
            row.add_widget(amount_input)

            min_input = TextInput(
                text=str(rule.get("min_threshold", 0)),
                multiline=False,
                font_size="9sp",
                input_filter="int",
                size_hint_x=None,
                width=dp(50),
                background_color=(0.1, 0.12, 0.18, 0.9),
                foreground_color=(0.8, 0.9, 1, 1),
            )
            min_input.bind(text=lambda inst, value, r=rule: self._update_rule_int(r, "min_threshold", value))
            row.add_widget(min_input)

            max_input = TextInput(
                text=str(rule.get("max_threshold", 0)),
                multiline=False,
                font_size="9sp",
                input_filter="int",
                size_hint_x=None,
                width=dp(50),
                background_color=(0.1, 0.12, 0.18, 0.9),
                foreground_color=(0.8, 0.9, 1, 1),
            )
            max_input.bind(text=lambda inst, value, r=rule: self._update_rule_int(r, "max_threshold", value))
            row.add_widget(max_input)

            remove_btn = Button(
                text="X",
                size_hint_x=None,
                width=dp(26),
                font_size="9sp",
                background_color=(0.35, 0.12, 0.12, 0.85),
                color=(1, 0.7, 0.7, 1),
            )
            remove_btn.bind(on_release=lambda btn, r=rule: self._remove_cargo_rule(r))
            row.add_widget(remove_btn)

            self.cargo_rules_layout.add_widget(row)

    def _populate_freighters(self):
        self.ship_layout.clear_widgets()
        if not self.game_state:
            return
        freighter_classes = {"freighter", "small_freighter", "medium_freighter", "large_freighter"}
        for ship in self.game_state.fleet.ships.values():
            ship_class = ship.ship_class or ""
            if ship_class not in freighter_classes and "freighter" not in ship_class:
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

    def _system_label(self, system_id):
        if not self.game_state or not system_id:
            return None
        system = self.game_state.galaxy.systems.get(system_id)
        if system:
            return system.name
        colony = self.game_state.colonies.colonies.get(system_id)
        if colony:
            return colony.name
        return system_id

    def _on_select_system(self, btn):
        waypoint = self.waypoints[self.selected_waypoint_index]
        waypoint["system_id"] = btn.system_id
        for child in self.system_button_layout.children:
            if hasattr(child, "system_id"):
                child.background_color = (
                    (0.2, 0.4, 0.6, 0.9)
                    if child.system_id == waypoint["system_id"]
                    else (0.12, 0.25, 0.4, 0.8)
                )
        self._refresh_waypoint_list()
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

    def _select_waypoint(self, btn):
        self.selected_waypoint_index = btn.waypoint_index
        self._refresh_waypoint_list()
        self._render_waypoint_editor()
        self._update_status()

    def _add_waypoint(self, *args):
        default_action = "load" if not self.waypoints else "unload"
        self.waypoints.append(self._new_waypoint(default_action=default_action))
        self.selected_waypoint_index = len(self.waypoints) - 1
        self._refresh_waypoint_list()
        self._render_waypoint_editor()
        self._update_status()

    def _remove_waypoint(self, *args):
        if len(self.waypoints) <= 2:
            self.status_label.text = "At least two waypoints are required"
            self.status_label.color = (1, 0.5, 0.3, 0.9)
            return
        self.waypoints.pop(self.selected_waypoint_index)
        self.selected_waypoint_index = max(0, self.selected_waypoint_index - 1)
        self._refresh_waypoint_list()
        self._render_waypoint_editor()
        self._update_status()

    def _move_waypoint(self, direction):
        if not self.waypoints:
            return
        new_index = self.selected_waypoint_index + direction
        if new_index < 0 or new_index >= len(self.waypoints):
            return
        self.waypoints[self.selected_waypoint_index], self.waypoints[new_index] = (
            self.waypoints[new_index],
            self.waypoints[self.selected_waypoint_index],
        )
        self.selected_waypoint_index = new_index
        self._refresh_waypoint_list()
        self._render_waypoint_editor()
        self._update_status()

    def _update_wait_turns(self, *args):
        waypoint = self.waypoints[self.selected_waypoint_index]
        raw_value = (self.wait_turns_input.text or "").strip()
        if raw_value == "":
            self.input_error_message = "Invalid wait turns: expected non-negative integer (e.g., 0, 2)."
            self._update_status()
            return
        try:
            parsed = int(raw_value)
        except ValueError:
            self.input_error_message = f"Invalid wait turns '{self.wait_turns_input.text}': expected non-negative integer (e.g., 0, 2)."
            self._update_status()
            return
        if parsed < 0:
            self.input_error_message = "Invalid wait turns: expected non-negative integer (e.g., 0, 2)."
            self._update_status()
            return
        waypoint["wait_turns"] = parsed
        self.input_error_message = None
        self._refresh_waypoint_list()
        self._update_status()

    def _add_cargo_rule(self, *args):
        waypoint = self.waypoints[self.selected_waypoint_index]
        waypoint.setdefault("cargo_rules", []).append(self._new_rule())
        self._refresh_cargo_rules()

    def _remove_cargo_rule(self, rule):
        waypoint = self.waypoints[self.selected_waypoint_index]
        if rule in waypoint.get("cargo_rules", []):
            waypoint["cargo_rules"].remove(rule)
        self._refresh_cargo_rules()

    def _toggle_rule_action(self, rule, button):
        rule["action"] = "unload" if rule.get("action") == "load" else "load"
        button.text = rule["action"].title()

    def _update_rule_text(self, rule, field, value):
        rule[field] = value.strip()

    def _update_rule_int(self, rule, field, value):
        text = (value or "").strip()
        label = field.replace("_", " ")
        if text == "":
            self.input_error_message = (
                f"Invalid {label}: expected non-negative integer (e.g., 0, 5)."
            )
            self._update_status()
            return
        try:
            parsed = int(text)
        except ValueError:
            self.input_error_message = (
                f"Invalid {label} '{value}': expected non-negative integer (e.g., 0, 5)."
            )
            self._update_status()
            return
        if parsed < 0:
            self.input_error_message = (
                f"Invalid {label}: expected non-negative integer (e.g., 0, 5)."
            )
            self._update_status()
            return
        rule[field] = parsed
        self.input_error_message = None
        self._update_status()

    def _update_status(self):
        if self.input_error_message:
            self.status_label.text = self.input_error_message
            self.status_label.color = (1, 0.3, 0.2, 1)
            return
        parts = []
        missing_systems = [i + 1 for i, wp in enumerate(self.waypoints) if not wp.get("system_id")]
        if missing_systems:
            parts.append(f"Select system for waypoint(s): {', '.join(map(str, missing_systems))}")
        if not self.selected_ship_id:
            parts.append("Assign freighter")
        if len(self.waypoints) < 2:
            parts.append("Need at least two waypoints")

        self.status_label.text = ", ".join(parts) if parts else "Ready to create route"
        self.status_label.color = (1, 0.5, 0.3, 0.9) if parts else (0.3, 1, 0.5, 0.9)

    def _on_create(self, *args):
        if not self.game_state:
            return
        if len(self.waypoints) < 2:
            self.status_label.text = "At least two waypoints are required"
            self.status_label.color = (1, 0.3, 0.2, 1)
            return
        if not self.selected_ship_id:
            self.status_label.text = "Assign a freighter"
            self.status_label.color = (1, 0.3, 0.2, 1)
            return
        if self.input_error_message:
            self.status_label.text = self.input_error_message
            self.status_label.color = (1, 0.3, 0.2, 1)
            return

        ship = self.game_state.fleet.ships.get(self.selected_ship_id)
        if not ship:
            self.status_label.text = "Assigned ship not found"
            self.status_label.color = (1, 0.3, 0.2, 1)
            return
        if "freighter" not in (ship.ship_class or ""):
            self.status_label.text = "Only freighter-class ships can run freight routes"
            self.status_label.color = (1, 0.3, 0.2, 1)
            return
        if ship.trade_route or self.game_state.logistics.get_route_for_ship(ship.id):
            self.status_label.text = "Ship already assigned to another route"
            self.status_label.color = (1, 0.3, 0.2, 1)
            return

        allowed_resources = set(self.game_state.production.config.resource_definitions.keys())
        allowed_resources.update(self.game_state.resources.global_resources.keys())
        allowed_resources.add("pop")

        waypoint_dicts = []
        has_cargo_resource = False
        for wp in self.waypoints:
            system_id = wp.get("system_id")
            if not system_id:
                self.status_label.text = "All waypoints must select a system"
                self.status_label.color = (1, 0.3, 0.2, 1)
                return
            if system_id not in self.game_state.galaxy.systems:
                self.status_label.text = f"Invalid system: {system_id}"
                self.status_label.color = (1, 0.3, 0.2, 1)
                return

            rules = []
            for rule in wp.get("cargo_rules", []):
                resource_id = rule.get("resource_id", "").strip()
                if not resource_id:
                    continue
                if resource_id not in allowed_resources:
                    self.status_label.text = f"Unsupported resource: {resource_id}"
                    self.status_label.color = (1, 0.3, 0.2, 1)
                    return
                action = rule.get("action", "load")
                if action not in {"load", "unload"}:
                    self.status_label.text = f"Invalid action: {action}"
                    self.status_label.color = (1, 0.3, 0.2, 1)
                    return
                has_cargo_resource = True
                int_fields = [
                    ("amount", "amount"),
                    ("min_threshold", "min threshold"),
                    ("max_threshold", "max threshold"),
                ]
                parsed_values = {}
                for field_name, label in int_fields:
                    raw_value = str(rule.get(field_name, "")).strip()
                    if raw_value == "":
                        self.status_label.text = (
                            f"Invalid {label} for resource '{resource_id}': expected non-negative integer (e.g., 0, 5)."
                        )
                        self.status_label.color = (1, 0.3, 0.2, 1)
                        return
                    try:
                        parsed = int(raw_value)
                    except ValueError:
                        self.status_label.text = (
                            f"Invalid {label} for resource '{resource_id}': expected non-negative integer (e.g., 0, 5)."
                        )
                        self.status_label.color = (1, 0.3, 0.2, 1)
                        return
                    if parsed < 0:
                        self.status_label.text = (
                            f"Invalid {label} for resource '{resource_id}': expected non-negative integer (e.g., 0, 5)."
                        )
                        self.status_label.color = (1, 0.3, 0.2, 1)
                        return
                    parsed_values[field_name] = parsed

                rules.append({
                    "resource_id": resource_id,
                    "action": action,
                    "amount": parsed_values["amount"],
                    "min_threshold": parsed_values["min_threshold"],
                    "max_threshold": parsed_values["max_threshold"],
                })

            raw_wait_turns = str(wp.get("wait_turns", "")).strip()
            if raw_wait_turns == "":
                self.status_label.text = (
                    f"Invalid wait turns for waypoint {len(waypoint_dicts) + 1}: expected non-negative integer (e.g., 0, 2)."
                )
                self.status_label.color = (1, 0.3, 0.2, 1)
                return
            try:
                wait_turns = int(raw_wait_turns)
            except ValueError:
                self.status_label.text = (
                    f"Invalid wait turns for waypoint {len(waypoint_dicts) + 1}: expected non-negative integer (e.g., 0, 2)."
                )
                self.status_label.color = (1, 0.3, 0.2, 1)
                return
            if wait_turns < 0:
                self.status_label.text = (
                    f"Invalid wait turns for waypoint {len(waypoint_dicts) + 1}: expected non-negative integer (e.g., 0, 2)."
                )
                self.status_label.color = (1, 0.3, 0.2, 1)
                return

            waypoint_dicts.append({
                "system_id": system_id,
                "wait_turns": wait_turns,
                "cargo_rules": rules,
            })

        if not has_cargo_resource:
            self.status_label.text = "Add at least one cargo rule with a resource"
            self.status_label.color = (1, 0.3, 0.2, 1)
            return

        route_name = self.name_input.text.strip() or None
        route = self.game_state.logistics.create_route(
            name=route_name or "Freight Route",
            waypoints=waypoint_dicts,
            assigned_ship_id=self.selected_ship_id,
        )
        ship.mission = "freight"

        self.dismiss()
        if self.create_callback:
            self.create_callback()


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
            wait_note = f" (wait {wp.wait_turns}t)" if wp.wait_turns > 0 else ""
            text += f"  {i+1}. {wp.system_id}{wait_note}{marker}\n"
            for rule in wp.cargo_rules:
                text += f"     {rule.action} {rule.resource_id}"
                details = []
                if rule.amount > 0:
                    details.append(f"max {rule.amount}")
                if rule.min_threshold > 0:
                    details.append(f"min {rule.min_threshold}")
                if rule.max_threshold > 0:
                    details.append(f"maxdest {rule.max_threshold}")
                if details:
                    text += f" ({', '.join(details)})"
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
