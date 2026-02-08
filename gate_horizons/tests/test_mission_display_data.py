import unittest

from gate_horizons.game.missions import Mission, mission_display_data


class TestMissionDisplayData(unittest.TestCase):
    def test_display_data_includes_progress_summary(self):
        mission = Mission(
            id="m1",
            category="exploration",
            title="Chart the Frontier",
            description="Discover 1 new star system.",
            requirement={"metric": "discoveries", "target": 3},
            reward={"credits": 25},
            progress=1,
            status="active",
            created_turn=1,
        )

        data = mission_display_data(mission)

        self.assertEqual(data["progress_summary"], "1/3")
        self.assertEqual(data["title"], "Chart the Frontier")
        self.assertEqual(data["reward"]["credits"], 25)
