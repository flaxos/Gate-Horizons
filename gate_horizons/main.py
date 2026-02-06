"""Gate Horizons — Main Application Entry Point."""

import os
import sys

# Kivy configuration must be set before importing any kivy modules
os.environ["KIVY_NO_CONSOLELOG"] = "1"
from kivy.config import Config
Config.set("graphics", "width", "1280")
Config.set("graphics", "height", "720")
Config.set("graphics", "resizable", "1")

from kivy.app import App
from kivy.uix.screenmanager import ScreenManager, FadeTransition
from kivy.clock import Clock
from kivy.resources import resource_add_path

from game.state import GameState
from game.save_load import SaveManager

from ui.screens.main_menu import MainMenuScreen
from ui.screens.galaxy_map import GalaxyMapScreen
from ui.screens.system_view import SystemViewScreen
from ui.screens.colony_screen import ColonyScreen
from ui.screens.fleet_screen import FleetScreen
from ui.screens.tech_screen import TechScreen
from ui.screens.event_screen import EventPopup


class GateHorizonsApp(App):
    title = "Gate Horizons"

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.game_state = None
        self.save_manager = None
        self.galaxy_map_screen = None

    def build(self):
        # Load theme
        theme_path = os.path.join(
            os.path.dirname(os.path.abspath(__file__)),
            "ui", "styles", "theme.kv",
        )
        if os.path.exists(theme_path):
            from kivy.lang import Builder
            Builder.load_file(theme_path)

        # Initialize save manager
        save_dir = os.path.join(
            os.path.dirname(os.path.abspath(__file__)),
            "saves",
        )
        os.makedirs(save_dir, exist_ok=True)
        self.save_manager = SaveManager(os.path.join(save_dir, "saves.db"))

        # Screen manager
        self.sm = ScreenManager(transition=FadeTransition(duration=0.2))

        # Create screens
        self.main_menu_screen = MainMenuScreen()
        self.galaxy_map_screen = GalaxyMapScreen()
        self.system_view_screen = SystemViewScreen()
        self.colony_screen = ColonyScreen()
        self.fleet_screen = FleetScreen()
        self.tech_screen = TechScreen()

        self.sm.add_widget(self.main_menu_screen)
        self.sm.add_widget(self.galaxy_map_screen)
        self.sm.add_widget(self.system_view_screen)
        self.sm.add_widget(self.colony_screen)
        self.sm.add_widget(self.fleet_screen)
        self.sm.add_widget(self.tech_screen)

        self.sm.current = "main_menu"
        return self.sm

    def start_new_game(self):
        """Start a fresh game."""
        self.game_state = GameState.new_game()
        self._push_state_to_screens()
        self.sm.current = "galaxy_map"

    def continue_game(self):
        """Load autosave and continue."""
        loaded = self.save_manager.load_by_name("autosave", GameState)
        if loaded:
            self.game_state = loaded
            self._push_state_to_screens()
            self.sm.current = "galaxy_map"
        else:
            # No autosave, start new game
            self.start_new_game()

    def show_load_screen(self):
        """Show save game list (simplified: load most recent)."""
        saves = self.save_manager.list_saves()
        if saves:
            # Load most recent non-autosave, or autosave
            for save in saves:
                loaded = self.save_manager.load_game(save["id"], GameState)
                if loaded:
                    self.game_state = loaded
                    self._push_state_to_screens()
                    self.sm.current = "galaxy_map"
                    return

        # No saves found
        self.start_new_game()

    def switch_screen(self, screen_name):
        """Navigate to a screen, refreshing its data."""
        if self.game_state:
            self._push_state_to_screens()
        self.sm.current = screen_name

    def show_system_view(self, system_id):
        """Navigate to system detail view."""
        if self.game_state:
            self.system_view_screen.set_system(self.game_state, system_id)
        self.sm.current = "system_view"

    def show_event(self, event):
        """Show an event popup."""
        popup = EventPopup(
            event=event,
            game_state=self.game_state,
            on_resolved=self._on_event_resolved,
        )
        popup.open()

    def auto_save(self):
        """Auto-save the current game."""
        if self.game_state and self.save_manager:
            self.save_manager.auto_save(self.game_state)

    def _on_event_resolved(self):
        """Called after an event is resolved. Show next pending event or refresh."""
        if self.game_state and self.game_state.events.event_queue:
            next_event = self.game_state.events.event_queue[0]
            self.show_event(next_event)
        else:
            self._push_state_to_screens()
            self.auto_save()

    def _push_state_to_screens(self):
        """Push current game state to all screens."""
        if not self.game_state:
            return
        self.galaxy_map_screen.set_game_state(self.game_state)
        self.colony_screen.set_game_state(self.game_state)
        self.fleet_screen.set_game_state(self.game_state)
        self.tech_screen.set_game_state(self.game_state)


def main():
    GateHorizonsApp().run()


if __name__ == "__main__":
    main()
