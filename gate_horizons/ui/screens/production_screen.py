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
from kivy.graphics import Color, Rectangle
from kivy.metrics import dp

from ..widgets.resource_bar import TopBar


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
            halign="left", valign="top",
            size_hint_y=None, height=dp(200),
        )
        self.inventory_label.bind(size=self.inventory_label.setter("text_size"))

        # Extraction section
        self.extraction_label = Label(
            text="", font_size="12sp", color=(0.7, 0.9, 0.7, 1),
            halign="left", valign="top",
            size_hint_y=None, height=dp(150),
        )
        self.extraction_label.bind(size=self.extraction_label.setter("text_size"))

        # Factory section
        self.factory_label = Label(
            text="", font_size="12sp", color=(0.9, 0.7, 0.3, 1),
            halign="left", valign="top",
            size_hint_y=None, height=dp(150),
        )
        self.factory_label.bind(size=self.factory_label.setter("text_size"))

        # Factory action buttons
        self.factory_buttons = BoxLayout(
            orientation="horizontal", size_hint_y=None, height=dp(40), spacing=dp(4),
        )
        for recipe in [
            "metal_alloys", "polymers", "fuel", "electronics",
            "hull_segments", "reactor_parts", "habitat_modules", "cargo_frames",
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
        details_box.add_widget(self.factory_label)
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
            "ore_iron", "silicates", "water_ice", "gas_h2", "organics", "rare_metals",
        ]}
        processed = {k: v for k, v in inv.items() if k in [
            "metal_alloys", "polymers", "fuel", "electronics",
        ]}
        components = {k: v for k, v in inv.items() if k in [
            "hull_segments", "reactor_parts", "habitat_modules", "cargo_frames",
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

    def _queue_recipe(self, instance):
        if not self.game_state or not self.selected_colony_id:
            return
        colony = self.game_state.colonies.colonies.get(self.selected_colony_id)
        if not colony or not colony.factories:
            return
        # Queue to first factory
        colony.factories[0].queue_recipe(instance.recipe_id)
        self._refresh_details()

    def _go_back(self, instance):
        self.manager.current = "galaxy_map"
