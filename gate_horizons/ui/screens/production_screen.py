"""Production management screen for Gate Horizons.

Provides UI for:
- Viewing colony production inventories (raw, processed, components)
- Managing extraction sites and their output rates
- Setting factory production queues (recipe selection)
- Viewing extraction and factory output per turn
"""

from kivy.uix.screenmanager import Screen
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.gridlayout import GridLayout
from kivy.uix.button import Button
from kivy.uix.label import Label
from kivy.uix.scrollview import ScrollView
from kivy.uix.popup import Popup
from kivy.graphics import Color, Rectangle
from kivy.metrics import dp

from ..widgets.resource_bar import TopBar


class NoticePopup(Popup):
    """Simple notification popup for production actions."""

    def __init__(self, title="Notice", message="", **kwargs):
        content = BoxLayout(orientation="vertical", spacing=dp(8), padding=dp(12))
        content.add_widget(Label(
            text=message,
            font_size="12sp",
            color=(0.7, 0.85, 1, 0.9),
            size_hint_y=None,
            height=dp(48),
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
        ok_btn.bind(on_release=lambda x: self.dismiss())
        content.add_widget(ok_btn)

        super().__init__(
            title=title,
            content=content,
            size_hint=(0.4, 0.35),
            title_color=(0.3, 0.85, 1, 1),
            separator_color=(0.15, 0.6, 0.8, 0.6),
            background_color=(0.04, 0.06, 0.12, 0.95),
            **kwargs,
        )


class ExtractionSitePopup(Popup):
    """Popup for selecting and building an extraction site."""

    def __init__(self, game_state=None, colony=None, on_build=None, **kwargs):
        self.game_state = game_state
        self.colony = colony
        self.on_build = on_build

        content = BoxLayout(orientation="vertical", spacing=dp(6), padding=dp(10))

        content.add_widget(Label(
            text="Select Extraction Resource",
            font_size="14sp",
            bold=True,
            color=(0.6, 0.8, 1, 1),
            size_hint_y=None,
            height=dp(24),
        ))

        self.option_box = BoxLayout(
            orientation="vertical",
            spacing=dp(4),
            size_hint_y=None,
        )
        self.option_box.bind(minimum_height=self.option_box.setter("height"))
        scroll = ScrollView(size_hint=(1, None), height=dp(180))
        scroll.add_widget(self.option_box)
        content.add_widget(scroll)

        self.status_label = Label(
            text="",
            font_size="11sp",
            color=(0.5, 0.7, 0.9, 0.8),
            size_hint_y=None,
            height=dp(20),
        )
        content.add_widget(self.status_label)

        close_btn = Button(
            text="Close",
            font_size="12sp",
            background_color=(0.3, 0.1, 0.1, 0.8),
            color=(1, 0.7, 0.7, 1),
            size_hint_y=None,
            height=dp(36),
        )
        close_btn.bind(on_release=lambda x: self.dismiss())
        content.add_widget(close_btn)

        super().__init__(
            title="Build Extraction Site",
            content=content,
            size_hint=(0.5, 0.6),
            title_color=(0.3, 0.85, 1, 1),
            separator_color=(0.15, 0.6, 0.8, 0.6),
            background_color=(0.04, 0.06, 0.12, 0.95),
            **kwargs,
        )

        self._populate_options()

    def _populate_options(self):
        self.option_box.clear_widgets()
        if not self.game_state or not self.colony:
            self.status_label.text = "No colony selected."
            return

        system = self.game_state.galaxy.systems.get(self.colony.system_id)
        planet = None
        if system:
            for candidate in system.planets:
                if candidate.id == self.colony.planet_id:
                    planet = candidate
                    break
        if not planet:
            self.status_label.text = "Planet data unavailable."
            return

        researched = {t.id for t in self.game_state.tech.techs.values() if t.researched}
        available = self.game_state.production.determine_extraction_resources(
            planet.type,
            seed=planet.id,
            researched_techs=researched,
        )
        if not available:
            self.status_label.text = "No extractable resources available."
            return

        max_sites = self.game_state.production.config.extraction_balance.get(
            "max_extraction_sites_per_colony", 0
        )
        cost = self.game_state.production.config.extraction_balance.get(
            "extraction_site_build_cost", {}
        )
        cost_text = ", ".join(f"{v} {k}" for k, v in cost.items()) if cost else "free"
        can_afford = self.game_state.can_afford_production_cost(
            self.colony.production_inventory,
            cost,
        )
        limit_reached = max_sites and len(self.colony.extraction_sites) >= max_sites

        for res_info in available:
            resource_id = res_info["resource_id"]
            base_yield = res_info.get("base_yield", 1)
            btn = Button(
                text=f"{resource_id} (yield {base_yield}) — {cost_text}",
                font_size="11sp",
                background_color=(0.15, 0.4, 0.2, 0.9) if can_afford and not limit_reached else (0.2, 0.2, 0.2, 0.5),
                color=(0.3, 1, 0.5, 1) if can_afford and not limit_reached else (0.4, 0.4, 0.4, 0.5),
                size_hint_y=None,
                height=dp(34),
                disabled=limit_reached or not can_afford,
            )
            btn.resource_id = resource_id
            btn.bind(on_release=self._on_build)
            self.option_box.add_widget(btn)

        if limit_reached:
            self.status_label.text = "Extraction site limit reached."
        elif not can_afford:
            self.status_label.text = "Insufficient resources for construction."
        else:
            self.status_label.text = "Select a resource to build."

    def _on_build(self, btn):
        if not self.game_state or not self.colony:
            return
        success, message = self.game_state.build_extraction_site(
            self.colony.system_id,
            btn.resource_id,
        )
        if not success:
            NoticePopup(title="Build Blocked", message=message).open()
            return
        self.dismiss()
        if self.on_build:
            self.on_build()


class ProductionScreen(Screen):
    """Colony production overview screen.

    Left panel: colony list
    Right panel: selected colony's production inventory, extraction sites,
    and factory queue management.
    """

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.name = "production_screen"
        self.game_state = None
        self.selected_colony_id = None
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

        # --- Left panel: colony list ---
        left_panel = BoxLayout(
            orientation="vertical", size_hint_x=0.25, padding=dp(8), spacing=dp(4),
        )
        left_panel.add_widget(Label(
            text="Colonies", font_size="16sp", bold=True,
            color=(0.3, 0.85, 1, 1), size_hint_y=None, height=dp(36),
        ))
        self.colony_list = BoxLayout(
            orientation="vertical", spacing=dp(4), size_hint_y=None,
        )
        self.colony_list.bind(minimum_height=self.colony_list.setter("height"))
        scroll = ScrollView(size_hint=(1, 1))
        scroll.add_widget(self.colony_list)
        left_panel.add_widget(scroll)

        back_btn = Button(
            text="< Back to Map", size_hint_y=None, height=dp(36),
            font_size="12sp", background_color=(0.08, 0.15, 0.25, 0.8),
            color=(0.7, 0.85, 1, 1),
        )
        back_btn.bind(on_release=self._go_back)
        left_panel.add_widget(back_btn)
        root.add_widget(left_panel)

        # --- Right panel: production details ---
        right_panel = BoxLayout(
            orientation="vertical", size_hint_x=0.75, padding=dp(8), spacing=dp(8),
        )

        right_panel.add_widget(Label(
            text="Production Overview", font_size="16sp", bold=True,
            color=(1, 0.8, 0.3, 1), size_hint_y=None, height=dp(36),
        ))

        # Inventory section
        self.inventory_label = Label(
            text="Select a colony to view production",
            font_size="12sp", color=(0.8, 0.8, 0.8, 1),
            markup=True,
            halign="left", valign="top",
            size_hint_y=None, height=dp(200),
        )
        self.inventory_label.bind(size=self.inventory_label.setter("text_size"))

        # Extraction section
        self.extraction_label = Label(
            text="", font_size="12sp", color=(0.7, 0.9, 0.7, 1),
            markup=True,
            halign="left", valign="top",
            size_hint_y=None, height=dp(150),
        )
        self.extraction_label.bind(size=self.extraction_label.setter("text_size"))

        self.extraction_actions = BoxLayout(
            orientation="horizontal", size_hint_y=None, height=dp(36), spacing=dp(6),
        )
        self.extraction_build_btn = Button(
            text="Add Extraction Site",
            font_size="11sp",
            background_color=(0.15, 0.35, 0.2, 0.9),
            color=(0.3, 1, 0.5, 1),
        )
        self.extraction_build_btn.bind(on_release=self._open_extraction_popup)
        self.extraction_actions.add_widget(self.extraction_build_btn)

        # Factory section
        self.factory_label = Label(
            text="", font_size="12sp", color=(0.9, 0.7, 0.3, 1),
            markup=True,
            halign="left", valign="top",
            size_hint_y=None, height=dp(150),
        )
        self.factory_label.bind(size=self.factory_label.setter("text_size"))

        self.factory_build_btn = Button(
            text="Build Factory",
            size_hint_y=None,
            height=dp(36),
            font_size="11sp",
            background_color=(0.2, 0.3, 0.45, 0.9),
            color=(0.8, 0.9, 1, 1),
        )
        self.factory_build_btn.bind(on_release=self._build_factory)

        # Factory action buttons
        self.factory_buttons = BoxLayout(
            orientation="horizontal", size_hint_y=None, height=dp(40), spacing=dp(4),
        )
        for recipe in [
            "metal_alloys", "polymers", "fuel", "electronics",
            "hull_plating", "drive_assemblies", "avionics", "hab_modules", "cargo_frames",
        ]:
            btn = Button(
                text=recipe.replace("_", "\n"), font_size="9sp",
                background_color=(0.15, 0.2, 0.3, 0.9),
                color=(0.8, 0.8, 0.8, 1),
            )
            btn.recipe_id = recipe
            btn.bind(on_release=self._queue_recipe)
            self.factory_buttons.add_widget(btn)

        details_scroll = ScrollView(size_hint=(1, 1))
        details_box = BoxLayout(
            orientation="vertical", size_hint_y=None, spacing=dp(4),
        )
        details_box.bind(minimum_height=details_box.setter("height"))
        details_box.add_widget(self.inventory_label)
        details_box.add_widget(self.extraction_label)
        details_box.add_widget(self.extraction_actions)
        details_box.add_widget(self.factory_label)
        details_box.add_widget(self.factory_build_btn)
        details_box.add_widget(self.factory_buttons)
        details_scroll.add_widget(details_box)
        right_panel.add_widget(details_scroll)

        root.add_widget(right_panel)
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
        self._refresh_colony_list()
        self._refresh_details()

    def _refresh_colony_list(self):
        self.colony_list.clear_widgets()
        if not self.game_state:
            return
        for system_id, colony in self.game_state.colonies.colonies.items():
            btn = Button(
                text=f"{colony.name}\n[{system_id}]",
                font_size="11sp", size_hint_y=None, height=dp(44),
                background_color=(0.1, 0.2, 0.35, 0.9),
                color=(0.8, 0.9, 1, 1),
            )
            btn.system_id = system_id
            btn.bind(on_release=self._select_colony)
            self.colony_list.add_widget(btn)

    def _select_colony(self, instance):
        self.selected_colony_id = instance.system_id
        self._refresh_details()

    def _refresh_details(self):
        if not self.game_state or not self.selected_colony_id:
            return
        colony = self.game_state.colonies.colonies.get(self.selected_colony_id)
        if not colony:
            return

        # Inventory display
        inv = colony.production_inventory
        raw = {k: v for k, v in inv.items() if v > 0 or k in [
            "ore_iron", "silicates", "water_ice", "fissiles", "gas_h2", "gas_he3",
            "gas_d2", "volatiles", "organics", "rare_metals", "exotics",
        ]}
        processed = {k: v for k, v in inv.items() if k in [
            "metal_alloys", "polymers", "fuel", "electronics",
        ]}
        components = {k: v for k, v in inv.items() if k in [
            "hull_plating", "drive_assemblies", "avionics", "hab_modules", "cargo_frames",
        ]}

        inv_text = f"[b]Production Inventory — {colony.name}[/b]\n\n"
        inv_text += "Raw: " + ", ".join(f"{k}={v}" for k, v in raw.items()) + "\n"
        inv_text += "Processed: " + ", ".join(f"{k}={v}" for k, v in processed.items()) + "\n"
        inv_text += "Components: " + ", ".join(f"{k}={v}" for k, v in components.items())
        self.inventory_label.text = inv_text

        # Extraction display
        ext_text = "[b]Extraction Sites[/b]\n"
        for site in colony.extraction_sites:
            status = "BUILDING" if site.building else "ACTIVE" if site.active else "IDLE"
            output = site.get_output_per_tick(
                colony.infrastructure.get("mining", {}).get("level", 0),
            )
            ext_text += f"  {site.resource_id}: yield={output}/turn [{status}]\n"
        if not colony.extraction_sites:
            ext_text += "  (none)\n"
        self.extraction_label.text = ext_text
        self._update_extraction_button(colony)

        # Factory display
        fac_text = "[b]Factories[/b]\n"
        for fac in colony.factories:
            status = "BUILDING" if fac.building else "ACTIVE" if fac.active else "IDLE"
            recipe = fac.current_recipe or "(idle)"
            queue_len = len(fac.recipe_queue)
            fac_text += f"  Recipe: {recipe} [{status}] queue={queue_len}\n"
        if not colony.factories:
            fac_text += "  (none — build a factory first)\n"
        self.factory_label.text = fac_text
        self._update_factory_button(colony)

    def _queue_recipe(self, instance):
        if not self.game_state or not self.selected_colony_id:
            return
        colony = self.game_state.colonies.colonies.get(self.selected_colony_id)
        if not colony or not colony.factories:
            return
        # Queue to first factory
        colony.factories[0].queue_recipe(instance.recipe_id)
        self._refresh_details()

    def _open_extraction_popup(self, instance):
        if not self.game_state or not self.selected_colony_id:
            return
        colony = self.game_state.colonies.colonies.get(self.selected_colony_id)
        if not colony:
            return
        popup = ExtractionSitePopup(
            game_state=self.game_state,
            colony=colony,
            on_build=self._refresh_details,
        )
        popup.open()

    def _build_factory(self, instance):
        if not self.game_state or not self.selected_colony_id:
            return
        success, message = self.game_state.build_factory(self.selected_colony_id)
        if not success:
            NoticePopup(title="Build Blocked", message=message).open()
            return
        self._refresh_details()

    def _update_factory_button(self, colony):
        cost = self.game_state.production.config.factory_balance.get("factory_build_cost", {})
        cost_text = ", ".join(f"{v} {k}" for k, v in cost.items()) if cost else "free"
        max_by_level = self.game_state.production.config.factory_balance.get(
            "max_factories_per_colony_level", {}
        )
        max_factories = int(max_by_level.get(str(colony.level), 0))
        limit_reached = len(colony.factories) >= max_factories
        can_afford = self.game_state.can_afford_production_cost(
            colony.production_inventory,
            cost,
        )
        self.factory_build_btn.text = f"Build Factory ({cost_text})"
        self.factory_build_btn.disabled = limit_reached or not can_afford
        self.factory_build_btn.background_color = (
            (0.2, 0.3, 0.45, 0.9)
            if can_afford and not limit_reached
            else (0.2, 0.2, 0.2, 0.5)
        )
        self.factory_build_btn.color = (
            (0.8, 0.9, 1, 1)
            if can_afford and not limit_reached
            else (0.4, 0.4, 0.4, 0.5)
        )

    def _update_extraction_button(self, colony):
        cost = self.game_state.production.config.extraction_balance.get(
            "extraction_site_build_cost", {}
        )
        cost_text = ", ".join(f"{v} {k}" for k, v in cost.items()) if cost else "free"
        max_sites = self.game_state.production.config.extraction_balance.get(
            "max_extraction_sites_per_colony", 0
        )
        limit_reached = max_sites and len(colony.extraction_sites) >= max_sites
        can_afford = self.game_state.can_afford_production_cost(
            colony.production_inventory,
            cost,
        )
        self.extraction_build_btn.text = f"Add Extraction Site ({cost_text})"
        self.extraction_build_btn.disabled = limit_reached or not can_afford
        self.extraction_build_btn.background_color = (
            (0.15, 0.35, 0.2, 0.9)
            if can_afford and not limit_reached
            else (0.2, 0.2, 0.2, 0.5)
        )
        self.extraction_build_btn.color = (
            (0.3, 1, 0.5, 1)
            if can_afford and not limit_reached
            else (0.4, 0.4, 0.4, 0.5)
        )

    def _go_back(self, instance):
        self.manager.current = "galaxy_map"
