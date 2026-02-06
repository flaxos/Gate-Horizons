"""Context menu widget for ship/system actions in Gate Horizons."""

from kivy.uix.boxlayout import BoxLayout
from kivy.uix.button import Button
from kivy.uix.label import Label
from kivy.uix.popup import Popup
from kivy.uix.scrollview import ScrollView
from kivy.metrics import dp


class ActionButton(Button):
    pass


class ContextMenu(Popup):
    """Modal context menu showing available actions for a ship or system."""

    def __init__(self, title_text="Actions", actions=None, callback=None, **kwargs):
        self.action_callback = callback

        content = BoxLayout(orientation="vertical", spacing=dp(4), padding=dp(8))

        scroll = ScrollView(size_hint=(1, 1))
        action_list = BoxLayout(
            orientation="vertical",
            spacing=dp(4),
            size_hint_y=None,
        )
        action_list.bind(minimum_height=action_list.setter("height"))

        for action in (actions or []):
            btn_text = action.name
            if action.cost:
                costs = ", ".join(f"{v} {k}" for k, v in action.cost.items())
                btn_text += f"\n  Cost: {costs}"
            if action.risk != "none":
                btn_text += f"  [{action.risk} risk]"

            btn = Button(
                text=btn_text,
                size_hint_y=None,
                height=dp(48),
                font_size="13sp",
                halign="left",
                valign="middle",
                text_size=(None, None),
                background_color=(0.12, 0.25, 0.4, 0.8),
                color=(0.85, 0.95, 1, 1),
            )
            btn.action = action
            btn.bind(on_release=self._on_action)
            action_list.add_widget(btn)

        # Cancel button
        cancel_btn = Button(
            text="Cancel",
            size_hint_y=None,
            height=dp(44),
            font_size="13sp",
            background_color=(0.3, 0.1, 0.1, 0.8),
            color=(1, 0.7, 0.7, 1),
        )
        cancel_btn.bind(on_release=lambda x: self.dismiss())
        action_list.add_widget(cancel_btn)

        scroll.add_widget(action_list)
        content.add_widget(scroll)

        super().__init__(
            title=title_text,
            content=content,
            size_hint=(0.4, 0.6),
            title_color=(0.3, 0.85, 1, 1),
            separator_color=(0.15, 0.6, 0.8, 0.6),
            background_color=(0.04, 0.06, 0.12, 0.95),
            **kwargs,
        )

    def _on_action(self, btn):
        self.dismiss()
        if self.action_callback and hasattr(btn, "action"):
            self.action_callback(btn.action)


class DestinationMenu(Popup):
    """Menu for selecting a destination system."""

    def __init__(self, systems=None, callback=None, **kwargs):
        self.dest_callback = callback

        content = BoxLayout(orientation="vertical", spacing=dp(4), padding=dp(8))

        scroll = ScrollView(size_hint=(1, 1))
        sys_list = BoxLayout(
            orientation="vertical",
            spacing=dp(4),
            size_hint_y=None,
        )
        sys_list.bind(minimum_height=sys_list.setter("height"))

        for system in (systems or []):
            status = ""
            if not system.gate_active:
                status = " [DORMANT]"
            elif not system.discovered:
                status = " [?]"

            btn = Button(
                text=f"{system.name}{status}",
                size_hint_y=None,
                height=dp(40),
                font_size="13sp",
                background_color=(0.12, 0.25, 0.4, 0.8),
                color=(0.85, 0.95, 1, 1),
            )
            btn.system_id = system.id
            btn.bind(on_release=self._on_select)
            sys_list.add_widget(btn)

        cancel_btn = Button(
            text="Cancel",
            size_hint_y=None,
            height=dp(44),
            font_size="13sp",
            background_color=(0.3, 0.1, 0.1, 0.8),
            color=(1, 0.7, 0.7, 1),
        )
        cancel_btn.bind(on_release=lambda x: self.dismiss())
        sys_list.add_widget(cancel_btn)

        scroll.add_widget(sys_list)
        content.add_widget(scroll)

        super().__init__(
            title="Select Destination",
            content=content,
            size_hint=(0.35, 0.5),
            title_color=(0.3, 0.85, 1, 1),
            separator_color=(0.15, 0.6, 0.8, 0.6),
            background_color=(0.04, 0.06, 0.12, 0.95),
            **kwargs,
        )

    def _on_select(self, btn):
        self.dismiss()
        if self.dest_callback and hasattr(btn, "system_id"):
            self.dest_callback(btn.system_id)
