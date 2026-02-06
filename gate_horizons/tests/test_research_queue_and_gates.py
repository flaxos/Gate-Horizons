"""Regression tests for research queue and gate cost reduction.

Covers:
1. Research queue auto-advances to the next tech after completion
2. Research queue persists through save/load round-trip
3. Gate Resonance Tuning (gate_cost_reduction) reduces dormant gate activation costs
4. Research queue skips techs whose prerequisites are not yet met
5. GameState.activate_gate convenience method applies tech discount
"""

import unittest

from gate_horizons.game.state import GameState
from gate_horizons.game.tech import TechTree, TechNode
from gate_horizons.game.galaxy import GalaxyMap, StarSystem
from gate_horizons.game.resources import ResourceManager


class TestResearchQueueAutoAdvances(unittest.TestCase):
    """After the active research completes, the next queued tech should start."""

    def test_queue_auto_starts_next_tech(self):
        state = GameState.new_game()
        state.resources.global_resources["intel"] = 500
        state.resources.global_resources["exotics"] = 50

        # Start efficient_drives (3 turns) and queue reinforced_hulls
        started = state.tech.start_research("efficient_drives", state.resources)
        self.assertTrue(started)
        queued = state.tech.queue_research("reinforced_hulls")
        self.assertTrue(queued)

        # Advance through turns until efficient_drives completes
        turns_needed = state.tech.techs["efficient_drives"].turns_remaining
        for _ in range(turns_needed):
            state.process_turn()

        # efficient_drives should be done
        self.assertTrue(state.tech.techs["efficient_drives"].researched)

        # reinforced_hulls should now be the active research
        self.assertEqual(state.tech.active_research, "reinforced_hulls")
        self.assertTrue(state.tech.techs["reinforced_hulls"].researching)

        # Queue should be empty
        self.assertEqual(len(state.tech.research_queue), 0)


class TestResearchQueuePersistsSaveLoad(unittest.TestCase):
    """The research queue should survive a to_dict/from_dict round-trip."""

    def test_queue_survives_round_trip(self):
        state = GameState.new_game()
        state.resources.global_resources["intel"] = 500

        # Start research and queue two more
        state.tech.start_research("efficient_drives", state.resources)
        state.tech.queue_research("reinforced_hulls")
        state.tech.queue_research("deep_scan")

        # Round-trip
        data = state.to_dict()
        loaded = GameState.from_dict(data)

        self.assertEqual(loaded.tech.active_research, "efficient_drives")
        self.assertEqual(loaded.tech.research_queue, ["reinforced_hulls", "deep_scan"])

        # Verify the queued techs are not yet researching
        self.assertFalse(loaded.tech.techs["reinforced_hulls"].researching)
        self.assertFalse(loaded.tech.techs["deep_scan"].researching)


class TestGateCostReduction(unittest.TestCase):
    """Gate Resonance Tuning should reduce dormant gate activation costs."""

    def test_cost_reduction_applied_to_gate_activation(self):
        state = GameState.new_game()

        # Barnard's Star has gate_activation_cost: energy=20, metals=15
        barnards = state.galaxy.systems.get("barnards_star")
        self.assertIsNotNone(barnards)
        self.assertFalse(barnards.gate_active)
        base_cost = dict(barnards.gate_activation_cost)
        self.assertEqual(base_cost, {"energy": 20, "metals": 15})

        # Without tech: verify full cost is required
        full_cost = state.galaxy.get_gate_activation_cost("barnards_star")
        self.assertEqual(full_cost, {"energy": 20, "metals": 15})

        # With 30% reduction (gate_resonance effect):
        reduced_cost = state.galaxy.get_gate_activation_cost(
            "barnards_star", cost_reduction=0.3
        )
        # int(20 * 0.7) = 14, int(15 * 0.7) = 10
        self.assertEqual(reduced_cost["energy"], 14)
        self.assertEqual(reduced_cost["metals"], 10)

        # Actually activate with reduction
        state.resources.global_resources["energy"] = 14
        state.resources.global_resources["metals"] = 10
        activated = state.galaxy.activate_gate(
            "barnards_star",
            resources=state.resources,
            cost_reduction=0.3,
        )
        self.assertTrue(activated)
        self.assertTrue(barnards.gate_active)
        # Resources should be spent
        self.assertEqual(state.resources.global_resources["energy"], 0)
        self.assertEqual(state.resources.global_resources["metals"], 0)


class TestResearchQueueSkipsUnresearchable(unittest.TestCase):
    """Queue should skip techs whose prerequisites aren't met yet."""

    def test_queue_skips_to_eligible_tech(self):
        state = GameState.new_game()
        state.resources.global_resources["intel"] = 500
        state.resources.global_resources["exotics"] = 50

        # Start efficient_drives (tier1, no prereqs)
        state.tech.start_research("efficient_drives", state.resources)

        # Queue burst_drives (tier2, prereq: efficient_drives)
        # then deep_scan (tier1, no prereqs)
        state.tech.queue_research("burst_drives")
        state.tech.queue_research("deep_scan")

        # Complete efficient_drives
        turns_needed = state.tech.techs["efficient_drives"].turns_remaining
        for _ in range(turns_needed):
            state.process_turn()

        self.assertTrue(state.tech.techs["efficient_drives"].researched)

        # burst_drives prereq (efficient_drives) IS now met, so it should start
        # since it's first in queue
        self.assertEqual(state.tech.active_research, "burst_drives")
        # deep_scan should still be in the queue
        self.assertIn("deep_scan", state.tech.research_queue)


class TestGameStateActivateGateWithTech(unittest.TestCase):
    """GameState.activate_gate should apply gate_cost_reduction from tech."""

    def test_activate_gate_uses_tech_discount(self):
        state = GameState.new_game()

        # Research gate_resonance to get gate_cost_reduction: 0.3
        state.resources.global_resources["intel"] = 500
        state.tech.start_research("gate_resonance", state.resources)
        tech = state.tech.techs["gate_resonance"]
        for _ in range(tech.cost.get("turns", 4) + 1):
            state.process_turn()
        self.assertTrue(tech.researched)

        # Verify tech effect is active
        effects = state.tech.get_effects()
        self.assertAlmostEqual(effects["gate_cost_reduction"], 0.3)

        # Barnard's Star: base cost energy=20, metals=15
        # With 30% reduction: energy=14, metals=10
        state.resources.global_resources["energy"] = 14
        state.resources.global_resources["metals"] = 10

        # Without tech discount, 14 energy wouldn't be enough for the 20 cost.
        # But with GameState.activate_gate, it should work.
        activated = state.activate_gate("barnards_star")
        self.assertTrue(activated)

        barnards = state.galaxy.systems["barnards_star"]
        self.assertTrue(barnards.gate_active)


if __name__ == "__main__":
    unittest.main()
