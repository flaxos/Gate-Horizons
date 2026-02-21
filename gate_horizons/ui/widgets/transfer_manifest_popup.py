"""Popup helpers for parameterized cargo/colonist transfer actions."""

from __future__ import annotations

from kivy.metrics import dp
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.button import Button
from kivy.uix.label import Label
from kivy.uix.popup import Popup
from kivy.uix.textinput import TextInput
from kivy.uix.widget import Widget


class TransferManifestPopup(Popup):
    """Collect optional transfer parameters for ship cargo/colonist actions."""

    _CARGO_ACTIONS = {"Load Cargo", "Unload Cargo"}
    _COLONIST_ACTIONS = {"Load Colonists", "Unload Colonists"}

    def __init__(self, action_name: str, on_submit=None, **kwargs):
        self.action_name = action_name
        self._on_submit = on_submit

        content = BoxLayout(orientation="vertical", spacing=dp(8), padding=dp(12))
        self._error_label = Label(
            text="",
            font_size="11sp",
            color=(1, 0.45, 0.35, 1),
            size_hint_y=None,
            height=dp(18),
            halign="left",
            text_size=(dp(340), None),
        )

        self._manifest_input = None
        self._amount_input = None

        if action_name in self._CARGO_ACTIONS:
            content.add_widget(Label(
                text="Manifest (optional): resource=amount, comma-separated",
                font_size="11sp",
                color=(0.72, 0.86, 1, 0.9),
                size_hint_y=None,
                height=dp(24),
                halign="left",
                text_size=(dp(340), None),
            ))
            self._manifest_input = TextInput(
                multiline=False,
                hint_text="metals=10, fuel=5",
                size_hint_y=None,
                height=dp(36),
                font_size="12sp",
            )
            content.add_widget(self._manifest_input)

        if action_name in self._COLONIST_ACTIONS:
            content.add_widget(Label(
                text="Amount (optional): leave blank for max possible",
                font_size="11sp",
                color=(0.72, 0.86, 1, 0.9),
                size_hint_y=None,
                height=dp(24),
                halign="left",
                text_size=(dp(340), None),
            ))
            self._amount_input = TextInput(
                multiline=False,
                hint_text="e.g. 5",
                size_hint_y=None,
                height=dp(36),
                font_size="12sp",
                input_filter="int",
            )
            content.add_widget(self._amount_input)

        content.add_widget(self._error_label)

        button_row = BoxLayout(orientation="horizontal", spacing=dp(8), size_hint_y=None, height=dp(40))
        submit_btn = Button(
            text="Transfer",
            font_size="12sp",
            background_color=(0.15, 0.35, 0.22, 0.9),
            color=(0.8, 1, 0.85, 1),
        )
        submit_btn.bind(on_release=self._submit)
        button_row.add_widget(submit_btn)

        cancel_btn = Button(
            text="Cancel",
            font_size="12sp",
            background_color=(0.3, 0.1, 0.1, 0.8),
            color=(1, 0.7, 0.7, 1),
        )
        cancel_btn.bind(on_release=lambda *_: self.dismiss())
        button_row.add_widget(cancel_btn)
        content.add_widget(button_row)
        content.add_widget(Widget())

        super().__init__(
            title=f"{action_name} Parameters",
            content=content,
            size_hint=(0.48, 0.42),
            title_color=(0.3, 0.85, 1, 1),
            separator_color=(0.15, 0.6, 0.8, 0.6),
            background_color=(0.04, 0.06, 0.12, 0.95),
            **kwargs,
        )

    @staticmethod
    def parse_manifest_text(raw_text: str) -> tuple[dict | None, str | None]:
        text = (raw_text or "").strip()
        if not text:
            return None, None
        manifest = {}
        for token in text.split(","):
            piece = token.strip()
            if not piece:
                continue
            if "=" not in piece:
                return None, f"Invalid manifest entry: '{piece}'"
            resource, amount_text = piece.split("=", 1)
            resource = resource.strip()
            if not resource:
                return None, "Manifest resource cannot be empty"
            try:
                amount = int(amount_text.strip())
            except (TypeError, ValueError):
                return None, f"Invalid amount for {resource}: {amount_text.strip()}"
            if amount < 0:
                return None, f"Invalid amount for {resource}: {amount}"
            if amount > 0:
                manifest[resource] = amount
        return manifest, None

    @staticmethod
    def parse_amount_text(raw_text: str) -> tuple[int | None, str | None]:
        text = (raw_text or "").strip()
        if not text:
            return None, None
        try:
            amount = int(text)
        except (TypeError, ValueError):
            return None, f"Invalid transfer amount: {raw_text}"
        if amount < 0:
            return None, f"Invalid transfer amount: {raw_text}"
        return amount, None

    def _submit(self, *_):
        params = {}
        if self._manifest_input is not None:
            manifest, manifest_error = self.parse_manifest_text(self._manifest_input.text)
            if manifest_error:
                self._error_label.text = manifest_error
                return
            if manifest is not None:
                params["manifest"] = manifest
        if self._amount_input is not None:
            amount, amount_error = self.parse_amount_text(self._amount_input.text)
            if amount_error:
                self._error_label.text = amount_error
                return
            if amount is not None:
                params["amount"] = amount

        self.dismiss()
        if self._on_submit:
            self._on_submit(params)
