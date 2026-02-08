"""Tactical combat screen for Gate Horizons."""

from __future__ import annotations

import hashlib
import math
import random

from kivy.uix.screenmanager import Screen
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.button import Button
from kivy.uix.label import Label
from kivy.uix.widget import Widget
from kivy.graphics import Color, Line, Ellipse, Rectangle
from kivy.metrics import dp

from gate_horizons.game.tactical import HexGrid, TacticalCombat, TacticalUnit, TERRAIN_TYPES
from ..widgets.resource_bar import TopBar


class TacticalGridWidget(Widget):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.combat: TacticalCombat | None = None
        self.hex_size = dp(22)
        self._centers = {}
        self.selected_unit_id = None
        self.on_cell_tap = None
        self.bind(size=self._redraw, pos=self._redraw)

    def set_combat(self, combat: TacticalCombat):
        self.combat = combat
        self._redraw()

    def _hex_center(self, q: int, r: int) -> tuple[float, float]:
        size = self.hex_size
        x = size * math.sqrt(3) * (q + r / 2)
        y = size * 1.5 * r
        return x, y

    def _build_centers(self):
        self._centers.clear()
        if not self.combat:
            return
        grid = self.combat.grid
        for q in range(grid.width):
            for r in range(grid.height):
                self._centers[(q, r)] = self._hex_center(q, r)

        if not self._centers:
            return
        xs = [p[0] for p in self._centers.values()]
        ys = [p[1] for p in self._centers.values()]
        min_x, max_x = min(xs), max(xs)
        min_y, max_y = min(ys), max(ys)
        offset_x = (self.width - (max_x - min_x)) / 2 - min_x
        offset_y = (self.height - (max_y - min_y)) / 2 - min_y
        for key, (x, y) in list(self._centers.items()):
            self._centers[key] = (x + offset_x, y + offset_y)

    def _hex_points(self, center_x: float, center_y: float) -> list[float]:
        size = self.hex_size
        points = []
        for i in range(6):
            angle_deg = 60 * i - 30
            angle_rad = math.pi / 180 * angle_deg
            px = center_x + size * math.cos(angle_rad)
            py = center_y + size * math.sin(angle_rad)
            points.extend([px, py])
        return points

    def _redraw(self, *args):
        self.canvas.clear()
        if not self.combat:
            return
        self._build_centers()
        grid = self.combat.grid

        with self.canvas:
            for coord, center in self._centers.items():
                cell = grid.cells.get(coord)
                if not cell:
                    continue
                terrain = cell.terrain
                Color(*terrain.color, 0.9)
                points = self._hex_points(*center)
                Line(points=points + points[:2], width=1)

            # Selection ring
            if self.selected_unit_id:
                selected = self.combat.get_unit(self.selected_unit_id)
                if selected and not selected.destroyed:
                    center = self._centers.get(selected.position)
                    if center:
                        Color(1, 1, 1, 0.4)
                        Line(points=self._hex_points(*center), width=2)

            # Units
            for unit in self.combat.units:
                if unit.destroyed:
                    continue
                center = self._centers.get(unit.position)
                if not center:
                    continue
                if unit.faction == "player":
                    Color(0.2, 0.9, 0.5, 1)
                else:
                    Color(0.9, 0.3, 0.3, 1)
                size = self.hex_size * 0.55
                Ellipse(pos=(center[0] - size / 2, center[1] - size / 2), size=(size, size))

    def on_touch_down(self, touch):
        if not self.collide_point(*touch.pos):
            return False
        if not self.combat:
            return True
        for coord, center in self._centers.items():
            dist = math.hypot(touch.x - center[0], touch.y - center[1])
            if dist <= self.hex_size:
                if self.on_cell_tap:
                    self.on_cell_tap(coord)
                return True
        return True


class TacticalScreen(Screen):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.name = "tactical_screen"
        self.game_state = None
        self.encounter_entry = None
        self.combat: TacticalCombat | None = None
        self.selected_unit_id: str | None = None
        self.action_mode = "move"
        self._build_ui()

    def _build_ui(self):
        root = BoxLayout(orientation="vertical")

        with root.canvas.before:
            Color(0.02, 0.03, 0.08, 1)
            self._bg = Rectangle(pos=root.pos, size=root.size)
        root.bind(
            size=lambda w, v: setattr(self._bg, "size", v),
            pos=lambda w, v: setattr(self._bg, "pos", v),
        )

        self.top_bar = TopBar()
        root.add_widget(self.top_bar)

        main = BoxLayout(orientation="horizontal")
        self.grid_widget = TacticalGridWidget()
        self.grid_widget.on_cell_tap = self._on_cell_tap
        main.add_widget(self.grid_widget)

        self.info_panel = BoxLayout(
            orientation="vertical",
            size_hint_x=0.35,
            padding=dp(8),
            spacing=dp(6),
        )
        with self.info_panel.canvas.before:
            Color(0.04, 0.06, 0.12, 0.95)
            self._panel_bg = Rectangle(pos=self.info_panel.pos, size=self.info_panel.size)
        self.info_panel.bind(
            size=lambda w, v: setattr(self._panel_bg, "size", v),
            pos=lambda w, v: setattr(self._panel_bg, "pos", v),
        )

        self.turn_label = Label(
            text="",
            font_size="14sp",
            bold=True,
            color=(0.85, 0.95, 1, 1),
            size_hint_y=None,
            height=dp(30),
        )
        self.info_panel.add_widget(self.turn_label)

        self.unit_label = Label(
            text="Select a unit.",
            font_size="12sp",
            color=(0.7, 0.85, 1, 0.9),
            size_hint_y=None,
            height=dp(60),
        )
        self.info_panel.add_widget(self.unit_label)

        self.action_info = Label(
            text="",
            font_size="11sp",
            color=(0.6, 0.8, 1, 0.8),
            size_hint_y=None,
            height=dp(40),
        )
        self.info_panel.add_widget(self.action_info)

        self.move_btn = Button(
            text="Move",
            size_hint_y=None,
            height=dp(40),
            font_size="12sp",
            background_color=(0.12, 0.35, 0.5, 0.85),
            color=(0.85, 0.95, 1, 1),
        )
        self.move_btn.bind(on_release=lambda *a: self._set_action_mode("move"))
        self.info_panel.add_widget(self.move_btn)

        self.attack_btn = Button(
            text="Attack",
            size_hint_y=None,
            height=dp(40),
            font_size="12sp",
            background_color=(0.35, 0.12, 0.2, 0.85),
            color=(1, 0.85, 0.85, 1),
        )
        self.attack_btn.bind(on_release=lambda *a: self._set_action_mode("attack"))
        self.info_panel.add_widget(self.attack_btn)

        self.end_btn = Button(
            text="End Turn",
            size_hint_y=None,
            height=dp(42),
            font_size="13sp",
            background_color=(0.2, 0.6, 0.3, 1),
            color=(1, 1, 1, 1),
        )
        self.end_btn.bind(on_release=self._end_turn)
        self.info_panel.add_widget(self.end_btn)

        self.info_panel.add_widget(Widget())

        back_btn = Button(
            text="Retreat",
            size_hint_y=None,
            height=dp(36),
            font_size="12sp",
            background_color=(0.4, 0.15, 0.15, 0.8),
            color=(1, 0.8, 0.8, 1),
        )
        back_btn.bind(on_release=self._retreat)
        self.info_panel.add_widget(back_btn)

        main.add_widget(self.info_panel)
        root.add_widget(main)
        self.add_widget(root)

    def set_encounter(self, game_state, encounter_entry: dict):
        self.game_state = game_state
        self.encounter_entry = encounter_entry
        self.top_bar.update(game_state)
        self._setup_combat()

    def _setup_combat(self):
        encounter_id = self.encounter_entry.get("encounter_id", "enc-unknown")
        seed = self._stable_seed(encounter_id)
        rng = random.Random(seed)
        grid = HexGrid.generate(width=10, height=8, seed=seed)

        attacker_ids = self.encounter_entry.get("attacker_ship_ids", [])
        units = []
        for index, ship_id in enumerate(attacker_ids):
            ship = self.game_state.fleet.ships.get(ship_id)
            if not ship:
                continue
            unit = TacticalUnit(
                unit_id=ship.id,
                name=ship.name,
                faction="player",
                hp=ship.hull,
                max_hp=ship.stats.max_hull,
                move_points=max(2, ship.stats.speed),
                weapon_range=2,
                weapon_damage=max(2, ship.stats.combat_power // 2),
                accuracy=0.7,
                position=(1, min(index * 2, grid.height - 1)),
            )
            units.append(unit)

        defender = self.encounter_entry.get("defender", {})
        enemy_hp = max(10, int(defender.get("strength", 8)) * 2)
        enemy = TacticalUnit(
            unit_id="enemy-1",
            name=defender.get("type", "Enemy").title(),
            faction="enemy",
            hp=enemy_hp,
            max_hp=enemy_hp,
            move_points=2,
            weapon_range=2,
            weapon_damage=max(2, int(defender.get("strength", 8)) // 3),
            accuracy=0.6,
            position=(grid.width - 2, grid.height // 2),
        )
        units.append(enemy)

        self.combat = TacticalCombat(
            grid=grid,
            units=units,
            rng=rng,
            defender_loot=defender.get("loot_table", {}),
        )
        self.grid_widget.set_combat(self.combat)
        self.selected_unit_id = units[0].unit_id if units else None
        self.grid_widget.selected_unit_id = self.selected_unit_id
        self._refresh_info()

    @staticmethod
    def _stable_seed(value: str) -> int:
        digest = hashlib.sha256(value.encode("utf-8")).hexdigest()
        return int(digest[:8], 16)

    def _set_action_mode(self, mode: str):
        self.action_mode = mode
        self._refresh_info()

    def _refresh_info(self):
        if not self.combat:
            return
        self.turn_label.text = f"Turn: {self.combat.current_faction.title()}"
        unit = self.combat.get_unit(self.selected_unit_id) if self.selected_unit_id else None
        if unit:
            terrain = self.combat.grid.terrain_at(unit.position).name
            self.unit_label.text = (
                f"{unit.name} ({unit.hp}/{unit.max_hp})\n"
                f"Move: {unit.remaining_move}  Terrain: {terrain}"
            )
        else:
            self.unit_label.text = "Select a unit."
        self.action_info.text = f"Mode: {self.action_mode.title()}"
        self.grid_widget.selected_unit_id = self.selected_unit_id
        self.grid_widget._redraw()

    def _on_cell_tap(self, coord):
        if not self.combat or self.combat.current_faction != "player":
            return
        occupant = self.combat.occupied_positions().get(coord)
        if occupant and occupant.faction == "player":
            self.selected_unit_id = occupant.unit_id
            self._refresh_info()
            return
        if not self.selected_unit_id:
            return
        unit = self.combat.get_unit(self.selected_unit_id)
        if not unit or unit.faction != "player":
            return
        if self.action_mode == "move":
            if self.combat.move_unit(unit.unit_id, coord):
                self._refresh_info()
        elif self.action_mode == "attack" and occupant and occupant.faction == "enemy":
            self.combat.attack(unit.unit_id, occupant.unit_id)
            self._check_resolution()
            self._refresh_info()

    def _end_turn(self, *args):
        if not self.combat:
            return
        self.combat.end_turn()
        if self.combat.current_faction == "enemy":
            self.combat.resolve_ai_turn()
            self._check_resolution()
            self.combat.end_turn()
        self._refresh_info()

    def _check_resolution(self):
        if not self.combat:
            return
        winner = self.combat.winner()
        if not winner:
            return
        outcome = self.combat.build_outcome()
        encounter_id = self.encounter_entry.get("encounter_id", "enc-unknown")
        player_units = [u for u in self.combat.units if u.faction == "player"]
        result_spec = self.combat.outcome_to_result_spec(outcome, encounter_id, player_units)
        self.game_state.submit_encounter_result(result_spec)

        from kivy.app import App
        app = App.get_running_app()
        if app:
            app.switch_screen("galaxy_map")

    def _retreat(self, *args):
        if not self.combat:
            return
        outcome = self.combat.build_outcome()
        outcome.winner = "enemy"
        outcome.summary = "Player retreated from the tactical engagement."
        encounter_id = self.encounter_entry.get("encounter_id", "enc-unknown")
        player_units = [u for u in self.combat.units if u.faction == "player"]
        result_spec = self.combat.outcome_to_result_spec(outcome, encounter_id, player_units)
        result_spec["outcome"] = "retreat"
        self.game_state.submit_encounter_result(result_spec)

        from kivy.app import App
        app = App.get_running_app()
        if app:
            app.switch_screen("galaxy_map")
