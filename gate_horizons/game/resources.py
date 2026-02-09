"""Resource management system for Gate Horizons."""


RESOURCE_TYPES = ["energy", "metals", "exotics", "credits", "intel"]


class ResourceManager:
    def __init__(self):
        self.global_resources: dict[str, int] = {r: 0 for r in RESOURCE_TYPES}
        self.per_system_resources: dict[str, dict[str, int]] = {}
        self._income_cache: dict[str, int] = {}
        self._expense_cache: dict[str, int] = {}

    def add(self, resource: str, amount: int, system_id: str = None) -> None:
        if resource not in RESOURCE_TYPES:
            return
        amount = max(0, amount)
        self.global_resources[resource] = self.global_resources.get(resource, 0) + amount
        if system_id:
            if system_id not in self.per_system_resources:
                self.per_system_resources[system_id] = {r: 0 for r in RESOURCE_TYPES}
            self.per_system_resources[system_id][resource] += amount

    def spend(self, resource: str, amount: int, system_id: str = None) -> bool:
        if resource not in RESOURCE_TYPES:
            return False
        current = self.global_resources.get(resource, 0)
        if current < amount:
            return False
        self.global_resources[resource] = current - amount
        if system_id and system_id in self.per_system_resources:
            sys_current = self.per_system_resources[system_id].get(resource, 0)
            self.per_system_resources[system_id][resource] = max(0, sys_current - amount)
        return True

    def spend_and_return_actual(self, resource: str, amount: int, system_id: str = None) -> int:
        if resource not in RESOURCE_TYPES:
            return 0
        amount = max(0, amount)
        current = self.global_resources.get(resource, 0)
        actual = min(current, amount)
        if actual <= 0:
            return 0
        self.global_resources[resource] = current - actual
        if system_id and system_id in self.per_system_resources:
            sys_current = self.per_system_resources[system_id].get(resource, 0)
            self.per_system_resources[system_id][resource] = max(0, sys_current - actual)
        return actual

    def can_afford(self, cost_dict: dict) -> bool:
        for resource, amount in cost_dict.items():
            if resource in ("turns",):  # Skip non-resource costs
                continue
            if self.global_resources.get(resource, 0) < amount:
                return False
        return True

    def spend_dict(self, cost_dict: dict) -> bool:
        """Spend multiple resources at once. Only spends if all can be afforded."""
        if not self.can_afford(cost_dict):
            return False
        for resource, amount in cost_dict.items():
            if resource in ("turns",):
                continue
            self.spend(resource, amount)
        return True

    def spend_from_colony(self, resource: str, amount: int, colony) -> bool:
        if resource not in RESOURCE_TYPES or amount <= 0 or colony is None:
            return False
        if self.global_resources.get(resource, 0) < amount:
            return False
        current = colony.stockpiles.get(resource, 0)
        if current < amount:
            return False
        colony.stockpiles[resource] = current - amount
        self.global_resources[resource] -= amount
        system_id = getattr(colony, "system_id", None)
        if system_id and system_id in self.per_system_resources:
            sys_current = self.per_system_resources[system_id].get(resource, 0)
            self.per_system_resources[system_id][resource] = max(0, sys_current - amount)
        return True

    def spend_from_colonies(self, resource: str, amount: int, colonies, owner_faction: str = "player") -> bool:
        if resource not in RESOURCE_TYPES or amount <= 0 or colonies is None:
            return False
        if self.global_resources.get(resource, 0) < amount:
            return False
        eligible = [
            (system_id, colony)
            for system_id, colony in colonies.colonies.items()
            if colony.owner_faction == owner_faction
        ]
        total_available = sum(colony.stockpiles.get(resource, 0) for _, colony in eligible)
        if total_available < amount:
            return False
        remaining = amount
        for system_id, colony in sorted(eligible, key=lambda item: item[0]):
            if remaining <= 0:
                break
            available = colony.stockpiles.get(resource, 0)
            if available <= 0:
                continue
            take = min(available, remaining)
            colony.stockpiles[resource] = available - take
            self.global_resources[resource] -= take
            if system_id in self.per_system_resources:
                sys_current = self.per_system_resources[system_id].get(resource, 0)
                self.per_system_resources[system_id][resource] = max(0, sys_current - take)
            remaining -= take
        return remaining == 0

    def get_income_summary(self) -> dict:
        """Return cached per-turn income summary."""
        return dict(self._income_cache)

    def get_expense_summary(self) -> dict:
        """Return cached per-turn expense summary."""
        return dict(self._expense_cache)

    def get_net_summary(self) -> dict:
        """Return net per-turn for each resource."""
        net = {}
        for r in RESOURCE_TYPES:
            net[r] = self._income_cache.get(r, 0) - self._expense_cache.get(r, 0)
        return net

    def update_projections(self, income: dict, expenses: dict) -> None:
        """Update the income/expense projections (called during turn processing)."""
        self._income_cache = dict(income)
        self._expense_cache = dict(expenses)

    def sync_from_colonies(self, colonies) -> None:
        """Synchronize global and per-system resources from colony stockpiles."""
        if not colonies:
            return
        per_system = {}
        totals = {r: 0 for r in RESOURCE_TYPES}
        for system_id, colony in colonies.colonies.items():
            per_system[system_id] = {r: 0 for r in RESOURCE_TYPES}
            for resource in RESOURCE_TYPES:
                amount = int(colony.stockpiles.get(resource, 0))
                per_system[system_id][resource] = amount
                totals[resource] += amount
        self.per_system_resources = per_system
        self.global_resources = totals

    def process_turn(self, colonies=None, fleet=None, include_maintenance: bool = True) -> dict:
        """Calculate all production/consumption and apply. Returns summary."""
        income = {r: 0 for r in RESOURCE_TYPES}
        expenses = {r: 0 for r in RESOURCE_TYPES}

        # Colony production
        if colonies:
            for colony in colonies.colonies.values():
                prod = colony.calculate_production()
                for r, amount in prod.items():
                    if r in RESOURCE_TYPES:
                        income[r] += amount
                        self.add(r, amount, colony.system_id)

                cons = colony.calculate_consumption()
                for r, amount in cons.items():
                    if r in RESOURCE_TYPES:
                        expenses[r] += amount

        # Ship maintenance (optional when handled elsewhere)
        if fleet and include_maintenance:
            maintenance = fleet.get_total_maintenance()
            expenses["credits"] += maintenance

        # Apply expenses
        for r, amount in expenses.items():
            if amount > 0:
                self.spend(r, amount)

        self.update_projections(income, expenses)

        return {
            "income": income,
            "expenses": expenses,
            "net": {r: income.get(r, 0) - expenses.get(r, 0) for r in RESOURCE_TYPES},
        }

    def to_dict(self) -> dict:
        return {
            "global_resources": dict(self.global_resources),
            "per_system_resources": {
                k: dict(v) for k, v in self.per_system_resources.items()
            },
            "income_cache": dict(self._income_cache),
            "expense_cache": dict(self._expense_cache),
        }

    @classmethod
    def from_dict(cls, data: dict) -> "ResourceManager":
        rm = cls()
        global_resources = data.get("global_resources") or {}
        rm.global_resources = {
            r: int(global_resources.get(r, 0)) for r in RESOURCE_TYPES
        }
        per_system = data.get("per_system_resources") or {}
        rm.per_system_resources = {}
        for system_id, resources in per_system.items():
            if not isinstance(resources, dict):
                continue
            rm.per_system_resources[system_id] = {
                r: int(resources.get(r, 0)) for r in RESOURCE_TYPES
            }
        income_cache = data.get("income_cache") or {}
        rm._income_cache = {r: int(income_cache.get(r, 0)) for r in RESOURCE_TYPES}
        expense_cache = data.get("expense_cache") or {}
        rm._expense_cache = {r: int(expense_cache.get(r, 0)) for r in RESOURCE_TYPES}
        return rm
