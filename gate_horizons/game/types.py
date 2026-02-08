"""Shared typing utilities for Gate Horizons."""

from __future__ import annotations

from typing import Protocol


class Traversable(Protocol):
    """Minimal protocol for importlib.resources-style Traversable objects."""

    def read_text(self, encoding: str = "utf-8") -> str:
        ...
