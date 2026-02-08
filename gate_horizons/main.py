"""Gate Horizons — Main Application Entry Point."""

import logging
import os
import sys

# Ensure the project root is on sys.path so that `from gate_horizons.game.X`
# works even when this file is executed directly (e.g. Pydroid on Android).
# Without this, Pydroid adds gate_horizons/ to the path instead of its parent,
# which makes `import gate_horizons` fail with ModuleNotFoundError.
_project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _project_root not in sys.path:
    sys.path.insert(0, _project_root)

from importlib import resources

# Kivy configuration must be set before importing any kivy modules
os.environ["KIVY_NO_CONSOLELOG"] = "1"
from kivy.config import Config
Config.set("graphics", "width", "1280")
Config.set("graphics", "height", "720")
Config.set("graphics", "resizable", "1")

from kivy.app import App
from kivy.uix.screenmanager import ScreenManager, FadeTransition
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.button import Button
from kivy.uix.label import Label
from kivy.uix.popup import Popup
from kivy.clock import Clock
from kivy.core.window import Window
from kivy.metrics import dp
from gate_horizons.game.state import GameState
from gate_horizons.game.save_load import SaveManager
from gate_horizons.game.settings import SettingsManager, GameSettings

from gate_horizons.ui.screens.main_menu import MainMenuScreen
from gate_horizons.ui.screens.galaxy_map import GalaxyMapScreen
from gate_horizons.ui.screens.system_view import SystemViewScreen
from gate_horizons.ui.screens.colony_screen import ColonyScreen
from gate_horizons.ui.screens.fleet_screen import FleetScreen
from gate_horizons.ui.screens.tech_screen import TechScreen
from gate_horizons.ui.screens.trade_screen import TradeScreen
from gate_horizons.ui.screens.production_screen import ProductionScreen
from gate_horizons.ui.screens.logistics_screen import LogisticsScreen
from gate_horizons.ui.screens.shipyard_screen import ShipyardScreen
from gate_horizons.ui.screens.event_screen import EventPopup
from gate_horizons.ui.widgets.save_load import LoadGamePopup

logger = logging.getLogger("gate_horizons.app")


class ExitConfirmPopup(Popup):
    """Confirmation dialog shown before closing the app."""

    def __init__(self, on_confirm=None, on_cancel=None, **kwargs):
        self._on_confirm = on_confirm
        self._on_cancel = on_cancel

        content = BoxLayout(orientation="vertical", spacing=dp(12), padding=dp(16))

        content.add_widget(Label(
            text="Are you sure you want to exit?\nUnsaved progress will be lost.",
            font_size="14sp",
            color=(0.78, 0.88, 0.96, 1),
            halign="center",
            valign="middle",
            size_hint_y=0.6,
        ))

        btn_row = BoxLayout(
            orientation="horizontal",
            spacing=dp(16),
            size_hint_y=None,
            height=dp(48),
        )

        cancel_btn = Button(
            text="Cancel",
            font_size="14sp",
            background_color=(0.12, 0.25, 0.4, 0.8),
            color=(0.85, 0.95, 1, 1),
        )
        cancel_btn.bind(on_release=self._cancel)
        btn_row.add_widget(cancel_btn)

        exit_btn = Button(
            text="Exit Game",
            font_size="14sp",
            bold=True,
            background_color=(0.5, 0.12, 0.12, 0.9),
            color=(1, 0.85, 0.85, 1),
        )
        exit_btn.bind(on_release=self._confirm)
        btn_row.add_widget(exit_btn)

        content.add_widget(btn_row)

        super().__init__(
            title="Exit Gate Horizons?",
            content=content,
            size_hint=(0.4, 0.35),
            title_color=(0.3, 0.85, 1, 1),
            separator_color=(0.15, 0.6, 0.8, 0.6),
            background_color=(0.04, 0.06, 0.12, 0.95),
            auto_dismiss=True,
            **kwargs,
        )

    def _cancel(self, *args):
        self.dismiss()
        if self._on_cancel:
            self._on_cancel()

    def _confirm(self, *args):
        self.dismiss()
        if self._on_confirm:
            self._on_confirm()


class GateHorizonsApp(App):
    title = "Gate Horizons"

    # Screens that should navigate back to galaxy_map on ESC/back
    _GAME_SCREENS = {
        "system_view", "colony_screen", "fleet_screen", "tech_screen",
        "trade_screen", "production_screen", "logistics_screen",
        "shipyard_screen",
    }

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.game_state = None
        self.save_manager = None
        self.settings_manager = None
        self.settings = None
        self.galaxy_map_screen = None
        self._exit_popup = None

    def build(self):
        # Load theme
        theme_resource = resources.files("gate_horizons").joinpath(
            "ui", "styles", "theme.kv",
        )
        try:
            with resources.as_file(theme_resource) as theme_path:
                if theme_path.exists():
                    from kivy.lang import Builder
                    Builder.load_file(str(theme_path))
        except FileNotFoundError:
            pass

        # Initialize save manager
        save_dir = os.path.join(
            os.path.dirname(os.path.abspath(__file__)),
            "saves",
        )
        os.makedirs(save_dir, exist_ok=True)
        self.save_manager = SaveManager(os.path.join(save_dir, "saves.db"))
        self.settings_manager = SettingsManager(os.path.join(save_dir, "settings.json"))
        self.settings = self.settings_manager.load()

        # Screen manager
        self.sm = ScreenManager(transition=FadeTransition(duration=0.2))

        # Create screens
        self.main_menu_screen = MainMenuScreen()
        self.galaxy_map_screen = GalaxyMapScreen()
        self.system_view_screen = SystemViewScreen()
        self.colony_screen = ColonyScreen()
        self.fleet_screen = FleetScreen()
        self.tech_screen = TechScreen()
        self.trade_screen = TradeScreen()
        self.production_screen = ProductionScreen()
        self.logistics_screen = LogisticsScreen()
        self.shipyard_screen = ShipyardScreen()

        self.sm.add_widget(self.main_menu_screen)
        self.sm.add_widget(self.galaxy_map_screen)
        self.sm.add_widget(self.system_view_screen)
        self.sm.add_widget(self.colony_screen)
        self.sm.add_widget(self.fleet_screen)
        self.sm.add_widget(self.tech_screen)
        self.sm.add_widget(self.trade_screen)
        self.sm.add_widget(self.production_screen)
        self.sm.add_widget(self.logistics_screen)
        self.sm.add_widget(self.shipyard_screen)

        self.sm.current = "main_menu"

        # Bind exit confirmation handlers
        Window.bind(on_request_close=self._on_close_request)
        Window.bind(on_keyboard=self._on_keyboard)

        logger.info("App built: %d screens registered", len(self.sm.screen_names))
        return self.sm

    # ------------------------------------------------------------------
    # Exit confirmation & back navigation
    # ------------------------------------------------------------------

    def _on_close_request(self, *args):
        """Intercept window close to show confirmation dialog."""
        self._show_exit_confirmation()
        return True  # Cancel the default close

    def _on_keyboard(self, window, key, scancode, codepoint, modifier):
        """Handle back button (Android) and Escape key.

        Navigation priority:
        1. On main_menu -> show exit confirmation
        2. On galaxy_map -> navigate to main_menu
        3. On any other game screen -> navigate back to galaxy_map
        """
        if key == 27:  # ESC / Android back
            current = self.sm.current
            if current == "main_menu":
                self._show_exit_confirmation()
            elif current == "galaxy_map":
                self.sm.current = "main_menu"
            elif current in self._GAME_SCREENS:
                self.switch_screen("galaxy_map")
            else:
                self._show_exit_confirmation()
            return True
        return False

    def _show_exit_confirmation(self):
        """Display the exit confirmation popup."""
        if self._exit_popup is not None:
            return  # Already showing
        self._exit_popup = ExitConfirmPopup(
            on_confirm=self._do_exit,
            on_cancel=self._cancel_exit,
        )
        self._exit_popup.bind(on_dismiss=lambda *a: setattr(self, '_exit_popup', None))
        self._exit_popup.open()

    def _do_exit(self):
        """Auto-save and stop the app."""
        self.auto_save()
        self.stop()

    def _cancel_exit(self):
        """Clear exit popup reference."""
        self._exit_popup = None

    def start_new_game(self):
        """Start a fresh game."""
        logger.info("Starting new game")
        self.game_state = GameState.new_game()
        self._push_state_to_screens()
        self.sm.current = "galaxy_map"

    def continue_game(self):
        """Load autosave and continue."""
        loaded = self.save_manager.load_by_name("autosave", GameState)
        if loaded:
            logger.info("Loaded autosave at turn %d", loaded.turn_number)
            self.game_state = loaded
            self._push_state_to_screens()
            self.sm.current = "galaxy_map"
        else:
            # No autosave, start new game
            self.start_new_game()

    def show_load_screen(self):
        """Show save game list with full UI."""
        popup = LoadGamePopup(
            save_manager=self.save_manager,
            on_load=self._load_from_popup,
        )
        popup.open()

    def _load_from_popup(self, save_id):
        """Load a game from the load popup."""
        loaded = self.save_manager.load_game(save_id, GameState)
        if loaded:
            logger.info("Loaded save id=%s at turn %d", save_id, loaded.turn_number)
            self.game_state = loaded
            self._push_state_to_screens()
            self.sm.current = "galaxy_map"

    def switch_screen(self, screen_name):
        """Navigate to a screen, refreshing its data."""
        logger.debug("switch_screen -> %s", screen_name)
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
        logger.info("Showing event: %s", event.title if event else "None")
        popup = EventPopup(
            event=event,
            game_state=self.game_state,
            on_resolved=self._on_event_resolved,
        )
        popup.open()

    def auto_save(self):
        """Auto-save the current game."""
        if not self.settings or not self.settings.autosave_enabled:
            return
        if self.game_state and self.save_manager:
            self.save_manager.auto_save(self.game_state)

    def apply_settings(self, settings: GameSettings):
        """Persist updated settings from the UI."""
        self.settings = settings
        if self.settings_manager:
            self.settings_manager.save(settings)

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
        self.trade_screen.set_game_state(self.game_state)
        self.production_screen.set_game_state(self.game_state)
        self.logistics_screen.set_game_state(self.game_state)
        self.shipyard_screen.set_game_state(self.game_state)


def main():
    GateHorizonsApp().run()


if __name__ == "__main__":
    main()
