"""Turn processing system for Gate Horizons.

Turn Resolution Order (deterministic, explicit):
=================================================
Phase A — Ship & Mining (unchanged from original)
  A0. Execute queued ship orders + action handlers
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
from .resources import RESOURCE_TYPES


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
    # Production loop reports
    extraction_output: dict = field(default_factory=dict)
    factory_output: dict = field(default_factory=dict)
    freighter_route_reports: list = field(default_factory=list)
    shipyard_report: dict = field(default_factory=dict)
    ship_actions: list = field(default_factory=list)
    ship_orders: list = field(default_factory=list)
    missions_generated: list = field(default_factory=list)
    missions_completed: list = field(default_factory=list)
    missions_active: list = field(default_factory=list)
    colony_ledger_entries: dict = field(default_factory=dict)
    colony_ledger_summary: str = ""

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
            "extraction_output": dict(self.extraction_output),
            "factory_output": dict(self.factory_output),
            "freighter_route_reports": self.freighter_route_reports,
            "shipyard_report": dict(self.shipyard_report),
            "ship_actions": self.ship_actions,
            "ship_orders": self.ship_orders,
            "missions_generated": self.missions_generated,
            "missions_completed": self.missions_completed,
            "missions_active": self.missions_active,
            "colony_ledger_entries": dict(self.colony_ledger_entries),
            "colony_ledger_summary": self.colony_ledger_summary,
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

        if self.ship_actions:
            lines.append(f"{len(self.ship_actions)} ship action(s) completed")
            for action in self.ship_actions:
                summary = action.get("summary")
                if summary:
                    lines.append(summary)

        if self.ship_orders:
            completed = [o for o in self.ship_orders if o.get("status") == "completed"]
            failed = [o for o in self.ship_orders if o.get("status") == "failed"]
            delayed = [o for o in self.ship_orders if o.get("status") == "delayed"]
            if completed:
                lines.append(f"{len(completed)} ship order(s) completed")
            if failed:
                lines.append(f"{len(failed)} ship order(s) failed")
                for order in failed:
                    summary = order.get("summary")
                    if summary:
                        lines.append(summary)
            if delayed:
                lines.append(f"{len(delayed)} ship order(s) delayed")

        if self.missions_generated:
            for mission in self.missions_generated:
                title = mission.get("title", "Mission")
                description = mission.get("description", "")
                if description:
                    lines.append(f"New mission: {title} — {description}")
                else:
                    lines.append(f"New mission: {title}")

        if self.missions_completed:
            for mission in self.missions_completed:
                title = mission.get("title", "Mission")
                reward = mission.get("reward", {})
                reward_text = ", ".join(
                    f"{amount} {resource}" for resource, amount in reward.items()
                )
                suffix = f" (Rewards: {reward_text})" if reward_text else ""
                lines.append(f"MISSION COMPLETE: {title}{suffix}")

        if self.missions_active:
            lines.append("Active missions:")
            for mission in self.missions_active:
                title = mission.get("title", "Mission")
                progress = mission.get("progress_summary", "")
                description = mission.get("description", "")
                detail = f"{description}" if description else title
                if progress:
                    lines.append(f"{detail} ({progress})")
                else:
                    lines.append(detail)

        if self.discoveries:
            for discovery in self.discoveries:
                lines.append(discovery)

        if self.mining_output:
            parts = [f"{amt} {res}" for res, amt in self.mining_output.items() if amt > 0]
            if parts:
                lines.append(f"Mining produced: {', '.join(parts)}")

        if self.extraction_output:
            parts = [f"{amt} {res}" for res, amt in self.extraction_output.items() if amt > 0]
            if parts:
                lines.append(f"Extraction produced: {', '.join(parts)}")

        if self.factory_output:
            parts = [f"{amt} {res}" for res, amt in self.factory_output.items() if amt > 0]
            if parts:
                lines.append(f"Factories produced: {', '.join(parts)}")

        if self.freighter_route_reports:
            active = [r for r in self.freighter_route_reports if r.get("actions")]
            if active:
                lines.append(f"{len(active)} freighter route(s) active")

        if self.shipyard_report:
            completed_ships = self.shipyard_report.get("ships_completed", [])
            completed_facilities = self.shipyard_report.get("facilities_completed", [])
            for s in completed_ships:
                lines.append(f"Ship completed: {s.get('ship_name', 'Unknown')}")
            for f in completed_facilities:
                lines.append(f"Facility completed: {f.get('facility_type', 'Unknown')} at {f.get('system_id', 'Unknown')}")

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
            stability_delta = report.get("stability_trait_adjustment", 0)
            if stability_delta:
                sign = "+" if stability_delta > 0 else ""
                lines.append(f"Colony {name}: stability {sign}{stability_delta} from traits")

        if self.shortage_reports:
            for system_id, shortages in self.shortage_reports.items():
                if shortages.get("stability_loss", 0) > 0:
                    lines.append(f"SHORTAGE at {system_id}: stability -{shortages['stability_loss']}")

        for system_id, entry in self.colony_ledger_entries.items():
            trait_effects = entry.get("trait_effects", {})
            exotics_bonus = trait_effects.get("exotics_bonus", 0)
            if exotics_bonus:
                colony_name = entry.get("colony_name", system_id)
                lines.append(f"Colony {colony_name}: +{exotics_bonus} exotics from traits")

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

        if hasattr(game_state, "process_ship_orders"):
            game_state.process_ship_orders(report)

        if hasattr(game_state, "pending_ship_actions"):
            report.ship_actions = list(game_state.pending_ship_actions)
            game_state.pending_ship_actions = []
            for action in report.ship_actions:
                for discovery in action.get("discoveries", []):
                    report.discoveries.append(discovery)
                for resource, amount in action.get("resources_spent", {}).items():
                    report.resources_spent[resource] = (
                        report.resources_spent.get(resource, 0) + amount
                    )

        # ============================================================
        # Phase A — Ship & Mining
        # ============================================================

        # A1. Process ship movements
        if clock.mark_processed("movements"):
            self._process_movements(game_state, report)

        # A2. Process mining operations
        if clock.mark_processed("mining"):
            self._process_mining(game_state, report)

        # A3. Process production extraction (new raw resource extraction)
        if clock.mark_processed("extraction"):
            self._process_extraction(game_state, report)

        # A4. Process factory production (recipes -> components)
        if clock.mark_processed("factories"):
            self._process_factories(game_state, report)

        # A5. Process freighter route execution (physical cargo movement)
        if clock.mark_processed("freighter_routes"):
            self._process_freighter_routes(game_state, report)

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

        if clock.mark_processed("colony_ledger"):
            self._finalize_colony_ledger(game_state, report)

        # ============================================================
        # Phase C — Construction & Research
        # ============================================================

        # C1. Process construction queues (infrastructure, ships)
        if clock.mark_processed("colonies"):
            self._process_colonies(game_state, report)

        # C1b. Process orbital shipyard builds
        if clock.mark_processed("shipyard"):
            self._process_shipyard(game_state, report)

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

        # E1b. Check mission progress and generate new missions
        if clock.mark_processed("missions"):
            self._process_missions(game_state, report)

        # E2. Check warnings
        if clock.mark_processed("warnings"):
            self._check_warnings(game_state, report)

        # E3. Check milestones
        if clock.mark_processed("milestones"):
            self._check_milestones(game_state, report)

        # Add to log
        if clock.mark_processed("turn_log"):
            game_state.log.append(f"Turn {report.turn_number}: {report.game_date}")
            if report.colony_ledger_summary:
                game_state.log.append(f"Ledger: {report.colony_ledger_summary}")

        return report

    def _process_missions(self, game_state, report: TurnReport) -> None:
        if not hasattr(game_state, "missions"):
            return

        completed = game_state.missions.check_completions(game_state, report)
        generated = game_state.missions.generate_turn_mission(game_state)

        report.missions_completed = [self._mission_report_entry(m) for m in completed]
        report.missions_generated = [self._mission_report_entry(m) for m in generated]
        report.missions_active = [
            self._mission_report_entry(m) for m in game_state.missions.active_missions
        ]

    @staticmethod
    def _mission_report_entry(mission) -> dict:
        data = mission.to_dict() if hasattr(mission, "to_dict") else dict(mission)
        if hasattr(mission, "progress_summary"):
            data["progress_summary"] = mission.progress_summary()
        return data

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
                    gate_capacity = None
                    if hasattr(game_state, "galaxy"):
                        gate_capacity = game_state.galaxy.get_gate_effective_capacity(system.id)
                    encounter_rng = None
                    if hasattr(game_state, "rng_for_context"):
                        encounter_rng = game_state.rng_for_context(
                            f"encounter:{ship.id}:{system.id}:{report.turn_number}"
                        )
                    encounter = game_state.combat.generate_random_encounter(
                        system.tier,
                        gate_capacity=gate_capacity,
                        rng=encounter_rng,
                    )
                    if encounter:
                        if hasattr(game_state, "resolve_encounter"):
                            game_state.resolve_encounter([ship], encounter, system, report)
                        else:
                            encounter_id = f"enc-{ship.id[-4:]}-{report.turn_number}"
                            encounter_spec = game_state.combat.create_encounter_spec(
                                attacker_ships=[ship],
                                defender=encounter,
                                system=system,
                                encounter_id=encounter_id,
                            )
                            combat_rng = None
                            if hasattr(game_state, "rng_for_context"):
                                combat_rng = game_state.rng_for_context(
                                    f"combat:{ship.id}:{system.id}:{report.turn_number}"
                                )
                            combat_result = game_state.combat.auto_resolve(
                                [ship],
                                encounter,
                                rng=combat_rng,
                            )
                            combat_result.encounter_id = encounter_id
                            combat_result.encounter_contract = encounter_spec.to_dict()
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

    def _process_extraction(self, game_state, report: TurnReport) -> None:
        """A3: Process raw resource extraction at all colonies."""
        if not hasattr(game_state, "colonies") or not hasattr(game_state, "production"):
            return

        tech_effects = game_state.tech.get_effects() if hasattr(game_state, "tech") else {}
        mining_mult = tech_effects.get("mining_yield", 1.0)

        total_extracted = {}
        for system_id, colony in game_state.colonies.colonies.items():
            if not colony.extraction_sites:
                continue
            storage_caps = game_state.production.get_storage_caps(colony)
            mining_level = colony.infrastructure.get("mining", {}).get("level", 0)
            extracted = game_state.production.process_extraction(
                extraction_sites=colony.extraction_sites,
                inventory=colony.production_inventory,
                mining_level=mining_level,
                tech_mult=mining_mult,
                storage_caps=storage_caps,
            )
            for res, amt in extracted.items():
                total_extracted[res] = total_extracted.get(res, 0) + amt

        report.extraction_output = total_extracted

    def _process_factories(self, game_state, report: TurnReport) -> None:
        """A4: Process factory recipe production at all colonies."""
        if not hasattr(game_state, "colonies") or not hasattr(game_state, "production"):
            return

        total_produced = {}
        for system_id, colony in game_state.colonies.colonies.items():
            if not colony.factories:
                continue
            storage_caps = game_state.production.get_storage_caps(colony)
            throughput_cap = game_state.production.get_factory_throughput(colony)
            industry_level = colony.infrastructure.get("industry", {}).get("level", 0)
            produced = game_state.production.process_factories(
                factories=colony.factories,
                inventory=colony.production_inventory,
                throughput_cap=throughput_cap,
                industry_level=industry_level,
                colony_level=colony.level,
                storage_caps=storage_caps,
            )
            for res, amt in produced.items():
                total_produced[res] = total_produced.get(res, 0) + amt

        report.factory_output = total_produced

    def _process_freighter_routes(self, game_state, report: TurnReport) -> None:
        """A5: Process physical freighter route execution."""
        if not hasattr(game_state, "logistics"):
            return

        # Build production inventories map
        prod_inventories = {}
        if hasattr(game_state, "colonies"):
            for system_id, colony in game_state.colonies.colonies.items():
                prod_inventories[system_id] = colony.production_inventory

        route_reports = game_state.logistics.process_routes(
            fleet=game_state.fleet,
            colonies=game_state.colonies if hasattr(game_state, "colonies") else None,
            galaxy=game_state.galaxy,
            production_inventories=prod_inventories,
        )
        report.freighter_route_reports = route_reports

    @staticmethod
    def _ensure_colony_ledger_entry(report: TurnReport, system_id: str) -> dict:
        entry = report.colony_ledger_entries.setdefault(
            system_id,
            {
                "production": {},
                "consumption": {},
                "imports": {},
                "exports": {},
                "net": {},
                "bottlenecks": [],
            },
        )
        return entry

    @staticmethod
    def _add_resource_delta(bucket: dict, resource: str, amount: int) -> None:
        if amount == 0:
            return
        bucket[resource] = bucket.get(resource, 0) + amount

    # ================================================================
    # Phase B — Colony Logistics (5-step deterministic order)
    # ================================================================

    def _process_logistics_arrivals(self, game_state, report: TurnReport) -> None:
        """B1: Apply arrivals from in-transit queue -> add to colony stockpiles."""
        if hasattr(game_state, "trade"):
            arrivals = game_state.trade.process_arrivals(
                colonies=game_state.colonies if hasattr(game_state, "colonies") else None,
                production=game_state.production if hasattr(game_state, "production") else None,
            )
            report.logistics_arrivals = arrivals
            for arrival in arrivals:
                system_id = arrival.get("to_world")
                if not system_id:
                    continue
                ledger_entry = self._ensure_colony_ledger_entry(report, system_id)
                for resource, amount in (arrival.get("delivered") or {}).items():
                    self._add_resource_delta(ledger_entry["imports"], resource, amount)

    def _process_colony_production(self, game_state, report: TurnReport) -> None:
        """B2: Compute colony production -> add to stockpiles (respect storage caps)."""
        if not hasattr(game_state, "colonies"):
            return

        tech_effects = game_state.tech.get_effects() if hasattr(game_state, "tech") else {}
        industry_bonus = tech_effects.get("industry_bonus", 1.0)
        research_bonus = tech_effects.get("research_bonus", 0)

        for system_id, colony in game_state.colonies.colonies.items():
            rng = None
            if hasattr(game_state, "rng_for_context"):
                rng = game_state.rng_for_context(
                    f"colony_production:{system_id}:{report.turn_number}"
                )
            production = colony.calculate_production(rng=rng)
            ledger_entry = self._ensure_colony_ledger_entry(report, system_id)
            ledger_entry.setdefault("colony_name", colony.name)
            if colony.last_trait_effects:
                ledger_entry["trait_effects"] = dict(colony.last_trait_effects)

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
                    self._add_resource_delta(ledger_entry["production"], resource, added)

    def _process_colony_consumption(self, game_state, report: TurnReport) -> None:
        """B3: Compute colony consumption/upkeep -> subtract from stockpiles."""
        if not hasattr(game_state, "colonies"):
            return

        for system_id, colony in game_state.colonies.colonies.items():
            consumption = colony.calculate_consumption()
            ledger_entry = self._ensure_colony_ledger_entry(report, system_id)
            if hasattr(game_state, "production"):
                maintenance = game_state.production.config.factory_balance.get(
                    "factory_maintenance_per_turn", 0,
                )
                if maintenance:
                    active_factories = sum(
                        1 for f in colony.factories if f.active and not f.building
                    )
                    consumption["credits"] = consumption.get("credits", 0) + active_factories * maintenance
            shortages = {}

            for resource, amount in consumption.items():
                if amount <= 0:
                    continue
                available = colony.stockpiles.get(resource, 0)
                consumed = min(amount, available)
                colony.stockpiles[resource] = available - consumed
                report.resources_spent[resource] = report.resources_spent.get(resource, 0) + consumed
                self._add_resource_delta(ledger_entry["consumption"], resource, consumed)

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
            tech_effects = game_state.tech.get_effects() if hasattr(game_state, "tech") else {}
            shipment_reports = game_state.trade.compute_and_ship(
                colonies=game_state.colonies if hasattr(game_state, "colonies") else None,
                resources=game_state.resources if hasattr(game_state, "resources") else None,
                fleet=game_state.fleet if hasattr(game_state, "fleet") else None,
                production=game_state.production if hasattr(game_state, "production") else None,
                tech_effects=tech_effects,
                galaxy=game_state.galaxy if hasattr(game_state, "galaxy") else None,
            )
            report.logistics_shipments = shipment_reports
            for shipment in shipment_reports:
                shipped = shipment.get("shipped", {}) or {}
                source = shipment.get("source")
                destination = shipment.get("destination")
                for key, amount in shipped.items():
                    if amount <= 0:
                        continue
                    if key.startswith("outbound_") and source:
                        resource = key.split("outbound_", 1)[1]
                        ledger_entry = self._ensure_colony_ledger_entry(report, source)
                        self._add_resource_delta(ledger_entry["exports"], resource, amount)
                    elif key.startswith("inbound_") and destination:
                        resource = key.split("inbound_", 1)[1]
                        ledger_entry = self._ensure_colony_ledger_entry(report, destination)
                        self._add_resource_delta(ledger_entry["exports"], resource, amount)

    def _finalize_colony_ledger(self, game_state, report: TurnReport) -> None:
        if not hasattr(game_state, "colonies"):
            return

        summary_parts = []
        for system_id, colony in game_state.colonies.colonies.items():
            entry = self._ensure_colony_ledger_entry(report, system_id)
            net = {}
            for resource in RESOURCE_TYPES:
                production = entry["production"].get(resource, 0)
                consumption = entry["consumption"].get(resource, 0)
                imports = entry["imports"].get(resource, 0)
                exports = entry["exports"].get(resource, 0)
                net_value = production - consumption - exports + imports
                if net_value != 0:
                    net[resource] = net_value
            entry["net"] = net

            shortages = report.shortage_reports.get(system_id, {}).get("shortages", {})
            bottlenecks = []
            if shortages:
                top_shortages = sorted(
                    shortages.items(),
                    key=lambda item: item[1],
                    reverse=True,
                )[:3]
                for resource, deficit in top_shortages:
                    bottlenecks.append(
                        f"Shortage: {resource.replace('_', ' ').title()} (-{deficit})"
                    )
            entry["bottlenecks"] = bottlenecks

            snapshot = {
                "turn": report.turn_number,
                "date": report.game_date,
                "production": dict(entry["production"]),
                "consumption": dict(entry["consumption"]),
                "imports": dict(entry["imports"]),
                "exports": dict(entry["exports"]),
                "net": dict(entry["net"]),
                "bottlenecks": list(entry["bottlenecks"]),
            }
            colony.resource_ledger.append(snapshot)
            colony.resource_ledger = colony.resource_ledger[-10:]
            colony.last_bottlenecks = list(bottlenecks)

            if net:
                net_parts = []
                for resource, value in list(net.items())[:3]:
                    sign = "+" if value >= 0 else ""
                    net_parts.append(f"{resource}:{sign}{value}")
                if net_parts:
                    summary_parts.append(f"{colony.name} [{', '.join(net_parts)}]")

        report.colony_ledger_entries = {
            sid: dict(entry) for sid, entry in report.colony_ledger_entries.items()
        }
        report.colony_ledger_summary = "; ".join(summary_parts)

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
                tech_effects=tech_effects,
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

    def _process_shipyard(self, game_state, report: TurnReport) -> None:
        """C1b: Process orbital shipyard construction."""
        if not hasattr(game_state, "shipyard"):
            return

        config = None
        if hasattr(game_state, "production"):
            config = game_state.production.config.to_dict()

        shipyard_report = game_state.shipyard.process_tick(
            fleet=game_state.fleet,
            config=config,
        )

        # Create ships from completed orbital builds
        for completed_ship in shipyard_report.get("ships_completed", []):
            blueprint_id = completed_ship.get("blueprint_id", "")
            ship_name = completed_ship.get("ship_name", "New Ship")
            system_id = completed_ship.get("system_id", "")

            if system_id and hasattr(game_state, "fleet"):
                # Use the blueprint_id as ship_class for the fleet manager
                ship = game_state.fleet.create_ship(
                    blueprint_id, system_id, ship_name,
                )
                if ship:
                    report.construction_completed.append(
                        f"Orbital build complete: {ship_name} launched at {system_id}!"
                    )

        report.shipyard_report = shipyard_report

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
                spent = False
                if hasattr(game_state, "colonies"):
                    spent = game_state.resources.spend_from_colonies(
                        "credits",
                        maintenance,
                        game_state.colonies,
                    )
                if not spent:
                    game_state.resources.spend("credits", maintenance)
                report.resources_spent["credits"] = report.resources_spent.get("credits", 0) + maintenance
            else:
                for ship in game_state.fleet.ships.values():
                    ship.morale = max(0, ship.morale - 5)

    def _process_resources(self, game_state, report: TurnReport) -> None:
        if hasattr(game_state, "colonies"):
            game_state.resources.sync_from_colonies(game_state.colonies)
        game_state.resources.update_projections(
            report.resources_gained,
            report.resources_spent,
        )

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

        if hasattr(game_state, "galaxy"):
            for system in game_state.galaxy.systems.values():
                if not system.discovered:
                    continue
                if not system.gate_active or system.gate_status <= 0 or system.gate_capacity <= 0:
                    report.warnings.append(f"Gate at {system.name} is offline")
                elif system.gate_status < 1.0:
                    effective = game_state.galaxy.get_gate_effective_capacity(system.id)
                    percent = int(system.gate_status * 100)
                    report.warnings.append(
                        f"Gate at {system.name} operating at {percent}% capacity ({effective} throughput)"
                    )

        if hasattr(game_state, "trade") and hasattr(game_state, "galaxy"):
            for route in game_state.trade.routes.values():
                if not route.enabled:
                    continue
                capacity = game_state.galaxy.get_path_capacity(
                    route.source_system,
                    route.destination_system,
                )
                if capacity <= 0:
                    report.warnings.append(
                        f"Trade route {route.source_system} → {route.destination_system} disrupted by gate damage"
                    )
                elif capacity < route.capacity_per_turn:
                    report.warnings.append(
                        f"Trade route {route.source_system} → {route.destination_system} limited to {capacity} throughput"
                    )

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
