"""Colony management system for Gate Horizons."""

from typing import Optional

INFRASTRUCTURE_TYPES = ["housing", "industry", "defense", "research", "spaceport"]

DEFAULT_INFRASTRUCTURE = {
    infra: {"level": 0, "building": False, "turns_remaining": 0}
    for infra in INFRASTRUCTURE_TYPES
}

# Build costs per infrastructure level
BUILD_COSTS = {
    "housing": {"credits": 30, "metals": 15},
    "industry": {"credits": 40, "metals": 25},
    "defense": {"credits": 50, "metals": 30},
    "research": {"credits": 45, "metals": 20},
    "spaceport": {"credits": 60, "metals": 40},
}

BUILD_TURNS = {
    "housing": 2,
    "industry": 3,
    "defense": 3,
    "research": 3,
    "spaceport": 4,
}


class Colony:
    def __init__(
        self,
        system_id: str,
        planet_id: str,
        name: str = "New Colony",
        population: int = 100,
        happiness: int = 70,
        infrastructure: dict = None,
        build_queue: list = None,
    ):
        self.system_id = system_id
        self.planet_id = planet_id
        self.name = name
        self.population = population
        self.happiness = happiness
        self.infrastructure = infrastructure or {
            k: dict(v) for k, v in DEFAULT_INFRASTRUCTURE.items()
        }
        self.build_queue = build_queue or []

    def get_tier(self) -> int:
        levels = [
            self.infrastructure.get(k, {}).get("level", 0)
            for k in INFRASTRUCTURE_TYPES
        ]
        if all(l >= 3 for l in levels):
            return 1  # Core world
        if any(l >= 1 for l in levels) and self.population >= 200:
            return 2  # Developing
        return 3  # Frontier outpost

    def calculate_production(self) -> dict:
        production = {}
        industry_level = self.infrastructure.get("industry", {}).get("level", 0)
        research_level = self.infrastructure.get("research", {}).get("level", 0)
        spaceport_level = self.infrastructure.get("spaceport", {}).get("level", 0)

        # Base production scales with population and infrastructure
        pop_factor = self.population / 100.0
        happiness_factor = self.happiness / 100.0

        # Industry produces metals and energy
        production["metals"] = int(industry_level * 3 * pop_factor * happiness_factor)
        production["energy"] = int((industry_level + 1) * 2 * pop_factor)

        # Research produces intel
        production["intel"] = int(research_level * 2 * pop_factor * happiness_factor)

        # Spaceport generates credits through trade
        production["credits"] = int((spaceport_level + 1) * 3 * pop_factor)

        return production

    def calculate_consumption(self) -> dict:
        consumption = {}
        pop_factor = self.population / 100.0

        # Population consumes energy and credits
        consumption["energy"] = int(2 * pop_factor)
        consumption["credits"] = int(1 * pop_factor)

        # Infrastructure maintenance
        for infra_type in INFRASTRUCTURE_TYPES:
            level = self.infrastructure.get(infra_type, {}).get("level", 0)
            consumption["credits"] = consumption.get("credits", 0) + level

        return consumption

    def start_construction(self, infra_type: str, build_time_reduction: int = 0) -> bool:
        """Start building/upgrading an infrastructure type."""
        if infra_type not in INFRASTRUCTURE_TYPES:
            return False

        infra = self.infrastructure.get(infra_type, {})
        if infra.get("building", False):
            return False  # Already building

        turns = max(1, BUILD_TURNS.get(infra_type, 3) - build_time_reduction)
        self.infrastructure[infra_type] = {
            "level": infra.get("level", 0),
            "building": True,
            "turns_remaining": turns,
        }
        return True

    def get_build_cost(self, infra_type: str) -> dict:
        """Get cost to build next level of infrastructure."""
        base_cost = BUILD_COSTS.get(infra_type, {})
        level = self.infrastructure.get(infra_type, {}).get("level", 0)
        # Cost scales with level
        return {r: int(amount * (1 + level * 0.5)) for r, amount in base_cost.items()}

    def queue_construction(self, infra_type: str) -> None:
        self.build_queue.append({"type": infra_type})

    def process_turn(self, build_time_reduction: int = 0) -> dict:
        """Process one turn for this colony. Returns summary of changes.

        Args:
            build_time_reduction: Turns to subtract from new construction
                (from tech effects like Rapid Construction).
        """
        report = {
            "construction_completed": [],
            "population_growth": 0,
            "happiness_change": 0,
            "tier_change": None,
        }

        old_tier = self.get_tier()

        # Advance construction
        for infra_type in INFRASTRUCTURE_TYPES:
            infra = self.infrastructure.get(infra_type, {})
            if infra.get("building", False):
                infra["turns_remaining"] = infra.get("turns_remaining", 0) - 1
                if infra["turns_remaining"] <= 0:
                    infra["level"] = infra.get("level", 0) + 1
                    infra["building"] = False
                    infra["turns_remaining"] = 0
                    report["construction_completed"].append(infra_type)

        # Process build queue
        if self.build_queue:
            for infra_type in INFRASTRUCTURE_TYPES:
                if not self.infrastructure.get(infra_type, {}).get("building", False):
                    # Find queued item for this type
                    for i, item in enumerate(self.build_queue):
                        if item["type"] == infra_type:
                            self.start_construction(infra_type, build_time_reduction)
                            self.build_queue.pop(i)
                            break

        # Population growth
        housing_level = self.infrastructure.get("housing", {}).get("level", 0)
        housing_cap = 100 + housing_level * 150
        if self.population < housing_cap:
            growth_rate = 0.05  # Base 5%
            if self.happiness >= 80:
                growth_rate += 0.02
            elif self.happiness < 40:
                growth_rate -= 0.03
            growth = max(1, int(self.population * growth_rate))
            growth = min(growth, housing_cap - self.population)
            self.population += growth
            report["population_growth"] = growth

        # Happiness adjustments
        if self.population > housing_cap * 0.9:
            self.happiness = max(0, self.happiness - 3)
            report["happiness_change"] -= 3
        elif self.population < housing_cap * 0.5:
            self.happiness = min(100, self.happiness + 2)
            report["happiness_change"] += 2
        elif self.happiness < 70:
            # Middle band (50-90% capacity): slowly recover toward baseline
            self.happiness = min(70, self.happiness + 1)
            report["happiness_change"] += 1

        # Tier check
        new_tier = self.get_tier()
        if new_tier != old_tier:
            report["tier_change"] = (old_tier, new_tier)

        return report

    def to_dict(self) -> dict:
        return {
            "system_id": self.system_id,
            "planet_id": self.planet_id,
            "name": self.name,
            "population": self.population,
            "happiness": self.happiness,
            "infrastructure": {
                k: dict(v) for k, v in self.infrastructure.items()
            },
            "build_queue": list(self.build_queue),
        }

    @classmethod
    def from_dict(cls, data: dict) -> "Colony":
        infrastructure = {
            k: dict(v) for k, v in DEFAULT_INFRASTRUCTURE.items()
        }
        incoming_infra = data.get("infrastructure") or {}
        for infra_type, infra_data in incoming_infra.items():
            if infra_type not in infrastructure or not isinstance(infra_data, dict):
                continue
            merged = dict(infrastructure[infra_type])
            merged.update(infra_data)
            infrastructure[infra_type] = merged
        return cls(
            system_id=data.get("system_id", ""),
            planet_id=data.get("planet_id", ""),
            name=data.get("name", "New Colony"),
            population=data.get("population", 100),
            happiness=data.get("happiness", 70),
            infrastructure=infrastructure,
            build_queue=list(data.get("build_queue", [])),
        )


class ColonyManager:
    def __init__(self):
        self.colonies: dict[str, Colony] = {}

    def establish_colony(
        self,
        system_id: str,
        planet_id: str,
        name: str,
        initial_pop: int = 100,
    ) -> Colony:
        colony = Colony(
            system_id=system_id,
            planet_id=planet_id,
            name=name,
            population=initial_pop,
        )
        self.colonies[system_id] = colony
        return colony

    def abandon_colony(self, system_id: str) -> bool:
        if system_id in self.colonies:
            del self.colonies[system_id]
            return True
        return False

    def get_total_production(self) -> dict:
        total = {}
        for colony in self.colonies.values():
            prod = colony.calculate_production()
            for r, amount in prod.items():
                total[r] = total.get(r, 0) + amount
        return total

    def get_total_consumption(self) -> dict:
        total = {}
        for colony in self.colonies.values():
            cons = colony.calculate_consumption()
            for r, amount in cons.items():
                total[r] = total.get(r, 0) + amount
        return total

    def process_all_turns(self, build_time_reduction: int = 0) -> list:
        reports = []
        for system_id, colony in self.colonies.items():
            report = colony.process_turn(build_time_reduction=build_time_reduction)
            report["system_id"] = system_id
            report["colony_name"] = colony.name
            reports.append(report)
        return reports

    def to_dict(self) -> dict:
        return {
            "colonies": {
                sid: c.to_dict() for sid, c in self.colonies.items()
            }
        }

    @classmethod
    def from_dict(cls, data: dict) -> "ColonyManager":
        cm = cls()
        for sid, cdata in data.get("colonies", {}).items():
            cm.colonies[sid] = Colony.from_dict(cdata)
        return cm
