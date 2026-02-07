"""Turn processing system for Gate Horizons.

Turn Resolution Order (deterministic, explicit):
=================================================
Phase A — Ship & Mining (unchanged from original)
  A1. Process ship movements
  A2. Process mining operations

Phase B — Colony Logistics (NEW — abstracted per-turn flows)
  B1. Apply arrivals from in-transit queue -> add to colony stockpiles
  B2. Compute colony production -> add to stockpiles (respect storage caps)
  B3. Compute colony consumption/upkeep -> subtract from stockpiles; record shortages
  B4. Apply shortage penalties -> stability/growth modifiers
  B5. Compute trade flows -> create in-transit shipments with latency

Phase C — Construction & Research
  C1. Process construction queues (infrastructure, ships)
  C2. Process tech research

Phase D — Economy & Events
  D1. Apply maintenance costs
  D2. Process resource economy (global level)
  D3. Check event triggers

Phase E — State Updates
  E1. Update fog of war
  E2. Check warnings
  E3. Check milestones

This is NOT Factorio. No belt/item micromanagement. Resources flow
as abstracted per-turn quantities through the logistics network.
"""

from dataclasses import dataclass, field
from typing import Optional

from .clock import GameClock


MONTHS = [
    "January", "February", "March", "April", "May", "June",
    "July", "August", "September", "October", "November", "December",
]


def turn_to_date(turn_number: int, start_year: int = 2157) -> str:
    """Convert turn number to game date string."""
    month_index = (turn_number - 1) % 12
    year = start_year + (turn_number - 1) // 12
    return f"{MONTHS[month_index]} {year}"


@dataclass
class TurnReport:
    turn_number: int = 0
    game_date: str = ""
    ships_moved: list = field(default_factory=list)
    resources_gained: dict = field(default_factory=dict)
    resources_spent: dict = field(default_factory=dict)
    construction_completed: list = field(default_factory=list)
    events_triggered: list = field(default_factory=list)
    combat_encounters: list = field(default_factory=list)
    discoveries: list = field(default_factory=list)
    warnings: list = field(default_factory=list)
    milestone_reached: str = None
    tech_completed: str = None
    colony_reports: list = field(default_factory=list)
    trade_reports: list = field(default_factory=list)
    mining_output: dict = field(default_factory=dict)
    logistics_arrivals: list = field(default_factory=list)
    logistics_shipments: list = field(default_factory=list)
    shortage_reports: dict = field(default_factory=dict)

    def to_dict(self) -> dict:
        return {
            "turn_number": self.turn_number,
            "game_date": self.game_date,
            "ships_moved": self.ships_moved,
            "resources_gained": dict(self.resources_gained),
            "resources_spent": dict(self.resources_spent),
            "construction_completed": self.construction_completed,
            "events_triggered": [
                e.to_dict() if hasattr(e, "to_dict") else e
                for e in self.events_triggered
            ],
            "combat_encounters": [
                c.to_dict() if hasattr(c, "to_dict") else c
                for c in self.combat_encounters
            ],
            "discoveries": self.discoveries,
            "warnings": self.warnings,
            "milestone_reached": self.milestone_reached,
            "tech_completed": self.tech_completed,
            "colony_reports": self.colony_reports,
            "trade_reports": self.trade_reports,
            "mining_output": dict(self.mining_output),
            "logistics_arrivals": self.logistics_arrivals,
            "logistics_shipments": self.logistics_shipments,
            "shortage_reports": dict(self.shortage_reports),
        }

    def get_summary_lines(self) -> list:
        """Get human-readable summary lines for the turn report."""
        lines = []
        lines.append(f"Turn {self.turn_number} — {self.game_date}")
        lines.append("")

        if self.ships_moved:
            arrived = [m for m in self.ships_moved if m.get("arrived")]
            in_transit = [m for m in self.ships_moved if not m.get("arrived")]
            if arrived:
                lines.append(f"{len(arrived)} ship(s) arrived at destinations")
            if in_transit:
                lines.append(f"{len(in_transit)} ship(s) in transit")

        if self.mining_output:
            parts = [f"{amt} {res}" for res, amt in self.mining_output.items() if amt > 0]
            if parts:
                lines.append(f"Mining produced: {', '.join(parts)}")

        if self.logistics_arrivals:
            lines.append(f"{len(self.logistics_arrivals)} logistics delivery(s) arrived")

        if self.logistics_shipments:
            active = [s for s in self.logistics_shipments if s.get("shipped")]
            if active:
                lines.append(f"{len(active)} trade shipment(s) dispatched")

        if self.trade_reports:
            active_trades = [t for t in self.trade_reports if t.get("transferred")]
            if active_trades:
                lines.append(f"{len(active_trades)} trade route(s) active")

        for report in self.colony_reports:
            name = report.get("colony_name", "Unknown")
            growth = report.get("population_growth", 0)
            if growth > 0:
                lines.append(f"Colony {name}: +{growth} population")
            for completed in report.get("construction_completed", []):
                lines.append(f"Colony {name}: {completed} construction complete!")

        if self.shortage_reports:
            for system_id, shortages in self.shortage_reports.items():
                if shortages.get("stability_loss", 0) > 0:
                    lines.append(f"SHORTAGE at {system_id}: stability -{shortages['stability_loss']}")

        if self.tech_completed:
            lines.append(f"RESEARCH COMPLETE: {self.tech_completed}")

        if self.construction_completed:
            for item in self.construction_completed:
                lines.append(f"Construction complete: {item}")

        if self.events_triggered:
            for event in self.events_triggered:
                title = event.title if hasattr(event, "title") else event.get("title", "Unknown")
                lines.append(f"EVENT: {title}")

        if self.combat_encounters:
            for combat in self.combat_encounters:
                narrative = combat.narrative if hasattr(combat, "narrative") else combat.get("narrative", "")
                lines.append(f"COMBAT: {narrative[:80]}...")

        for warning in self.warnings:
            lines.append(f"WARNING: {warning}")

        if self.milestone_reached:
            lines.append(f"MILESTONE: {self.milestone_reached}")

        return lines


class TurnProcessor:
    def process_turn(self, game_state) -> TurnReport:
        """Execute a full turn following the deterministic resolution order.

        See module docstring for the complete turn resolution order.
        """
        report = TurnReport()
        clock = getattr(game_state, "game_clock", None)
        if clock is None:
            clock = GameClock(current_tick=game_state.turn_number, turn_number=game_state.turn_number)
            game_state.game_clock = clock

        clock.advance_turn()
        game_state.turn_number = clock.turn_number
        report.turn_number = clock.turn_number
        report.game_date = turn_to_date(clock.turn_number)
        game_state.game_time = report.game_date

        # ============================================================
        # Phase A — Ship & Mining
        # ============================================================

        # A1. Process ship movements
        if clock.mark_processed("movements"):
            self._process_movements(game_state, report)

        # A2. Process mining operations
        if clock.mark_processed("mining"):
            self._process_mining(game_state, report)

        # ============================================================
        # Phase B — Colony Logistics (5-step deterministic order)
        # ============================================================

        # B1. Apply arrivals from in-transit queue -> add to colony stockpiles
        if clock.mark_processed("logistics_arrivals"):
            self._process_logistics_arrivals(game_state, report)

        # B2. Compute colony production -> add to stockpiles (respect storage caps)
        if clock.mark_processed("colony_production"):
            self._process_colony_production(game_state, report)

        # B3. Compute colony consumption/upkeep -> subtract from stockpiles
        if clock.mark_processed("colony_consumption"):
            self._process_colony_consumption(game_state, report)

        # B4. Apply shortage penalties -> stability/growth modifiers
        if clock.mark_processed("shortage_penalties"):
            self._process_shortage_penalties(game_state, report)

        # B5. Compute trade flows -> create in-transit shipments with latency
        if clock.mark_processed("logistics_shipments"):
            self._process_logistics_shipments(game_state, report)

        # ============================================================
        # Phase C — Construction & Research
        # ============================================================

        # C1. Process construction queues (infrastructure, ships)
        if clock.mark_processed("colonies"):
            self._process_colonies(game_state, report)

        # C2. Process tech research
        if clock.mark_processed("research"):
            self._process_research(game_state, report)

        # ============================================================
        # Phase D — Economy & Events
        # ============================================================

        # D1. Apply maintenance costs
        if clock.mark_processed("maintenance"):
            self._process_maintenance(game_state, report)

        # D2. Process resource economy (global level)
        if clock.mark_processed("resources"):
            self._process_resources(game_state, report)

        # D3. Check event triggers
        if clock.mark_processed("events"):
            self._process_events(game_state, report)

        # ============================================================
        # Phase E — State Updates
        # ============================================================

        # E1. Update fog of war
        if clock.mark_processed("fog_of_war"):
            self._update_fog_of_war(game_state, report)

        # E2. Check warnings
        if clock.mark_processed("warnings"):
            self._check_warnings(game_state, report)

        # E3. Check milestones
        if clock.mark_processed("milestones"):
            self._check_milestones(game_state, report)

        # Add to log
        if clock.mark_processed("turn_log"):
            game_state.log.append(f"Turn {report.turn_number}: {report.game_date}")

        return report

    # ================================================================
    # Phase A — Ship & Mining
    # ================================================================

    def _process_movements(self, game_state, report: TurnReport) -> None:
        ships_to_process = [
            s for s in game_state.fleet.ships.values()
            if s.path
        ]
        tech_effects = game_state.tech.get_effects() if hasattr(game_state, "tech") else {}
        fuel_efficiency = tech_effects.get("fuel_efficiency", 1.0)

        for ship in ships_to_process:
            if not game_state.game_clock.mark_processed("movements", ship.id):
                continue
            result = game_state.fleet.process_movement(ship.id, fuel_efficiency=fuel_efficiency)
            report.ships_moved.append({
                "ship_id": ship.id,
                "ship_name": ship.name,
                "arrived": result.arrived,
                "location": result.current_location,
                "fuel_consumed": result.fuel_consumed,
            })

            if result.arrived or result.current_location:
                system = game_state.galaxy.systems.get(result.current_location)
                if system and hasattr(game_state, "combat"):
                    encounter = game_state.combat.generate_random_encounter(system.tier)
                    if encounter:
                        combat_result = game_state.combat.auto_resolve([ship], encounter)
                        report.combat_encounters.append(combat_result)
                        for resource, amount in combat_result.loot.items():
                            game_state.resources.add(resource, amount)
                        for destroyed_id in combat_result.ships_destroyed:
                            game_state.fleet.destroy_ship(destroyed_id)

    def _process_mining(self, game_state, report: TurnReport) -> None:
        mining_output = {}
        for ship in game_state.fleet.ships.values():
            if not ship.mining or ship.ship_class != "miner":
                continue

            system = game_state.galaxy.systems.get(ship.location)
            if not system:
                continue

            for planet in system.planets:
                for resource, yield_per_turn in planet.resources.items():
                    if yield_per_turn > 0:
                        tech_effects = game_state.tech.get_effects() if hasattr(game_state, "tech") else {}
                        mining_mult = tech_effects.get("mining_yield", 1.0)
                        amount = int(yield_per_turn * mining_mult)
                        added = ship.add_cargo(resource, amount)
                        mining_output[resource] = mining_output.get(resource, 0) + added

        for ship in game_state.fleet.ships.values():
            if ship.ship_class != "miner" or not ship.cargo:
                continue
            at_colony = ship.location in game_state.colonies.colonies if hasattr(game_state, "colonies") else False
            cargo_full = ship.cargo_used >= ship.stats.cargo_capacity * 0.8
            if at_colony or cargo_full:
                for resource, amount in list(ship.cargo.items()):
                    game_state.resources.add(resource, amount, ship.location)
                ship.cargo.clear()

        report.mining_output = mining_output

    # ================================================================
    # Phase B — Colony Logistics (5-step deterministic order)
    # ================================================================

    def _process_logistics_arrivals(self, game_state, report: TurnReport) -> None:
        """B1: Apply arrivals from in-transit queue -> add to colony stockpiles."""
        if hasattr(game_state, "trade"):
            arrivals = game_state.trade.process_arrivals(
                colonies=game_state.colonies if hasattr(game_state, "colonies") else None,
            )
            report.logistics_arrivals = arrivals

    def _process_colony_production(self, game_state, report: TurnReport) -> None:
        """B2: Compute colony production -> add to stockpiles (respect storage caps)."""
        if not hasattr(game_state, "colonies"):
            return

        tech_effects = game_state.tech.get_effects() if hasattr(game_state, "tech") else {}
        industry_bonus = tech_effects.get("industry_bonus", 1.0)
        research_bonus = tech_effects.get("research_bonus", 0)

        for system_id, colony in game_state.colonies.colonies.items():
            production = colony.calculate_production()

            # Apply tech bonuses
            if industry_bonus > 1.0:
                production["metals"] = int(production.get("metals", 0) * industry_bonus)
                production["energy"] = int(production.get("energy", 0) * industry_bonus)

            # Research acceleration: +bonus per colony with research lab
            if research_bonus > 0:
                research_level = colony.infrastructure.get("research", {}).get("level", 0)
                if research_level >= 1:
                    production["intel"] = production.get("intel", 0) + research_bonus

            # Add to colony stockpiles, respect storage caps
            caps = colony.get_storage_caps()
            for resource, amount in production.items():
                if amount <= 0:
                    continue
                current = colony.stockpiles.get(resource, 0)
                cap = caps.get(resource, 100)
                added = min(amount, cap - current)
                if added > 0:
                    colony.stockpiles[resource] = current + added
                    report.resources_gained[resource] = report.resources_gained.get(resource, 0) + added

    def _process_colony_consumption(self, game_state, report: TurnReport) -> None:
        """B3: Compute colony consumption/upkeep -> subtract from stockpiles."""
        if not hasattr(game_state, "colonies"):
            return

        for system_id, colony in game_state.colonies.colonies.items():
            consumption = colony.calculate_consumption()
            shortages = {}

            for resource, amount in consumption.items():
                if amount <= 0:
                    continue
                available = colony.stockpiles.get(resource, 0)
                consumed = min(amount, available)
                colony.stockpiles[resource] = available - consumed
                report.resources_spent[resource] = report.resources_spent.get(resource, 0) + consumed

                # Record shortage if can't fully cover consumption
                deficit = amount - consumed
                if deficit > 0:
                    shortages[resource] = deficit

            # Store shortages for penalty step
            colony._pending_shortages = shortages

    def _process_shortage_penalties(self, game_state, report: TurnReport) -> None:
        """B4: Apply shortage penalties -> stability/growth modifiers."""
        if not hasattr(game_state, "colonies"):
            return

        for system_id, colony in game_state.colonies.colonies.items():
            shortages = getattr(colony, "_pending_shortages", {})
            penalties = colony.apply_shortage_penalties(shortages)
            if shortages or penalties.get("stability_loss", 0) > 0:
                report.shortage_reports[system_id] = {
                    "shortages": dict(shortages),
                    **penalties,
                }
            # Clean up temporary attribute
            if hasattr(colony, "_pending_shortages"):
                del colony._pending_shortages

    def _process_logistics_shipments(self, game_state, report: TurnReport) -> None:
        """B5: Compute trade flows -> create in-transit shipments with latency."""
        if hasattr(game_state, "trade"):
            shipment_reports = game_state.trade.compute_and_ship(
                colonies=game_state.colonies if hasattr(game_state, "colonies") else None,
                resources=game_state.resources if hasattr(game_state, "resources") else None,
            )
            report.logistics_shipments = shipment_reports

    # ================================================================
    # Phase C — Construction & Research
    # ================================================================

    def _process_colonies(self, game_state, report: TurnReport) -> None:
        """C1: Process construction queues, shipyard, population growth."""
        if hasattr(game_state, "colonies"):
            tech_effects = game_state.tech.get_effects() if hasattr(game_state, "tech") else {}
            build_time_reduction = int(tech_effects.get("build_time_reduction", 0))

            colony_reports = game_state.colonies.process_all_turns(
                build_time_reduction=build_time_reduction,
            )
            report.colony_reports = colony_reports

            for cr in colony_reports:
                for completed in cr.get("construction_completed", []):
                    report.construction_completed.append(
                        f"{cr.get('colony_name', 'Unknown')}: {completed}"
                    )
                for ship_info in cr.get("ships_completed", []):
                    system_id = cr.get("system_id", "")
                    ship = game_state.fleet.create_ship(
                        ship_info["ship_class"],
                        system_id,
                        ship_info["name"],
                    )
                    if ship:
                        report.construction_completed.append(
                            f"{cr.get('colony_name', 'Unknown')}: {ship.name} launched!"
                        )

    def _process_research(self, game_state, report: TurnReport) -> None:
        if hasattr(game_state, "tech"):
            completed = game_state.tech.process_turn(
                resources=game_state.resources if hasattr(game_state, "resources") else None,
            )
            if completed:
                tech = game_state.tech.techs.get(completed)
                report.tech_completed = tech.name if tech else completed
                self._apply_tech_effects(game_state, completed)

    def _apply_tech_effects(self, game_state, tech_id: str) -> None:
        """Apply the effects of a newly completed tech."""
        tech = game_state.tech.techs.get(tech_id)
        if not tech:
            return

        effects = tech.effect

        if "combat_accuracy_bonus" in effects and hasattr(game_state, "combat"):
            game_state.combat.combat_accuracy_bonus += effects["combat_accuracy_bonus"]

        if "speed_bonus" in effects:
            for ship_class, bonus in effects["speed_bonus"].items():
                for ship in game_state.fleet.ships.values():
                    if ship.ship_class == ship_class:
                        ship.stats.speed += bonus

        if "hull_bonus" in effects:
            mult = effects["hull_bonus"]
            for ship in game_state.fleet.ships.values():
                ship.stats.max_hull = int(ship.stats.max_hull * mult)
                ship.hull = min(ship.hull, ship.stats.max_hull)

        if "sensor_bonus" in effects:
            bonus = effects["sensor_bonus"]
            for ship in game_state.fleet.ships.values():
                ship.stats.sensor_range += bonus

    # ================================================================
    # Phase D — Economy & Events
    # ================================================================

    def _process_maintenance(self, game_state, report: TurnReport) -> None:
        maintenance = game_state.fleet.get_total_maintenance()
        if maintenance > 0:
            if game_state.resources.global_resources.get("credits", 0) >= maintenance:
                game_state.resources.spend("credits", maintenance)
                report.resources_spent["credits"] = report.resources_spent.get("credits", 0) + maintenance
            else:
                for ship in game_state.fleet.ships.values():
                    ship.morale = max(0, ship.morale - 5)

    def _process_resources(self, game_state, report: TurnReport) -> None:
        if hasattr(game_state, "colonies"):
            summary = game_state.resources.process_turn(
                colonies=game_state.colonies,
                fleet=game_state.fleet,
                include_maintenance=False,
            )
            for k, v in summary.get("income", {}).items():
                report.resources_gained[k] = report.resources_gained.get(k, 0) + v
            for k, v in summary.get("expenses", {}).items():
                report.resources_spent[k] = report.resources_spent.get(k, 0) + v

    def _process_events(self, game_state, report: TurnReport) -> None:
        if hasattr(game_state, "events"):
            triggered = game_state.events.check_triggers(game_state)
            report.events_triggered = triggered

    # ================================================================
    # Phase E — State Updates
    # ================================================================

    def _update_fog_of_war(self, game_state, report: TurnReport) -> None:
        """Reveal systems within sensor range of player ships."""
        for ship in game_state.fleet.ships.values():
            system = game_state.galaxy.systems.get(ship.location)
            if not system:
                continue

            if not system.discovered:
                system.discovered = True
                report.discoveries.append(f"Discovered {system.name}")

            sensor_range = ship.stats.sensor_range
            self._reveal_in_range(game_state, ship.location, sensor_range, report)

    def _reveal_in_range(self, game_state, center_id: str, range_remaining: int, report: TurnReport) -> None:
        """BFS reveal systems within sensor range."""
        if range_remaining <= 0:
            return

        from collections import deque
        visited = {center_id}
        queue = deque([(center_id, 0)])

        while queue:
            current_id, depth = queue.popleft()
            if depth >= range_remaining:
                continue

            system = game_state.galaxy.systems.get(current_id)
            if not system:
                continue

            for neighbor_id in system.gate_connections:
                if neighbor_id in visited:
                    continue
                visited.add(neighbor_id)

                neighbor = game_state.galaxy.systems.get(neighbor_id)
                if neighbor and not neighbor.discovered:
                    neighbor.discovered = True
                    report.discoveries.append(f"Detected {neighbor.name}")

                queue.append((neighbor_id, depth + 1))

    def _check_warnings(self, game_state, report: TurnReport) -> None:
        for ship in game_state.fleet.ships.values():
            if ship.fuel <= 2 and ship.fuel < ship.stats.fuel_capacity:
                report.warnings.append(f"{ship.name} is low on fuel ({ship.fuel} remaining)")

        for resource, amount in game_state.resources.global_resources.items():
            if amount <= 0:
                report.warnings.append(f"{resource.title()} reserves depleted!")
            elif amount < 10:
                report.warnings.append(f"{resource.title()} reserves low ({amount})")

        if hasattr(game_state, "colonies"):
            for colony in game_state.colonies.colonies.values():
                if colony.happiness < 30:
                    report.warnings.append(f"Colony {colony.name} is unhappy ({colony.happiness}%)")
                if colony.stability < 30:
                    report.warnings.append(f"Colony {colony.name} stability critical ({colony.stability}%)")

    def _check_milestones(self, game_state, report: TurnReport) -> None:
        num_colonies = len(game_state.colonies.colonies) if hasattr(game_state, "colonies") else 0
        num_discovered = sum(1 for s in game_state.galaxy.systems.values() if s.discovered)
        total_systems = len(game_state.galaxy.systems)

        if num_discovered == total_systems and "all_discovered" not in game_state.log:
            report.milestone_reached = "All systems discovered!"
            game_state.log.append("all_discovered")

        if num_colonies >= 3 and "three_colonies" not in game_state.log:
            report.milestone_reached = "Established three colonies!"
            game_state.log.append("three_colonies")

        if game_state.turn_number == 50 and "fifty_turns" not in game_state.log:
            report.milestone_reached = "50 turns completed — veteran explorer!"
            game_state.log.append("fifty_turns")
