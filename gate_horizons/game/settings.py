"""Persistent settings for Gate Horizons."""

from dataclasses import asdict, dataclass
import json
import os


@dataclass
class GameSettings:
    """User-adjustable settings."""

    music_volume: float = 0.7
    sfx_volume: float = 0.7
    autosave_enabled: bool = True

    def clamp(self) -> "GameSettings":
        """Clamp numeric settings to valid ranges."""
        self.music_volume = _clamp_volume(self.music_volume, 0.7)
        self.sfx_volume = _clamp_volume(self.sfx_volume, 0.7)
        self.autosave_enabled = bool(self.autosave_enabled)
        return self


class SettingsManager:
    """Load and save settings to disk."""

    def __init__(self, settings_path: str):
        self.settings_path = settings_path

    def load(self) -> GameSettings:
        """Load settings from JSON, returning defaults on error."""
        if not os.path.exists(self.settings_path):
            return GameSettings()

        try:
            with open(self.settings_path, "r", encoding="utf-8") as handle:
                data = json.load(handle)
        except (OSError, json.JSONDecodeError):
            return GameSettings()

        settings = GameSettings(
            music_volume=_clamp_volume(data.get("music_volume"), 0.7),
            sfx_volume=_clamp_volume(data.get("sfx_volume"), 0.7),
            autosave_enabled=_coerce_bool(data.get("autosave_enabled"), True),
        )
        return settings.clamp()

    def save(self, settings: GameSettings) -> None:
        """Persist settings to JSON."""
        os.makedirs(os.path.dirname(self.settings_path), exist_ok=True)
        with open(self.settings_path, "w", encoding="utf-8") as handle:
            json.dump(asdict(settings), handle, indent=2, sort_keys=True)


def _clamp_volume(value, default: float) -> float:
    try:
        numeric = float(value)
    except (TypeError, ValueError):
        numeric = default
    return max(0.0, min(1.0, numeric))


def _coerce_bool(value, default: bool) -> bool:
    if value is None:
        return default
    return bool(value)
