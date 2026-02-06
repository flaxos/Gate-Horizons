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
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.button import Button
from kivy.uix.label import Label
from kivy.uix.popup import Popup
from kivy.clock import Clock
from kivy.core.window import Window
from kivy.metrics import dp
from kivy.resources import resource_add_path

from game.state import GameState
from game.save_load import SaveManager

from ui.screens.main_menu import MainMenuScreen
from ui.screens.galaxy_map import GalaxyMapScreen
from ui.screens.system_view import SystemViewScreen
from ui.screens.colony_screen import ColonyScreen
from ui.screens.fleet_screen import FleetScreen
from ui.screens.tech_screen import TechScreen
from ui.screens.trade_screen import TradeScreen
from ui.screens.event_screen import EventPopup
from ui.widgets.save_load import LoadGamePopup


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

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.game_state = None
        self.save_manager = None
        self.galaxy_map_screen = None
        self._exit_popup = None

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
        self.trade_screen = TradeScreen()

        self.sm.add_widget(self.main_menu_screen)
        self.sm.add_widget(self.galaxy_map_screen)
        self.sm.add_widget(self.system_view_screen)
        self.sm.add_widget(self.colony_screen)
        self.sm.add_widget(self.fleet_screen)
        self.sm.add_widget(self.tech_screen)
        self.sm.add_widget(self.trade_screen)

        self.sm.current = "main_menu"

        # Bind exit confirmation handlers
        Window.bind(on_request_close=self._on_close_request)
        Window.bind(on_keyboard=self._on_keyboard)

        return self.sm

    # ------------------------------------------------------------------
    # Exit confirmation
    # ------------------------------------------------------------------

    def _on_close_request(self, *args):
        """Intercept window close to show confirmation dialog."""
        self._show_exit_confirmation()
        return True  # Cancel the default close

    def _on_keyboard(self, window, key, scancode, codepoint, modifier):
        """Handle back button (Android) and Escape key."""
        if key == 27:  # ESC / Android back
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
            self.game_state = loaded
            self._push_state_to_screens()
            self.sm.current = "galaxy_map"

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
        self.trade_screen.set_game_state(self.game_state)


def main():
    GateHorizonsApp().run()


if __name__ == "__main__":
    main()
