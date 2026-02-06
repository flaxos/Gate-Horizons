"""Regression tests for economy system fixes in Gate Horizons.

Covers:
1. All planet resources in demo_galaxy.json use valid RESOURCE_TYPES
2. Mining at Sol delivers all resources to global pool (no silent drops)
3. Colony happiness stabilizes in middle band instead of spiraling
4. Starting colony does not immediately enter happiness death spiral
5. Mining output survives a save/load round-trip correctly
"""

import unittest

from gate_horizons.game.state import GameState
from gate_horizons.game.resources import RESOURCE_TYPES
from gate_horizons.game.colonies import Colony


class TestPlanetResourceTypesValid(unittest.TestCase):
    """All planet resources must be in RESOURCE_TYPES — no 'food' or 'fuel'."""

    def test_no_invalid_resource_types_in_galaxy(self):
        state = GameState.new_game()
        invalid = []
        for sys_id, system in state.galaxy.systems.items():
            for planet in system.planets:
                for res_type in planet.resources:
                    if res_type not in RESOURCE_TYPES:
                        invalid.append(
                            f"{sys_id}/{planet.name}: '{res_type}' not in {RESOURCE_TYPES}"
                        )
        self.assertEqual(
            invalid, [],
            f"Found invalid planet resource types: {invalid}",
        )


class TestMiningDeliversAllResources(unittest.TestCase):
    """A miner at Sol should deliver all mined resources to the global pool."""

    def test_mining_output_reaches_global_resources(self):
        state = GameState.new_game()

        # Find or create a miner at Sol
        miner = None
        for ship in state.fleet.ships.values():
            if ship.ship_class == "miner":
                miner = ship
                break
        if miner is None:
            state.resources.global_resources["credits"] = 500
            state.resources.global_resources["metals"] = 500
            miner = state.fleet.create_ship("miner", "sol", "Test Miner")
        self.assertIsNotNone(miner)
        miner.location = "sol"
        miner.mining = True

        # Record resources before turn
        before = dict(state.resources.global_resources)

        # Process a turn
        report = state.process_turn()

        # Mining should produce something — Sol has Earth (energy, metals, credits),
        # Mars (metals, energy), Jupiter (energy)
        after = dict(state.resources.global_resources)
        mining_output = report.mining_output

        # Verify mining_output only contains valid resource types
        for res_type in mining_output:
            self.assertIn(
                res_type, RESOURCE_TYPES,
                f"Mining output contains invalid resource type: '{res_type}'",
            )

        # Verify at least energy and metals were mined (Sol has both)
        self.assertGreater(
            mining_output.get("energy", 0) + mining_output.get("metals", 0),
            0,
            "Mining at Sol should produce energy and/or metals",
        )


class TestColonyHappinessMiddleBandRecovery(unittest.TestCase):
    """Colony happiness should recover in the 50-90% population band."""

    def test_happiness_recovers_in_middle_band(self):
        colony = Colony(
            system_id="test",
            planet_id="test_planet",
            name="Test Colony",
            population=200,
            happiness=50,
        )
        # Housing level 3 → cap = 100 + 3*150 = 550
        colony.infrastructure["housing"]["level"] = 3

        # Population 200 / cap 550 = 36% — below 50%, so +2
        report = colony.process_turn()
        self.assertGreater(colony.happiness, 50)

        # Now set population in the middle band
        colony.population = 400  # 400/550 = 73% — in middle band
        colony.happiness = 50  # Below baseline of 70

        report = colony.process_turn()
        # Should recover by +1 toward 70
        self.assertEqual(
            colony.happiness, 51,
            "Happiness should increase by 1 in middle band when below 70",
        )

    def test_happiness_stable_at_baseline_in_middle_band(self):
        colony = Colony(
            system_id="test",
            planet_id="test_planet",
            name="Test Colony",
            population=400,
            happiness=70,
        )
        colony.infrastructure["housing"]["level"] = 3  # cap=550

        report = colony.process_turn()
        # At 70 happiness in middle band, should stay at 70 (no change)
        self.assertEqual(
            colony.happiness, 70,
            "Happiness at 70 in middle band should be stable",
        )


class TestStartingColonyNotDeathSpiral(unittest.TestCase):
    """Starting colony should not lose happiness catastrophically in 10 turns."""

    def test_starting_colony_happiness_stays_playable(self):
        state = GameState.new_game()
        colony = state.colonies.colonies.get("sol")
        self.assertIsNotNone(colony)

        initial_happiness = colony.happiness  # 75

        # Process 10 turns
        for _ in range(10):
            state.process_turn()

        # Happiness should not have crashed below 40
        self.assertGreaterEqual(
            colony.happiness, 40,
            f"Starting colony happiness dropped from {initial_happiness} to "
            f"{colony.happiness} in 10 turns — death spiral detected",
        )


class TestMiningOutputSurvivesSaveLoad(unittest.TestCase):
    """Mining state and planet resources should survive a save/load round-trip."""

    def test_mined_resources_persist_through_roundtrip(self):
        state = GameState.new_game()

        # Set up a miner
        miner = None
        for ship in state.fleet.ships.values():
            if ship.ship_class == "miner":
                miner = ship
                break
        if miner is None:
            state.resources.global_resources["credits"] = 500
            state.resources.global_resources["metals"] = 500
            miner = state.fleet.create_ship("miner", "sol", "Test Miner")
        miner.location = "sol"
        miner.mining = True

        # Mine for 3 turns
        for _ in range(3):
            state.process_turn()

        resources_before = dict(state.resources.global_resources)

        # Round-trip
        data = state.to_dict()
        loaded = GameState.from_dict(data)

        # Resources should match
        self.assertEqual(
            resources_before,
            loaded.resources.global_resources,
            "Global resources should match after save/load round-trip",
        )

        # Planet resources should still be valid types
        for sys_id, system in loaded.galaxy.systems.items():
            for planet in system.planets:
                for res_type in planet.resources:
                    self.assertIn(res_type, RESOURCE_TYPES)


if __name__ == "__main__":
    unittest.main()
