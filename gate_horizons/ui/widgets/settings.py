"""Settings popup for Gate Horizons."""

from kivy.uix.boxlayout import BoxLayout
from kivy.uix.button import Button
from kivy.uix.checkbox import CheckBox
from kivy.uix.label import Label
from kivy.uix.popup import Popup
from kivy.uix.slider import Slider
from kivy.metrics import dp

from gate_horizons.game.settings import GameSettings


class SettingsPopup(Popup):
    """Popup for editing persistent settings."""

    def __init__(self, settings: GameSettings, on_save=None, **kwargs):
        self.settings = settings
        self.on_save_callback = on_save

        content = BoxLayout(orientation="vertical", spacing=dp(10), padding=dp(12))

        header = Label(
            text="Settings",
            font_size="16sp",
            bold=True,
            color=(0.3, 0.85, 1, 1),
            size_hint_y=None,
            height=dp(30),
        )
        content.add_widget(header)

        self._music_label = Label(
            text=self._volume_label("Music Volume", self.settings.music_volume),
            font_size="12sp",
            color=(0.7, 0.85, 1, 0.9),
            size_hint_y=None,
            height=dp(22),
        )
        content.add_widget(self._music_label)

        self._music_slider = Slider(
            min=0.0,
            max=1.0,
            value=self.settings.music_volume,
            step=0.05,
        )
        self._music_slider.bind(value=self._on_music_change)
        content.add_widget(self._music_slider)

        self._sfx_label = Label(
            text=self._volume_label("SFX Volume", self.settings.sfx_volume),
            font_size="12sp",
            color=(0.7, 0.85, 1, 0.9),
            size_hint_y=None,
            height=dp(22),
        )
        content.add_widget(self._sfx_label)

        self._sfx_slider = Slider(
            min=0.0,
            max=1.0,
            value=self.settings.sfx_volume,
            step=0.05,
        )
        self._sfx_slider.bind(value=self._on_sfx_change)
        content.add_widget(self._sfx_slider)

        autosave_row = BoxLayout(
            orientation="horizontal",
            size_hint_y=None,
            height=dp(30),
            spacing=dp(8),
        )
        autosave_row.add_widget(Label(
            text="Enable autosave",
            font_size="12sp",
            color=(0.7, 0.85, 1, 0.9),
            size_hint_x=0.8,
        ))
        self._autosave_checkbox = CheckBox(
            active=self.settings.autosave_enabled,
            size_hint_x=0.2,
        )
        autosave_row.add_widget(self._autosave_checkbox)
        content.add_widget(autosave_row)

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
            title="Settings",
            content=content,
            size_hint=(0.45, 0.6),
            title_color=(0.3, 0.85, 1, 1),
            separator_color=(0.15, 0.6, 0.8, 0.6),
            background_color=(0.04, 0.06, 0.12, 0.95),
            **kwargs,
        )

    def _volume_label(self, label: str, value: float) -> str:
        percent = int(round(value * 100))
        return f"{label}: {percent}%"

    def _on_music_change(self, slider, value):
        self._music_label.text = self._volume_label("Music Volume", value)

    def _on_sfx_change(self, slider, value):
        self._sfx_label.text = self._volume_label("SFX Volume", value)

    def _on_save(self, *args):
        self.settings.music_volume = self._music_slider.value
        self.settings.sfx_volume = self._sfx_slider.value
        self.settings.autosave_enabled = self._autosave_checkbox.active
        self.settings.clamp()
        if self.on_save_callback:
            self.on_save_callback(self.settings)
        self.dismiss()
