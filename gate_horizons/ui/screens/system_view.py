"""System view screen - zoomed view of a single star system."""

from kivy.uix.screenmanager import Screen
from kivy.uix.floatlayout import FloatLayout
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.gridlayout import GridLayout
from kivy.uix.button import Button
from kivy.uix.label import Label
from kivy.uix.widget import Widget
from kivy.uix.scrollview import ScrollView
from kivy.uix.popup import Popup
from kivy.graphics import Color, Ellipse, Line, Rectangle
from kivy.metrics import dp
import math

from ..widgets.resource_bar import TopBar


COLONIZATION_COST = {"credits": 50, "metals": 30}


class ColonizeConfirmPopup(Popup):
    """Confirmation popup for establishing a colony."""

    def __init__(self, planet_name="", cost=None, can_afford=True, on_confirm=None, **kwargs):
        self.confirm_callback = on_confirm
        cost = cost or COLONIZATION_COST

        content = BoxLayout(orientation="vertical", spacing=dp(8), padding=dp(12))

        content.add_widget(Label(
            text=f"Establish colony on {planet_name}?",
            font_size="14sp",
            bold=True,
            color=(0.3, 0.85, 1, 1),
            size_hint_y=None,
            height=dp(30),
        ))

        cost_text = ", ".join(f"{v} {k}" for k, v in cost.items())
        content.add_widget(Label(
            text=f"Cost: {cost_text}",
            font_size="12sp",
            color=(1, 0.8, 0.3, 0.9) if can_afford else (1, 0.4, 0.3, 0.9),
            size_hint_y=None,
            height=dp(24),
        ))

        if not can_afford:
            content.add_widget(Label(
                text="Insufficient resources!",
                font_size="12sp",
                color=(1, 0.3, 0.2, 1),
                size_hint_y=None,
                height=dp(22),
            ))

        content.add_widget(Label(
            text="A new colony starts with 100 population.",
            font_size="11sp",
            color=(0.5, 0.7, 0.9, 0.8),
            size_hint_y=None,
            height=dp(22),
        ))

        btn_row = BoxLayout(orientation="horizontal", size_hint_y=None, height=dp(44), spacing=dp(8))

        confirm_btn = Button(
            text="Establish Colony",
            font_size="13sp",
            background_color=(0.15, 0.4, 0.2, 0.9) if can_afford else (0.2, 0.2, 0.2, 0.5),
            color=(0.3, 1, 0.5, 1) if can_afford else (0.4, 0.4, 0.4, 0.5),
            disabled=not can_afford,
        )
        confirm_btn.bind(on_release=self._on_confirm)
        btn_row.add_widget(confirm_btn)

        cancel_btn = Button(
            text="Cancel",
            font_size="13sp",
            background_color=(0.3, 0.1, 0.1, 0.8),
            color=(1, 0.7, 0.7, 1),
        )
        cancel_btn.bind(on_release=lambda x: self.dismiss())
        btn_row.add_widget(cancel_btn)

        content.add_widget(btn_row)
        content.add_widget(Widget())

        super().__init__(
            title="Colonization",
            content=content,
            size_hint=(0.4, 0.45),
            title_color=(0.3, 0.85, 1, 1),
            separator_color=(0.15, 0.6, 0.8, 0.6),
            background_color=(0.04, 0.06, 0.12, 0.95),
            **kwargs,
        )

    def _on_confirm(self, *args):
        self.dismiss()
        if self.confirm_callback:
            self.confirm_callback()


class SystemViewScreen(Screen):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.name = "system_view"
        self.game_state = None
        self.system_id = None
        self._build_ui()

    def _build_ui(self):
        root = FloatLayout()

        with root.canvas.before:
            Color(0.02, 0.03, 0.08, 1)
            self._bg = Rectangle(pos=root.pos, size=root.size)
        root.bind(
            size=lambda w, v: setattr(self._bg, 'size', v),
            pos=lambda w, v: setattr(self._bg, 'pos', v),
        )

        main_vertical = BoxLayout(orientation="vertical", size_hint=(1, 1))

        # Top bar
        self.top_bar = TopBar()
        main_vertical.add_widget(self.top_bar)

        main = BoxLayout(orientation="horizontal", size_hint=(1, 1))

        # Left side: planet orbital view
        self.orbital_view = Widget(size_hint=(0.6, 1))
        self.orbital_view.bind(size=self._draw_orbital, pos=self._draw_orbital)
        main.add_widget(self.orbital_view)

        # Right side: info panel
        self.info_panel = BoxLayout(
            orientation="vertical",
            size_hint=(0.4, 1),
            padding=dp(8),
            spacing=dp(4),
        )
        with self.info_panel.canvas.before:
            Color(0.04, 0.06, 0.12, 0.95)
            self._panel_bg = Rectangle(pos=self.info_panel.pos, size=self.info_panel.size)
        self.info_panel.bind(
            size=lambda w, v: setattr(self._panel_bg, 'size', v),
            pos=lambda w, v: setattr(self._panel_bg, 'pos', v),
        )
        main.add_widget(self.info_panel)

        main_vertical.add_widget(main)
        root.add_widget(main_vertical)

        # Back button overlay
        back_btn = Button(
            text="< Back to Map",
            size_hint=(None, None),
            size=(dp(130), dp(36)),
            pos_hint={"x": 0.01, "top": 0.93},
            font_size="12sp",
            background_color=(0.08, 0.15, 0.25, 0.8),
            color=(0.7, 0.85, 1, 1),
        )
        back_btn.bind(on_release=self._go_back)
        root.add_widget(back_btn)

        self.add_widget(root)

    def set_system(self, game_state, system_id):
        self.game_state = game_state
        self.system_id = system_id
        self.top_bar.update(game_state)
        self._draw_orbital()
        self._update_info()

    def _draw_orbital(self, *args):
        self.orbital_view.canvas.clear()
        if not self.game_state or not self.system_id:
            return

        system = self.game_state.galaxy.systems.get(self.system_id)
        if not system:
            return

        cx = self.orbital_view.center_x
        cy = self.orbital_view.center_y
        max_radius = min(self.orbital_view.width, self.orbital_view.height) * 0.4

        with self.orbital_view.canvas:
            # Star at center
            Color(1, 0.9, 0.3, 1)
            star_size = dp(30)
            Ellipse(pos=(cx - star_size / 2, cy - star_size / 2),
                    size=(star_size, star_size))

            # Draw orbital rings and planets
            num_planets = len(system.planets)
            for i, planet in enumerate(system.planets):
                orbit_r = max_radius * (0.3 + 0.7 * (i / max(1, num_planets)))

                # Orbital ring
                Color(0.2, 0.3, 0.4, 0.3)
                Line(circle=(cx, cy, orbit_r), width=0.8)

                # Planet position (spread around the orbit)
                angle = (i * 137.5 + 45) * math.pi / 180  # Golden angle spread
                px = cx + orbit_r * math.cos(angle)
                py = cy + orbit_r * math.sin(angle)

                # Planet colors by type
                planet_colors = {
                    "rocky": (0.6, 0.5, 0.3, 1),
                    "gas_giant": (0.8, 0.6, 0.2, 1),
                    "ice": (0.6, 0.8, 1, 1),
                    "volcanic": (1, 0.3, 0.1, 1),
                    "oceanic": (0.2, 0.5, 0.9, 1),
                    "barren": (0.5, 0.5, 0.5, 1),
                }
                color = planet_colors.get(planet.type, (0.5, 0.5, 0.5, 1))
                Color(*color)

                p_size = dp(16) if planet.type != "gas_giant" else dp(24)
                Ellipse(pos=(px - p_size / 2, py - p_size / 2),
                        size=(p_size, p_size))

                # Colony indicator on planet
                if self.system_id in self.game_state.colonies.colonies:
                    colony = self.game_state.colonies.colonies[self.system_id]
                    if colony.planet_id == planet.id:
                        Color(1, 1, 0.3, 0.8)
                        c_size = dp(6)
                        Ellipse(pos=(px - c_size / 2, py + p_size / 2),
                                size=(c_size, c_size))

    def _update_info(self):
        self.info_panel.clear_widgets()
        if not self.game_state or not self.system_id:
            return

        system = self.game_state.galaxy.systems.get(self.system_id)
        if not system:
            return

        # System header
        self.info_panel.add_widget(Label(
            text=system.name,
            font_size="18sp",
            bold=True,
            color=(0.3, 0.85, 1, 1),
            size_hint_y=None,
            height=dp(36),
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
        if not system.gate_active and system.gate_activation_cost:
            costs = ", ".join(f"{v} {k}" for k, v in system.gate_activation_cost.items())
            gate_text += f" (Activate: {costs})"
        self.info_panel.add_widget(Label(
            text=gate_text,
            font_size="11sp",
            color=(0.15, 0.6, 0.8, 1) if system.gate_active else (1, 0.4, 0.2, 1),
            size_hint_y=None,
            height=dp(22),
            halign="left",
            text_size=(dp(300), None),
        ))

        # Anomalies
        if system.anomalies:
            for anomaly in system.anomalies:
                self.info_panel.add_widget(Label(
                    text=f"Anomaly: {anomaly}",
                    font_size="11sp",
                    color=(1, 0.7, 0.3, 0.9),
                    size_hint_y=None,
                    height=dp(20),
                    halign="left",
                    text_size=(dp(300), None),
                ))

        # Planets scroll
        scroll = ScrollView(size_hint=(1, 1))
        planet_list = BoxLayout(
            orientation="vertical",
            spacing=dp(6),
            size_hint_y=None,
            padding=[0, dp(4)],
        )
        planet_list.bind(minimum_height=planet_list.setter("height"))

        # Colony info at top
        colony = self.game_state.colonies.colonies.get(self.system_id)
        if colony:
            col_card = BoxLayout(
                orientation="vertical",
                size_hint_y=None,
                height=dp(60),
                padding=dp(6),
            )
            with col_card.canvas.before:
                Color(0.15, 0.2, 0.1, 0.8)
                col_bg = Rectangle(pos=col_card.pos, size=col_card.size)
            col_card.bind(
                size=lambda w, v, bg=col_bg: setattr(bg, 'size', v),
                pos=lambda w, v, bg=col_bg: setattr(bg, 'pos', v),
            )
            col_card.add_widget(Label(
                text=f"Colony: {colony.name} (Pop: {colony.population}, T{colony.get_tier()})",
                font_size="12sp",
                bold=True,
                color=(1, 1, 0.3, 1),
                size_hint_y=None,
                height=dp(22),
                halign="left",
                text_size=(dp(300), None),
            ))
            view_colony_btn = Button(
                text="View Colony Details",
                size_hint_y=None,
                height=dp(30),
                font_size="11sp",
                background_color=(0.15, 0.35, 0.2, 0.9),
                color=(0.3, 1, 0.5, 1),
            )
            view_colony_btn.bind(on_release=self._on_view_colony)
            col_card.add_widget(view_colony_btn)
            planet_list.add_widget(col_card)

        # Planet entries
        planet_list.add_widget(Label(
            text="Planets:",
            font_size="13sp",
            bold=True,
            color=(0.6, 0.8, 1, 1),
            size_hint_y=None,
            height=dp(26),
            halign="left",
            text_size=(dp(300), None),
        ))

        for planet in system.planets:
            # Planet card
            card = BoxLayout(
                orientation="vertical",
                size_hint_y=None,
                height=dp(90),
                padding=dp(6),
                spacing=dp(2),
            )

            card.add_widget(Label(
                text=f"{planet.name} ({planet.type})",
                font_size="13sp",
                bold=True,
                color=(0.8, 0.9, 1, 1),
                size_hint_y=None,
                height=dp(22),
                halign="left",
                text_size=(dp(300), None),
            ))

            if planet.description:
                card.add_widget(Label(
                    text=planet.description[:100],
                    font_size="10sp",
                    color=(0.5, 0.6, 0.7, 0.8),
                    size_hint_y=None,
                    height=dp(20),
                    halign="left",
                    text_size=(dp(300), None),
                ))

            # Resources
            if planet.resources:
                res_text = "  ".join(f"{k}: {v}/turn" for k, v in planet.resources.items() if v > 0)
                if res_text:
                    card.add_widget(Label(
                        text=f"Resources: {res_text}",
                        font_size="11sp",
                        color=(0.7, 0.85, 1, 0.9),
                        size_hint_y=None,
                        height=dp(18),
                        halign="left",
                        text_size=(dp(300), None),
                    ))

            # Colonize button
            if planet.colonizable and self.system_id not in self.game_state.colonies.colonies:
                can_afford = self.game_state.resources.can_afford(COLONIZATION_COST)
                cost_text = ", ".join(f"{v} {k}" for k, v in COLONIZATION_COST.items())
                col_btn = Button(
                    text=f"Establish Colony ({cost_text})",
                    size_hint_y=None,
                    height=dp(32),
                    font_size="12sp",
                    background_color=(0.15, 0.4, 0.2, 0.9) if can_afford else (0.2, 0.2, 0.2, 0.5),
                    color=(0.3, 1, 0.5, 1) if can_afford else (0.4, 0.4, 0.4, 0.5),
                )
                col_btn.planet_id = planet.id
                col_btn.planet_name = planet.name
                col_btn.bind(on_release=self._on_colonize)
                card.add_widget(col_btn)

            planet_list.add_widget(card)

        # Ships section
        ships_here = self.game_state.fleet.get_ships_at(self.system_id)
        if ships_here:
            planet_list.add_widget(Label(
                text=f"Ships ({len(ships_here)}):",
                font_size="13sp",
                bold=True,
                color=(0.6, 0.8, 1, 1),
                size_hint_y=None,
                height=dp(26),
                halign="left",
                text_size=(dp(300), None),
            ))

            for ship in ships_here:
                mission_text = f" [{ship.mission}]" if ship.mission else ""
                if ship.mining:
                    mission_text = " [mining]"
                ship_btn = Button(
                    text=f"{ship.name} [{ship.ship_class}] hull:{ship.hull}/{ship.stats.max_hull}{mission_text}",
                    size_hint_y=None,
                    height=dp(34),
                    font_size="11sp",
                    background_color=(0.12, 0.25, 0.4, 0.6),
                    color=(0.85, 0.95, 1, 1),
                )
                planet_list.add_widget(ship_btn)

        # Build ship section
        if colony and colony.infrastructure.get("spaceport", {}).get("level", 0) > 0:
            planet_list.add_widget(Label(
                text="Build Ship:",
                font_size="13sp",
                bold=True,
                color=(0.6, 0.8, 1, 1),
                size_hint_y=None,
                height=dp(26),
                halign="left",
                text_size=(dp(300), None),
            ))

            for ship_class in ["scout", "freighter", "miner", "corvette"]:
                template = self.game_state.fleet._ship_templates.get(ship_class, {})
                cost = template.get("build_cost", {})
                cost_text = ", ".join(f"{v} {k}" for k, v in cost.items()) if cost else "free"
                can_afford = self.game_state.resources.can_afford(cost) if cost else True
                build_btn = Button(
                    text=f"{template.get('name', ship_class)} ({cost_text})",
                    size_hint_y=None,
                    height=dp(36),
                    font_size="11sp",
                    background_color=(0.12, 0.25, 0.4, 0.8) if can_afford else (0.15, 0.15, 0.2, 0.5),
                    color=(0.85, 0.95, 1, 1) if can_afford else (0.4, 0.4, 0.5, 0.5),
                    disabled=not can_afford,
                )
                build_btn.ship_class = ship_class
                build_btn.bind(on_release=self._on_build_ship)
                planet_list.add_widget(build_btn)

        # Gate activation
        if not system.gate_active and system.gate_activation_cost:
            planet_list.add_widget(Widget(size_hint_y=None, height=dp(8)))
            can_activate = self.game_state.resources.can_afford(system.gate_activation_cost)
            costs = ", ".join(f"{v} {k}" for k, v in system.gate_activation_cost.items())
            activate_btn = Button(
                text=f"Activate Gate ({costs})",
                size_hint_y=None,
                height=dp(40),
                font_size="13sp",
                background_color=(0.15, 0.4, 0.2, 0.9) if can_activate else (0.2, 0.2, 0.2, 0.5),
                color=(0.3, 1, 0.5, 1) if can_activate else (0.4, 0.4, 0.4, 0.5),
                disabled=not can_activate,
            )
            activate_btn.bind(on_release=self._on_activate_gate)
            planet_list.add_widget(activate_btn)

        scroll.add_widget(planet_list)
        self.info_panel.add_widget(scroll)

    def _on_colonize(self, btn):
        if not self.game_state:
            return
        can_afford = self.game_state.resources.can_afford(COLONIZATION_COST)

        popup = ColonizeConfirmPopup(
            planet_name=btn.planet_name,
            cost=COLONIZATION_COST,
            can_afford=can_afford,
            on_confirm=lambda pid=btn.planet_id, pname=btn.planet_name: self._do_colonize(pid, pname),
        )
        popup.open()

    def _do_colonize(self, planet_id, planet_name):
        if not self.game_state:
            return
        if self.game_state.resources.can_afford(COLONIZATION_COST):
            self.game_state.resources.spend_dict(COLONIZATION_COST)
            self.game_state.colonies.establish_colony(
                self.system_id,
                planet_id,
                planet_name,
            )
            # Update system tier
            system = self.game_state.galaxy.systems.get(self.system_id)
            if system and system.tier == 0:
                system.tier = 3
            self.top_bar.update(self.game_state)
            self._update_info()

    def _on_build_ship(self, btn):
        if not self.game_state:
            return
        template = self.game_state.fleet._ship_templates.get(btn.ship_class, {})
        cost = template.get("build_cost", {})
        if cost:
            if not self.game_state.resources.can_afford(cost):
                return
            self.game_state.resources.spend_dict(cost)
        self.game_state.fleet.create_ship(btn.ship_class, self.system_id)
        self.top_bar.update(self.game_state)
        self._update_info()

    def _on_activate_gate(self, *args):
        if not self.game_state or not self.system_id:
            return
        result = self.game_state.galaxy.activate_gate(
            self.system_id, self.game_state.resources
        )
        if result:
            self.top_bar.update(self.game_state)
            self._update_info()

    def _on_view_colony(self, *args):
        from kivy.app import App
        app = App.get_running_app()
        if app:
            app.colony_screen.selected_colony = self.system_id
            app.switch_screen("colony_screen")

    def _go_back(self, *args):
        from kivy.app import App
        app = App.get_running_app()
        if app:
            app.switch_screen("galaxy_map")
