"""Content tests for event library size and schema."""

import json
from importlib import resources


def _load_events() -> list[dict]:
    base = resources.files("gate_horizons").joinpath("data", "events")
    events = []
    for entry in base.iterdir():
        if entry.suffix != ".json":
            continue
        data = json.loads(entry.read_text(encoding="utf-8"))
        if isinstance(data, dict):
            for value in data.values():
                if isinstance(value, list):
                    events.extend(value)
        elif isinstance(data, list):
            events.extend(data)
    return events


def test_event_library_has_minimum_count():
    events = _load_events()
    assert len(events) >= 100


def test_event_schema_is_consistent():
    events = _load_events()
    for event in events:
        assert event.get("id")
        assert event.get("title")
        assert event.get("description")
        choices = event.get("choices")
        assert isinstance(choices, list) and choices
        for choice in choices:
            outcomes = choice.get("outcomes")
            assert isinstance(outcomes, list) and outcomes
            for outcome in outcomes:
                assert "probability" in outcome
                assert "result" in outcome
                assert "description" in outcome
