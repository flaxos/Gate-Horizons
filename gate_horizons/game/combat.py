"""Combat auto-resolve system for Gate Horizons."""

import random
from dataclasses import dataclass, field
from typing import Optional


@dataclass
class EncounterData:
    type: str = "pirates"  # pirates, alien_patrol, hazard, derelict_defense, rogue_ai
    strength: int = 10
    description: str = ""
    loot_table: dict = field(default_factory=dict)
    flee_difficulty: float = 0.3  # chance to fail to escape

    def to_dict(self) -> dict:
        return {
            "type": self.type,
            "strength": self.strength,
            "description": self.description,
            "loot_table": dict(self.loot_table),
            "flee_difficulty": self.flee_difficulty,
        }

    @classmethod
    def from_dict(cls, data: dict) -> "EncounterData":
        return cls(**{k: v for k, v in data.items() if k in cls.__dataclass_fields__})


@dataclass
class CombatResult:
    victory: bool = False
    attacker_damage: dict = field(default_factory=dict)  # ship_id -> damage
    ships_destroyed: list = field(default_factory=list)
    loot: dict = field(default_factory=dict)
    intel_gained: int = 0
    narrative: str = ""
    xp_gained: int = 0
    fled: bool = False

    def to_dict(self) -> dict:
        return {
            "victory": self.victory,
            "attacker_damage": dict(self.attacker_damage),
            "ships_destroyed": list(self.ships_destroyed),
            "loot": dict(self.loot),
            "intel_gained": self.intel_gained,
            "narrative": self.narrative,
            "xp_gained": self.xp_gained,
            "fled": self.fled,
        }


class CombatResolver:
    def __init__(self):
        self.combat_accuracy_bonus: float = 0.0

    def calculate_odds(
        self, attacker_ships: list, defender: EncounterData, tech_bonuses: dict = None
    ) -> float:
        """Calculate win probability for attackers. Returns 0.0 to 1.0."""
        if not attacker_ships:
            return 0.0

        total_power = sum(s.stats.combat_power for s in attacker_ships)

        # Apply tech bonuses
        if tech_bonuses:
            power_mult = tech_bonuses.get("combat_power_bonus", 1.0)
            total_power = int(total_power * power_mult)

        if defender.strength == 0:
            return 1.0

        # Base odds from power ratio
        ratio = total_power / defender.strength
        base_odds = min(0.95, max(0.05, ratio / (ratio + 1)))

        # Apply accuracy bonus from tech
        base_odds = min(0.95, base_odds + self.combat_accuracy_bonus)

        return round(base_odds, 3)

    def auto_resolve(
        self, attacker_ships: list, defender: EncounterData, odds: float = None
    ) -> CombatResult:
        """Auto-resolve combat with variance."""
        if odds is None:
            odds = self.calculate_odds(attacker_ships, defender)

        result = CombatResult()

        # Roll with ±15% variance
        roll = random.random()
        adjusted_odds = odds + random.uniform(-0.15, 0.15)
        adjusted_odds = max(0.0, min(1.0, adjusted_odds))

        result.victory = roll < adjusted_odds

        if result.victory:
            # Victory: lighter damage, gain loot
            result.narrative = self._victory_narrative(attacker_ships, defender)
            result.xp_gained = max(1, defender.strength // 5)
            result.intel_gained = random.randint(1, 3)

            # Calculate loot
            for resource, amount_range in defender.loot_table.items():
                if isinstance(amount_range, list) and len(amount_range) == 2:
                    result.loot[resource] = random.randint(amount_range[0], amount_range[1])
                elif isinstance(amount_range, (int, float)):
                    result.loot[resource] = int(amount_range)

            # Light damage to attackers
            for ship in attacker_ships:
                damage = random.randint(0, max(1, defender.strength // len(attacker_ships)))
                if damage > 0:
                    result.attacker_damage[ship.id] = damage
                    ship.hull -= damage
                    if ship.hull <= 0:
                        ship.hull = 0
                        result.ships_destroyed.append(ship.id)
        else:
            # Defeat: heavier damage
            result.narrative = self._defeat_narrative(attacker_ships, defender)
            result.xp_gained = max(1, defender.strength // 10)

            for ship in attacker_ships:
                damage = random.randint(
                    max(1, defender.strength // (len(attacker_ships) * 2)),
                    max(2, defender.strength // len(attacker_ships)),
                )
                result.attacker_damage[ship.id] = damage
                ship.hull -= damage
                if ship.hull <= 0:
                    ship.hull = 0
                    result.ships_destroyed.append(ship.id)

        return result

    def attempt_flee(self, ships: list, defender: EncounterData) -> CombatResult:
        """Attempt to flee from an encounter."""
        result = CombatResult()
        result.fled = True

        flee_roll = random.random()
        # Faster ships flee more easily
        avg_speed = sum(s.stats.speed for s in ships) / max(1, len(ships))
        flee_bonus = avg_speed * 0.1

        if flee_roll > defender.flee_difficulty - flee_bonus:
            # Successful escape
            result.victory = False
            result.narrative = "Your ships engage emergency thrusters and escape the engagement zone."
        else:
            # Failed escape, take some damage
            result.narrative = "Escape attempt failed! Your ships take damage while disengaging."
            for ship in ships:
                damage = random.randint(1, max(2, defender.strength // (len(ships) * 3)))
                result.attacker_damage[ship.id] = damage
                ship.hull -= damage
                if ship.hull <= 0:
                    ship.hull = 0
                    result.ships_destroyed.append(ship.id)

        return result

    def _victory_narrative(self, ships: list, defender: EncounterData) -> str:
        narratives = {
            "pirates": "Your fleet engages the pirate raiders. Coordinated fire makes quick work of their outdated vessels. Salvage teams recover useful materials from the wreckage.",
            "alien_patrol": "The alien patrol vessels move to intercept, but your tactical positioning gives you the advantage. After a brief exchange of fire, they withdraw.",
            "hazard": "Your ships navigate through the hazardous zone, shields absorbing the worst of the impacts. Sensor data reveals valuable readings.",
            "derelict_defense": "The automated defense systems put up resistance, but your crews systematically disable each turret. The derelict is now safe to explore.",
            "rogue_ai": "The rogue AI's combat algorithms prove predictable. Your crews adapt and overwhelm its defenses.",
        }
        return narratives.get(
            defender.type,
            "Your forces prevail in the engagement. The sector is secured."
        )

    def _defeat_narrative(self, ships: list, defender: EncounterData) -> str:
        narratives = {
            "pirates": "The pirate fleet proves more formidable than expected. Your ships take heavy damage and are forced to withdraw.",
            "alien_patrol": "The alien vessels demonstrate superior technology. Your fleet is outmatched and sustains significant damage.",
            "hazard": "The hazardous conditions prove overwhelming. Your ships sustain serious damage before clearing the area.",
            "derelict_defense": "The derelict's defense systems are far more advanced than anticipated. Your boarding teams are repelled with casualties.",
            "rogue_ai": "The rogue AI adapts to your tactics with alarming speed. Your fleet takes heavy losses.",
        }
        return narratives.get(
            defender.type,
            "The engagement does not go in your favor. Your ships sustain heavy damage."
        )

    def generate_random_encounter(self, system_tier: int) -> Optional[EncounterData]:
        """Generate a random encounter based on system tier."""
        # Higher tier (frontier) = more encounters
        encounter_chance = {1: 0.02, 2: 0.05, 3: 0.1}.get(system_tier, 0.05)

        if random.random() > encounter_chance:
            return None

        encounters = [
            EncounterData(
                type="pirates",
                strength=random.randint(5, 15) * system_tier,
                description="A band of pirate raiders emerges from behind an asteroid field.",
                loot_table={"credits": [5, 20], "metals": [2, 10]},
                flee_difficulty=0.3,
            ),
            EncounterData(
                type="alien_patrol",
                strength=random.randint(10, 25) * system_tier,
                description="Unknown alien vessels move to intercept your ships.",
                loot_table={"exotics": [1, 5], "intel": [3, 8]},
                flee_difficulty=0.4,
            ),
            EncounterData(
                type="rogue_ai",
                strength=random.randint(8, 20) * system_tier,
                description="Automated combat drones activate and target your fleet.",
                loot_table={"metals": [5, 15], "intel": [2, 6]},
                flee_difficulty=0.2,
            ),
        ]

        return random.choice(encounters)

    def to_dict(self) -> dict:
        return {"combat_accuracy_bonus": self.combat_accuracy_bonus}

    @classmethod
    def from_dict(cls, data: dict) -> "CombatResolver":
        cr = cls()
        cr.combat_accuracy_bonus = data.get("combat_accuracy_bonus", 0.0)
        return cr
