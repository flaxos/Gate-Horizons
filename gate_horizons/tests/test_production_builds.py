import unittest

from gate_horizons.game.state import GameState
from gate_horizons.game.production import ExtractionSite


class TestProductionBuilds(unittest.TestCase):
    def setUp(self):
        self.state = GameState.new_game()

    def test_build_factory_spends_resources(self):
        colony = self.state.colonies.colonies["sol"]
        cost = self.state.production.config.factory_balance.get("factory_build_cost", {})
        alloy_cost = cost.get("metal_alloys", 0)
        credit_cost = cost.get("credits", 0)
        colony.production_inventory["metal_alloys"] = alloy_cost + 10
        starting_credits = self.state.resources.global_resources["credits"]

        success, message = self.state.build_factory("sol")

        self.assertTrue(success, message)
        self.assertEqual(1, len(colony.factories))
        factory = colony.factories[0]
        self.assertTrue(factory.building)
        self.assertGreater(factory.build_turns_remaining, 0)
        self.assertEqual(
            starting_credits - credit_cost,
            self.state.resources.global_resources["credits"],
        )
        self.assertEqual(10, colony.production_inventory["metal_alloys"])

    def test_build_extraction_site_respects_limits(self):
        colony = self.state.colonies.colonies["sol"]
        cost = self.state.production.config.extraction_balance.get(
            "extraction_site_build_cost", {}
        )
        alloy_cost = cost.get("metal_alloys", 0)
        credit_cost = cost.get("credits", 0)
        colony.production_inventory["metal_alloys"] = alloy_cost + 40
        starting_credits = self.state.resources.global_resources["credits"]

        success, message = self.state.build_extraction_site("sol", "ore_iron")

        self.assertTrue(success, message)
        self.assertGreater(len(colony.extraction_sites), 0)
        new_site = colony.extraction_sites[-1]
        self.assertTrue(new_site.building)
        self.assertEqual("ore_iron", new_site.resource_id)
        self.assertEqual(
            starting_credits - credit_cost,
            self.state.resources.global_resources["credits"],
        )
        self.assertEqual(40, colony.production_inventory["metal_alloys"])

        max_sites = self.state.production.config.extraction_balance.get(
            "max_extraction_sites_per_colony", 0
        )
        while max_sites and len(colony.extraction_sites) < max_sites:
            colony.extraction_sites.append(
                ExtractionSite(resource_id="ore_iron", base_yield=1)
            )

        success, _ = self.state.build_extraction_site("sol", "ore_iron")
        if max_sites:
            self.assertFalse(success)
