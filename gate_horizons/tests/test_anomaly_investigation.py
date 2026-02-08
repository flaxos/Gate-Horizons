import unittest

from gate_horizons.game.state import GameState


class TestAnomalyInvestigation(unittest.TestCase):
    def setUp(self):
        self.state = GameState.new_game()

    def _move_scout(self, system_id: str):
        scout = next(
            ship for ship in self.state.fleet.ships.values()
            if ship.ship_class == "scout"
        )
        scout.location = system_id
        scout.path = []
        return scout

    def test_investigate_anomaly_queues_event_and_marks_investigated(self):
        system_id = "alpha_centauri"
        self._move_scout(system_id)
        system = self.state.galaxy.systems[system_id]

        for anomaly in system.anomalies:
            if isinstance(anomaly, dict):
                anomaly["investigated"] = False

        event = self.state.investigate_anomaly(system_id)

        self.assertIsNotNone(event)
        self.assertTrue(self.state.events.event_queue)
        self.assertTrue(
            any(
                isinstance(anomaly, dict) and anomaly.get("investigated")
                for anomaly in system.anomalies
            )
        )

    def test_investigate_anomaly_applies_bonus_resources(self):
        system_id = "barnards_star"
        self._move_scout(system_id)
        system = self.state.galaxy.systems[system_id]

        target = next(
            (
                anomaly for anomaly in system.anomalies
                if isinstance(anomaly, dict) and anomaly.get("bonus_resources")
            ),
            None,
        )
        self.assertIsNotNone(target)
        target["investigated"] = False
        before = dict(self.state.resources.global_resources)

        self.state.investigate_anomaly(system_id)

        for resource, amount in target.get("bonus_resources", {}).items():
            self.assertEqual(
                self.state.resources.global_resources.get(resource, 0),
                before.get(resource, 0) + amount,
            )
