import random
import unittest

from gate_horizons.game.tactical import HexGrid, TacticalCombat, TacticalUnit, TERRAIN_TYPES


class TestTacticalCombat(unittest.TestCase):
    def test_grid_movement_constraints(self):
        grid = HexGrid.generate(width=5, height=5, seed=1)
        grid.cells[(2, 3)].terrain = TERRAIN_TYPES["asteroid"]
        unit = TacticalUnit(
            unit_id="u1",
            name="Scout",
            faction="player",
            hp=10,
            max_hp=10,
            move_points=1,
            weapon_range=1,
            weapon_damage=2,
            accuracy=0.7,
            position=(2, 2),
        )
        combat = TacticalCombat(grid=grid, units=[unit], rng=random.Random(0))
        self.assertFalse(combat.can_move(unit, (2, 3)))
        self.assertTrue(combat.can_move(unit, (3, 2)))

    def test_attack_resolution_deterministic(self):
        grid = HexGrid.generate(width=3, height=3, seed=2)
        attacker = TacticalUnit(
            unit_id="a1",
            name="Attacker",
            faction="player",
            hp=10,
            max_hp=10,
            move_points=1,
            weapon_range=2,
            weapon_damage=3,
            accuracy=0.5,
            position=(0, 0),
        )
        target = TacticalUnit(
            unit_id="t1",
            name="Target",
            faction="enemy",
            hp=6,
            max_hp=6,
            move_points=1,
            weapon_range=1,
            weapon_damage=2,
            accuracy=0.4,
            position=(1, 0),
        )
        combat = TacticalCombat(grid=grid, units=[attacker, target], rng=random.Random(1))
        hit, damage = combat.attack(attacker.unit_id, target.unit_id)
        self.assertTrue(hit)
        self.assertEqual(damage, attacker.weapon_damage)
        self.assertEqual(target.hp, 3)

    def test_outcome_payload(self):
        grid = HexGrid.generate(width=3, height=3, seed=3)
        attacker = TacticalUnit(
            unit_id="p1",
            name="Player",
            faction="player",
            hp=10,
            max_hp=10,
            move_points=1,
            weapon_range=1,
            weapon_damage=10,
            accuracy=1.0,
            position=(0, 0),
        )
        target = TacticalUnit(
            unit_id="e1",
            name="Enemy",
            faction="enemy",
            hp=5,
            max_hp=5,
            move_points=1,
            weapon_range=1,
            weapon_damage=2,
            accuracy=0.4,
            position=(1, 0),
        )
        combat = TacticalCombat(
            grid=grid,
            units=[attacker, target],
            rng=random.Random(0),
            defender_loot={"metals": [1, 2]},
        )
        combat.attack(attacker.unit_id, target.unit_id)
        outcome = combat.build_outcome()
        result_spec = combat.outcome_to_result_spec(outcome, "enc-test", [attacker])
        self.assertIn("outcome", result_spec)
        self.assertIn("loot", result_spec)
        self.assertIn("tacticalReport", result_spec)
        self.assertEqual(result_spec["encounterId"], "enc-test")


if __name__ == "__main__":
    unittest.main()
