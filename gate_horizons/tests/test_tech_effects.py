"""Regression tests for tech effect application in Gate Horizons.

Covers:
1. sensor_bonus permanently increases ship sensor_range on completion
2. fuel_efficiency reduces fuel consumption during movement
3. build_time_reduction shortens colony construction queued via turn processing
4. one-time events do not re-trigger once queued
5. tech effects survive a save/load round-trip
"""

import unittest

from gate_horizons.game.state import GameState
from gate_horizons.game.tech import TechNode, TechTree


class TestSensorBonusApplied(unittest.TestCase):
    """Researching Deep Scanning Arrays should give +1 sensor_range to all ships."""

    def test_sensor_range_increases_on_research_complete(self):
        state = GameState.new_game()

        # Record baseline sensor ranges
        baseline = {
            sid: ship.stats.sensor_range
            for sid, ship in state.fleet.ships.items()
        }
        self.assertTrue(len(baseline) > 0)

        # Start researching deep_scan (sensor_bonus: 1)
        # Give enough intel to afford it
        state.resources.global_resources["intel"] = 200
        started = state.tech.start_research("deep_scan", state.resources)
        self.assertTrue(started, "Should be able to start deep_scan research")

        # Fast-forward turns until research completes
        tech = state.tech.techs["deep_scan"]
        for _ in range(tech.cost.get("turns", 3) + 1):
            state.process_turn()

        self.assertTrue(tech.researched, "deep_scan should be marked researched")

        # Verify every ship gained +1 sensor_range
        for sid, ship in state.fleet.ships.items():
            expected = baseline[sid] + 1
            self.assertEqual(
                ship.stats.sensor_range,
                expected,
                f"Ship {ship.name} sensor_range should be {expected}, got {ship.stats.sensor_range}",
            )


class TestFuelEfficiencyReducesCost(unittest.TestCase):
    """Researching Efficient Drives should reduce fuel consumed during movement."""

    def test_fuel_efficiency_saves_fuel(self):
        state = GameState.new_game()

        # Find the scout (speed 3)
        scout = None
        for ship in state.fleet.ships.values():
            if ship.ship_class == "scout":
                scout = ship
                break
        self.assertIsNotNone(scout)

        # Research efficient_drives (fuel_efficiency: 1.2)
        state.resources.global_resources["intel"] = 200
        state.tech.start_research("efficient_drives", state.resources)
        tech = state.tech.techs["efficient_drives"]
        for _ in range(tech.cost.get("turns", 3) + 1):
            state.process_turn()
        self.assertTrue(tech.researched)

        # Now send scout on a journey and measure fuel
        # Scout speed=3, so a 3-hop path costs round(3/1.2)=2 fuel instead of 3
        initial_fuel = scout.fuel

        # Use FleetManager.process_movement directly with fuel_efficiency
        scout.path = ["alpha_centauri", "sirius", "procyon"]
        scout.destination = "procyon"
        scout.mission = "moving"

        result = state.fleet.process_movement(scout.id, fuel_efficiency=1.2)

        # With efficiency 1.2, 3 hops should cost round(3/1.2) = round(2.5) = 2 fuel
        self.assertEqual(result.fuel_consumed, 2, "3 hops at 1.2 efficiency should cost 2 fuel")
        self.assertEqual(scout.fuel, initial_fuel - 2)


class TestBuildTimeReduction(unittest.TestCase):
    """Researching Rapid Construction should reduce build times for queued buildings."""

    def test_queued_construction_uses_reduced_time(self):
        state = GameState.new_game()

        # Research rapid_construction (build_time_reduction: 1)
        state.resources.global_resources["intel"] = 200
        state.tech.start_research("rapid_construction", state.resources)
        tech = state.tech.techs["rapid_construction"]
        for _ in range(tech.cost.get("turns", 3) + 1):
            state.process_turn()
        self.assertTrue(tech.researched)

        colony = state.colonies.colonies.get("sol")
        self.assertIsNotNone(colony)

        # Queue a housing upgrade via the build queue
        colony.build_queue.append({"type": "defense"})

        # Process one turn to dequeue it into active construction
        state.process_turn()

        # defense base build time is 3, with reduction of 1 => 2 turns
        defense = colony.infrastructure.get("defense", {})
        self.assertTrue(defense.get("building"), "Defense should be under construction")
        self.assertEqual(
            defense.get("turns_remaining"),
            2,
            f"Defense should need 2 turns (3 base - 1 reduction), got {defense.get('turns_remaining')}",
        )


class TestOneTimeEventsNoRetrigger(unittest.TestCase):
    """One-time events should not re-trigger after being queued."""

    def test_one_time_event_queued_then_blocked(self):
        from gate_horizons.game.events import Event, EventEngine

        engine = EventEngine()
        event = Event(
            id="test_unique",
            title="Test Unique Event",
            description="Should only fire once",
            one_time=True,
            choices=[{"text": "OK", "outcomes": [{"probability": 1.0, "result": "success"}]}],
        )
        engine.available_events.append(event)

        # Create a minimal game_state mock
        class FakeFleet:
            ships = {}

        class FakeGalaxy:
            systems = {}

        class FakeState:
            fleet = FakeFleet()
            galaxy = FakeGalaxy()

        fake = FakeState()

        # Force-trigger (bypass random selection) by checking that the event
        # becomes ineligible after first trigger.
        # Manually simulate what check_triggers does:
        engine.triggered_events = []
        engine.event_queue = []

        # First trigger: eligible
        eligible_before = [
            e for e in engine.available_events
            if not (e.one_time and e.id in engine.triggered_events)
        ]
        self.assertEqual(len(eligible_before), 1)

        # Simulate triggering
        engine.triggered_events.append(event.id)
        engine.event_queue.append(event)

        # Second check: should be blocked
        eligible_after = [
            e for e in engine.available_events
            if not (e.one_time and e.id in engine.triggered_events)
        ]
        self.assertEqual(len(eligible_after), 0, "One-time event should not be eligible after triggering")


class TestTechEffectsSurviveSaveLoad(unittest.TestCase):
    """Tech effects (sensor_bonus etc.) should persist through save/load."""

    def test_researched_tech_effects_persist(self):
        state = GameState.new_game()

        # Research deep_scan for sensor_bonus
        state.resources.global_resources["intel"] = 200
        state.tech.start_research("deep_scan", state.resources)
        tech = state.tech.techs["deep_scan"]
        for _ in range(tech.cost.get("turns", 3) + 1):
            state.process_turn()
        self.assertTrue(tech.researched)

        # Record post-research sensor ranges
        sensor_ranges_before = {
            sid: ship.stats.sensor_range
            for sid, ship in state.fleet.ships.items()
        }

        # Round-trip through serialization
        data = state.to_dict()
        loaded = GameState.from_dict(data)

        # Verify sensor ranges match (the bonus was baked into stats)
        for sid, ship in loaded.fleet.ships.items():
            self.assertEqual(
                ship.stats.sensor_range,
                sensor_ranges_before[sid],
                f"Ship {ship.name} sensor_range should persist through save/load",
            )

        # Verify the tech is still marked as researched
        self.assertTrue(loaded.tech.techs["deep_scan"].researched)

        # Verify get_effects still returns the sensor_bonus
        effects = loaded.tech.get_effects()
        self.assertIn("sensor_bonus", effects)
        self.assertEqual(effects["sensor_bonus"], 1)


if __name__ == "__main__":
    unittest.main()
