"""Content tests for the tech tree data."""

import json
from importlib import resources

from gate_horizons.game.tech import TechTree


def test_tech_tree_has_full_set():
    path = resources.files("gate_horizons").joinpath("data", "tech_tree.json")
    data = json.loads(path.read_text(encoding="utf-8"))

    tech_count = 0
    for branch in data.values():
        for tier in branch.values():
            tech_count += len(tier)

    assert tech_count >= 20


def test_new_tier_three_techs_loaded():
    path = resources.files("gate_horizons").joinpath("data", "tech_tree.json")
    tree = TechTree()
    tree.load_from_json(path)

    for tech_id in ("long_range_drives", "hardened_plating", "battlefield_simulation"):
        assert tech_id in tree.techs
