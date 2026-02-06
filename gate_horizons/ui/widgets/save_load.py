"""Save/Load UI widgets for Gate Horizons."""

from kivy.uix.boxlayout import BoxLayout
from kivy.uix.button import Button
from kivy.uix.label import Label
from kivy.uix.widget import Widget
from kivy.uix.scrollview import ScrollView
from kivy.uix.popup import Popup
from kivy.uix.textinput import TextInput
from kivy.graphics import Color, Rectangle
from kivy.metrics import dp


class SaveGamePopup(Popup):
    """Popup for saving the current game."""

    def __init__(self, save_manager=None, game_state=None, on_saved=None, **kwargs):
        self.save_manager = save_manager
        self.game_state = game_state
        self.saved_callback = on_saved

        content = BoxLayout(orientation="vertical", spacing=dp(8), padding=dp(12))

        content.add_widget(Label(
            text="Save Game",
            font_size="16sp",
            bold=True,
            color=(0.3, 0.85, 1, 1),
            size_hint_y=None,
            height=dp(30),
        ))

        # Save name input
        name_row = BoxLayout(orientation="horizontal", size_hint_y=None, height=dp(36))
        name_row.add_widget(Label(
            text="Save Name:",
            font_size="12sp",
            color=(0.7, 0.85, 1, 0.9),
            size_hint_x=0.3,
        ))
        self.name_input = TextInput(
            text=f"Save Turn {game_state.turn_number}" if game_state else "Save",
            font_size="12sp",
            multiline=False,
            size_hint_x=0.7,
            background_color=(0.1, 0.12, 0.18, 0.9),
            foreground_color=(0.8, 0.9, 1, 1),
        )
        name_row.add_widget(self.name_input)
        content.add_widget(name_row)

        # Existing saves list
        content.add_widget(Label(
            text="Existing Saves (click to overwrite):",
            font_size="11sp",
            color=(0.5, 0.7, 0.9, 0.7),
            size_hint_y=None,
            height=dp(22),
            halign="left",
            text_size=(dp(380), None),
        ))

        scroll = ScrollView(size_hint=(1, 1))
        save_list = BoxLayout(
            orientation="vertical",
            spacing=dp(4),
            size_hint_y=None,
        )
        save_list.bind(minimum_height=save_list.setter("height"))

        if save_manager:
            saves = save_manager.list_saves()
            for save in saves:
                btn = Button(
                    text=f"{save['save_name']} | Turn {save['turn_number']} | {save['timestamp'][:16]}",
                    size_hint_y=None,
                    height=dp(36),
                    font_size="11sp",
                    background_color=(0.12, 0.25, 0.4, 0.8),
                    color=(0.85, 0.95, 1, 1),
                )
                btn.save_name = save['save_name']
                btn.bind(on_release=lambda b: setattr(self.name_input, 'text', b.save_name))
                save_list.add_widget(btn)

        if not save_list.children:
            save_list.add_widget(Label(
                text="No existing saves",
                font_size="12sp",
                color=(0.5, 0.5, 0.6, 0.7),
                size_hint_y=None,
                height=dp(30),
            ))

        scroll.add_widget(save_list)
        content.add_widget(scroll)

        # Buttons
        btn_row = BoxLayout(orientation="horizontal", size_hint_y=None, height=dp(44), spacing=dp(8))

        save_btn = Button(
            text="Save",
            font_size="14sp",
            bold=True,
            background_color=(0.15, 0.4, 0.2, 0.9),
            color=(0.3, 1, 0.5, 1),
        )
        save_btn.bind(on_release=self._on_save)
        btn_row.add_widget(save_btn)

        cancel_btn = Button(
            text="Cancel",
            font_size="14sp",
            background_color=(0.3, 0.1, 0.1, 0.8),
            color=(1, 0.7, 0.7, 1),
        )
        cancel_btn.bind(on_release=lambda x: self.dismiss())
        btn_row.add_widget(cancel_btn)

        content.add_widget(btn_row)

        super().__init__(
            title="Save Game",
            content=content,
            size_hint=(0.5, 0.65),
            title_color=(0.3, 0.85, 1, 1),
            separator_color=(0.15, 0.6, 0.8, 0.6),
            background_color=(0.04, 0.06, 0.12, 0.95),
            **kwargs,
        )

    def _on_save(self, *args):
        name = self.name_input.text.strip()
        if not name:
            return
        if self.save_manager and self.game_state:
            self.save_manager.save_game(self.game_state, name)
        self.dismiss()
        if self.saved_callback:
            self.saved_callback()


class LoadGamePopup(Popup):
    """Popup for loading a saved game."""

    def __init__(self, save_manager=None, on_load=None, on_delete=None, **kwargs):
        self.save_manager = save_manager
        self.load_callback = on_load
        self.delete_callback = on_delete

        content = BoxLayout(orientation="vertical", spacing=dp(8), padding=dp(12))

        content.add_widget(Label(
            text="Load Game",
            font_size="16sp",
            bold=True,
            color=(0.3, 0.85, 1, 1),
            size_hint_y=None,
            height=dp(30),
        ))

        scroll = ScrollView(size_hint=(1, 1))
        self.save_list = BoxLayout(
            orientation="vertical",
            spacing=dp(4),
            size_hint_y=None,
        )
        self.save_list.bind(minimum_height=self.save_list.setter("height"))

        self._populate_saves()

        scroll.add_widget(self.save_list)
        content.add_widget(scroll)

        # Cancel button
        cancel_btn = Button(
            text="Cancel",
            size_hint_y=None,
            height=dp(44),
            font_size="14sp",
            background_color=(0.3, 0.1, 0.1, 0.8),
            color=(1, 0.7, 0.7, 1),
        )
        cancel_btn.bind(on_release=lambda x: self.dismiss())
        content.add_widget(cancel_btn)

        super().__init__(
            title="Load Game",
            content=content,
            size_hint=(0.55, 0.7),
            title_color=(0.3, 0.85, 1, 1),
            separator_color=(0.15, 0.6, 0.8, 0.6),
            background_color=(0.04, 0.06, 0.12, 0.95),
            **kwargs,
        )

    def _populate_saves(self):
        self.save_list.clear_widgets()
        if not self.save_manager:
            return

        saves = self.save_manager.list_saves()
        if not saves:
            self.save_list.add_widget(Label(
                text="No saved games found",
                font_size="13sp",
                color=(0.5, 0.5, 0.6, 0.7),
                size_hint_y=None,
                height=dp(30),
            ))
            return

        for save in saves:
            row = BoxLayout(orientation="horizontal", size_hint_y=None, height=dp(44), spacing=dp(4))

            load_btn = Button(
                text=f"{save['save_name']} | Turn {save['turn_number']} | {save['timestamp'][:16]}",
                font_size="12sp",
                size_hint_x=0.75,
                background_color=(0.12, 0.25, 0.4, 0.8),
                color=(0.85, 0.95, 1, 1),
            )
            load_btn.save_id = save['id']
            load_btn.bind(on_release=self._on_load)
            row.add_widget(load_btn)

            del_btn = Button(
                text="Delete",
                font_size="11sp",
                size_hint_x=0.25,
                background_color=(0.3, 0.1, 0.1, 0.8),
                color=(1, 0.5, 0.5, 1),
            )
            del_btn.save_id = save['id']
            del_btn.bind(on_release=self._on_delete)
            row.add_widget(del_btn)

            self.save_list.add_widget(row)

    def _on_load(self, btn):
        self.dismiss()
        if self.load_callback:
            self.load_callback(btn.save_id)

    def _on_delete(self, btn):
        if self.save_manager:
            self.save_manager.delete_save(btn.save_id)
        self._populate_saves()
