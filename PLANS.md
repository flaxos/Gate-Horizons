# ExecPlans

## FREIGHT-01: Freight automation + throughput UI + EncounterSpec handshake

### Current-state analysis
- **Abstract trade routes & latency shipments**: `gate_horizons/game/trade.py` defines `TradeRoute`, `TradeManager`, and `Shipment` with per-turn `compute_and_ship()` and `process_arrivals()` using in-transit queues.
- **Physical freighter routes**: `gate_horizons/game/logistics.py` defines `FreighterRoute` + `LogisticsManager` with waypoint-based load/unload rules, executed in `TurnProcessor._process_freighter_routes()` (`gate_horizons/game/turn.py`).
- **Route creation & UI**:
  - Abstract trade routes UI in `gate_horizons/ui/screens/trade_screen.py` with manifest-based per-turn transfers.
  - Physical freighter UI in `gate_horizons/ui/screens/logistics_screen.py` with cargo rules per waypoint.
- **Colony stockpiles & production/consumption**: `gate_horizons/game/colonies.py` stores `stockpiles`, `calculate_production()`, `calculate_consumption()`; turn order in `gate_horizons/game/turn.py` handles production/consumption and logistics shipments.
- **Freighters & fleet**: `gate_horizons/game/ships.py` defines ship stats (cargo/freight capacity) and mission assignments; trade routes can attach freighters for capacity.
- **Encounter specs**: `gate_horizons/game/combat.py` defines `EncounterSpec` and `ResultSpec` with basic fields; `gate_horizons/game/state.py` tracks `pending_encounters` and manual resolution.

### Definitions (Automated freight for Gate Horizons)
- **Automated freight** = when a trade route uses a simple policy to choose shipment manifests each turn based on destination deficits and route allowlist/limits, without manual per-turn resource entry.
- Policy stays **deterministic** and **turn-based**: no real-time loops, no continuous agent micromanagement.
- Manual overrides remain: existing cargo transfer actions and explicit manifest entries on trade routes still take precedence.

### Data model changes
- `TradeRoute` additions:
  - `auto_policy`: string (e.g., `"manual" | "auto_deficit"`).
  - `auto_allowlist`: list of resource ids eligible for automation.
  - `auto_max_per_resource`: dict of per-resource max per turn.
- `Colony` additions:
  - `resource_ledger`: list of recent per-turn deltas (production, consumption, imports, exports, net).
  - `last_bottlenecks`: cached list of top bottleneck messages for UI.
- `TurnReport` additions:
  - `colony_ledger_entries`: per-turn ledger snapshots used for logging/UI updates.
- **Event log**: append a concise per-turn logistics/ledger summary to `game_state.log`.

### Milestones

#### Milestone 1 — Automate freight (minimum viable autop-run)
**Acceptance criteria**
- Route creation remains unchanged; each trade route has explicit source/destination.
- End-of-turn automation computes shipments based on destination deficits + route config.
- Shipments respect: source stockpiles, destination storage caps, route/freighter capacity, latency.
- Manual transfers remain available (existing UI and freighter rules unaffected).
- Tests cover: stockpile -> in-transit -> arrival; no shipment when no supply or when destination full.

**Files**
- `gate_horizons/game/trade.py` (automation policy + shipment allocation)
- `gate_horizons/game/state.py` (route creation defaults / settings)
- `gate_horizons/ui/screens/trade_screen.py` (toggle/summary for auto routes)
- `gate_horizons/tests/test_trade_automation.py` (new tests)
- Docs: `DESIGN_SUMMARY.md`, `PROJECT_PLAN.md`

**Test plan**
- `python -m pytest gate_horizons/tests/test_trade_automation.py`
- Full suite at the end: `python -m pytest`

#### Milestone 2 — Throughput visibility (route + colony deltas)
**Acceptance criteria**
- Trade route UI shows capacity, latency/ETA, current cargo, next arrival, queue length.
- Colony UI shows per-resource net delta per turn and top 1–3 bottlenecks.
- Per-turn ledger/event log entry recorded.
- Tests validate net delta math for balanced vs shortage cases.

**Files**
- `gate_horizons/game/turn.py` (ledger snapshot + log entries)
- `gate_horizons/game/colonies.py` (ledger fields)
- `gate_horizons/ui/screens/trade_screen.py` (route throughput/ETA)
- `gate_horizons/ui/screens/colony_screen.py` (net delta + bottlenecks)
- `gate_horizons/tests/test_colony_ledger.py` (new tests)
- Docs: `DESIGN_SUMMARY.md`, `PROJECT_PLAN.md`

**Test plan**
- `python -m pytest gate_horizons/tests/test_colony_ledger.py`

#### Milestone 3 — EncounterSpec handshake (export/import contract plumbing)
**Acceptance criteria**
- Debug/CLI action can export `EncounterSpec.json` to `exports/encounters/`.
- Importer reads `ResultSpec.json` from `imports/results/` and applies consequences.
- Consequences include ship damage/loss, resource changes, colony stability adjustments, intel.
- Schema matches `docs/ENCOUNTER_CONTRACT.md` (or updated if needed).
- Tests for EncounterSpec serialization and ResultSpec import effects.

**Files**
- `gate_horizons/game/state.py` (export/import + apply consequences)
- `gate_horizons/game/combat.py` (schema alignment)
- `gate_horizons/ui/screens/*` or CLI hook (expose export action)
- `gate_horizons/tests/test_encounter_contract.py` (new tests)
- Docs: `docs/ENCOUNTER_CONTRACT.md`, `DESIGN_SUMMARY.md`, `PROJECT_PLAN.md`

**Test plan**
- `python -m pytest gate_horizons/tests/test_encounter_contract.py`

### Risks & rollback plan
- **Risk**: Automation shipping wrong resources/overfilling. **Mitigation**: enforce destination storage caps and per-resource max.
- **Risk**: UI clutter on mobile. **Mitigation**: compact labels, keep details in scrollable areas.
- **Risk**: EncounterSpec mismatch with docs. **Mitigation**: align schema and document any adjustments.
- **Rollback**: revert per milestone commits independently; keep data model defaults backward-compatible.

### Out of scope
- Piracy/diplomacy systems beyond minimal encounter consequences.
- Procedural galaxy generation or large-scale economy rework.
- Real-time automation loops or factorio-style belts.
