"""Regression tests for ship construction and colony housing balance."""

import json
import unittest

from gate_horizons.game.state import GameState
from gate_horizons.game.colonies import (
    Colony,
    HOUSING_BASE_CAP,
    HOUSING_PER_LEVEL,
)


class TestShipConstructionCompletesAndAddsToFleet(unittest.TestCase):
    """A ship queued at a colony spaceport should be created in the fleet
    after the required number of turns."""

    def test_ship_built_after_build_turns(self):
        gs = GameState.new_game()
        initial_count = len(gs.fleet.ships)

        # Scout: build_cost = {credits: 50, metals: 20}, build_turns = 2
        ok = gs.build_ship("sol", "scout", "ISS Explorer")
        self.assertTrue(ok, "build_ship should succeed with sufficient resources")

        colony = gs.colonies.colonies["sol"]
        self.assertEqual(len(colony.shipyard_queue), 1)

        # Process 1 turn — ship still building
        gs.process_turn()
        self.assertEqual(len(gs.fleet.ships), initial_count)

        # Process 2nd turn — ship should complete
        report = gs.process_turn()
        self.assertEqual(len(gs.fleet.ships), initial_count + 1)
        self.assertEqual(len(colony.shipyard_queue), 0)

        # The new ship should be at Sol
        new_ships = [
            s for s in gs.fleet.ships.values() if s.name == "ISS Explorer"
        ]
        self.assertEqual(len(new_ships), 1)
        self.assertEqual(new_ships[0].location, "sol")
        self.assertEqual(new_ships[0].ship_class, "scout")

        # Construction report should mention the launch
        launched = [c for c in report.construction_completed if "launched" in c]
        self.assertTrue(len(launched) > 0, "Turn report should mention ship launch")


class TestShipBuildRejectsInsufficientResources(unittest.TestCase):
    """build_ship should return False if resources can't cover the cost,
    and should not deduct anything or queue a build."""

    def test_no_build_without_resources(self):
        gs = GameState.new_game()
        # Zero out resources
        gs.resources.global_resources = {r: 0 for r in gs.resources.global_resources}
        colony = gs.colonies.colonies["sol"]

        ok = gs.build_ship("sol", "corvette", "ISS Costly")
        self.assertFalse(ok, "build_ship should fail with no resources")
        self.assertEqual(len(colony.shipyard_queue), 0)


class TestShipBuildRespectsSpaceportSlotLimit(unittest.TestCase):
    """Spaceport level determines concurrent build slots.
    Level 1 = 1 slot, so a second build should be rejected."""

    def test_slot_limit(self):
        gs = GameState.new_game()
        # Give enough resources for two scouts
        gs.resources.global_resources["credits"] = 500
        gs.resources.global_resources["metals"] = 500
        colony = gs.colonies.colonies["sol"]
        spaceport_level = colony.infrastructure["spaceport"]["level"]
        self.assertEqual(spaceport_level, 1)

        ok1 = gs.build_ship("sol", "scout", "ISS First")
        self.assertTrue(ok1)
        self.assertEqual(len(colony.shipyard_queue), 1)

        # Second build should fail (only 1 slot at spaceport level 1)
        ok2 = gs.build_ship("sol", "scout", "ISS Second")
        self.assertFalse(ok2, "second concurrent build should be rejected at spaceport level 1")
        self.assertEqual(len(colony.shipyard_queue), 1)


class TestShipyardQueuePersistsSaveLoad(unittest.TestCase):
    """Shipyard queue must survive a save/load round-trip and still
    produce the ship on the correct turn."""

    def test_shipyard_roundtrip(self):
        gs = GameState.new_game()
        gs.build_ship("sol", "scout", "ISS Roundtrip")

        # Serialize and deserialize
        data = gs.to_dict()
        gs2 = GameState.from_dict(data)

        colony2 = gs2.colonies.colonies["sol"]
        self.assertEqual(len(colony2.shipyard_queue), 1)
        self.assertEqual(colony2.shipyard_queue[0]["ship_class"], "scout")
        self.assertEqual(colony2.shipyard_queue[0]["name"], "ISS Roundtrip")
        self.assertEqual(colony2.shipyard_queue[0]["turns_remaining"], 2)

        initial_count = len(gs2.fleet.ships)
        # Complete the build
        gs2.process_turn()
        gs2.process_turn()
        self.assertEqual(len(gs2.fleet.ships), initial_count + 1)
        built = [s for s in gs2.fleet.ships.values() if s.name == "ISS Roundtrip"]
        self.assertEqual(len(built), 1)


class TestHousingCapDoesNotCauseImmediateHappinessDrop(unittest.TestCase):
    """Starting colony should NOT lose happiness on turn 1.

    Previously, housing cap was 550 with starting pop 500 (90.9% > 90%
    threshold), causing an immediate death spiral.  With the fix the cap
    is 700, so pop 500 = 71.4% — well below the 90% overcrowding line.
    """

    def test_no_happiness_drop_on_first_turn(self):
        gs = GameState.new_game()
        colony = gs.colonies.colonies["sol"]
        initial_happiness = colony.happiness  # 75

        housing_level = colony.infrastructure["housing"]["level"]
        housing_cap = HOUSING_BASE_CAP + housing_level * HOUSING_PER_LEVEL
        self.assertGreater(
            housing_cap * 0.9,
            colony.population,
            "Housing 90% threshold should exceed starting population",
        )

        report = gs.process_turn()
        colony_report = [
            cr for cr in report.colony_reports if cr["system_id"] == "sol"
        ][0]

        self.assertGreaterEqual(
            colony.happiness,
            initial_happiness,
            "Happiness should not drop on turn 1",
        )
        self.assertGreaterEqual(
            colony_report["happiness_change"],
            0,
            "Happiness change should be non-negative on turn 1",
        )


class TestBuildTimeReductionAppliesToShipyard(unittest.TestCase):
    """Rapid Construction tech effect should reduce shipyard build turns."""

    def test_reduced_build_time(self):
        gs = GameState.new_game()

        # Manually mark rapid_construction as researched
        tech = gs.tech.techs["rapid_construction"]
        tech.researched = True
        tech.researching = False
        tech.turns_remaining = 0

        # Scout normally takes 2 turns, with -1 reduction = 1 turn
        ok = gs.build_ship("sol", "scout", "ISS Fast Build")
        self.assertTrue(ok)

        colony = gs.colonies.colonies["sol"]
        self.assertEqual(colony.shipyard_queue[0]["turns_remaining"], 1)

        # Should complete after 1 turn
        initial_count = len(gs.fleet.ships)
        gs.process_turn()
        self.assertEqual(len(gs.fleet.ships), initial_count + 1)


if __name__ == "__main__":
    unittest.main()
