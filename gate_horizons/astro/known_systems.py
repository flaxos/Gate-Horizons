"""Registry for known, handcrafted star systems."""

from __future__ import annotations

import json
from pathlib import Path
from importlib import resources


def _default_known_system_path() -> Path:
    return resources.files("gate_horizons").joinpath("data", "astronomy", "known_systems")


class KnownSystemRegistry:
    def __init__(self, base_path: Path | None = None):
        self.base_path = Path(base_path) if base_path else _default_known_system_path()

    def get_system_data(self, system_id: str) -> dict | None:
        if not system_id:
            return None
        candidates = [
            self.base_path / f"{system_id}.json",
            self.base_path / f"{system_id.lower()}.json",
            self.base_path / f"{system_id.title()}.json",
        ]
        for path in candidates:
            if path.exists():
                with path.open("r", encoding="utf-8") as handle:
                    return json.load(handle)
        return None
