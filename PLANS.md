# ExecPlans

## PR: Colony ship build queue active/pending progression

### Goal
Separate colony ship build queue ordering from active execution so only intended active builds progress each turn, with explicit queue/concurrency limits and regression coverage.

### Steps
1. Define colony shipyard queue semantics (ordered queue, active concurrency, optional max queue cap) and expose summary status for active vs pending entries.
2. Refactor `can_build_ship`, `start_ship_build`, and `process_turn` to enforce queue/concurrency rules and prevent unintended progress for pending orders.
3. Add regression tests for multi-queue same-turn behavior, 2–3 turn progression, and completion order/count per turn.
4. Verify/cover queue summary status reporting so UI consumers can distinguish active and pending orders.

## PR: Body-level intra-system ship movement

### Goal
Track ship anchors/transit at celestial body granularity, process local movement on non-turn ticks, persist the new movement state, and render ship placement from body/transit status in the gravity well map.

### Steps
1. Extend ship state + serialization with body anchor and local transit progress fields.
2. Refactor local movement execution to validate body targets and start tick-based local transit instead of same-system no-op moves.
3. Add local movement tick processing tied to the game clock and wire it into game flow.
4. Update gravity well ship placement to derive icon positions from body anchors and in-progress local transit.
5. Add regression tests for local body-to-body movement, persistence, and non-turn tick progression.

## PR: AU-based system map orbit geometry

### Goal
Carry semi-major axis distances from known/procedural system data into runtime planet objects and use AU-aware orbit layout in the gravity well map with configurable compression.

### Steps
1. Extend astronomy body schema and procedural generation to emit `semi_major_axis_au` for planets and moons.
2. Ensure galaxy/runtime planet parsing/serialization retains the AU field and treats `orbit_index` as fallback ordering metadata.
3. Replace index-only UI orbit spacing with AU-to-screen transform helpers (configurable compression + minimum visual separation) and add focused regression tests.

## PR: Prevent diplomacy actions before unlock_diplomacy

### Goal
Block diplomacy branches/actions until the unlock_diplomacy tech is researched, add UI lock messaging, and cover with tests.

### Steps
1. Gate diplomacy branches and relation actions on unlock_diplomacy in game state logic.
2. Show a diplomacy lock state in the relations screen and hide diplomacy buttons until unlocked.
3. Add regression coverage for locked relations UI and encounter branch omission.

## PR: Persist combat/diplomacy resource deltas across colony sync

### Goal
Ensure resource gains/spends from combat/diplomacy persist through colony resource sync by applying deltas to colony stockpiles and adding regression coverage.

### Steps
1. Add colony-aware resource delta helpers in `GameState` and route combat/diplomacy rewards through them.
2. Ensure resource delta application updates colony stockpiles before `ResourceManager.sync_from_colonies` runs.
3. Add/strengthen a regression test that grants combat loot, processes a turn, and asserts resources persist in both global totals and colony stockpiles.

## PR: Pause trade routes halts shipments

### Goal
Ensure trade route pause/resume in the UI maps to the execution flag and that turn processing skips paused routes, with a regression test.

### Steps
1. Align trade route toggle and trade execution to the same enabled flag while preserving legacy active state on load.
2. Add a turn-processing test that pauses a route and asserts no shipments are created.

## PR: Trade route pause toggle uses enabled flag

### Goal
Ensure the trade route pause/resume toggle flips the execution flag and turn processing skips paused routes, with a regression test.

### Steps
1. Update the trade route toggle UI to flip the enabled flag used by execution and keep legacy active in sync.
2. Confirm `compute_and_ship` respects the enabled flag (sync legacy state if needed).
3. Add a test that pauses a route, runs a turn, and asserts no shipments are created.

## PR: Gate diplomacy actions behind Signal Decryption

### Goal
Prevent diplomacy actions and encounter branches until the unlock_diplomacy tech is researched, with UI lock messaging and tests.

### Steps
1. Add explicit tech gating in encounter branch selection and relation action resolution paths.
2. Surface a lock message in the relations screen and hide/disable diplomacy actions until unlocked.
3. Add regression tests for locked diplomacy UI state and encounter branch omission when tech is unresearched.

## PR: Deduplicate POP transfer adjustments

### Goal
Ensure POP transfers update colony populations exactly once across ship actions, logistics, and trade, with regression coverage.

### Steps
1. Keep ship POP load/unload paths using immediate transfer without pending migration bookkeeping.
2. Ensure trade/logistics POP transfers only apply once and do not duplicate migration with colony turn processing.
3. Add a regression test that advances a turn and asserts POP export/import changes match the transfer amount.

## PR: Fix audited gameplay/blocker issues (A-F)

### Goal
Implement fixes for the audited playability/shipping issues across population, resources, encounters, trade, diplomacy, missions, and UI feedback.

### Steps
1. Fix POP export double-decrement by unifying migration bookkeeping across trade/logistics and ship actions; add safeguards in colony processing.
2. Preserve resource deltas by syncing combat/diplomacy/event rewards into colony stockpiles before global sync; add affordability checks for manual result imports.
3. Align trade route toggles with runtime checks, prevent export overwrites, and improve manual encounter import/export handling.
4. Gate diplomacy features behind tech unlocks and refine encounter branching + UI feedback.
5. Address remaining UX dead-ends (missions discovery counting, mining feedback, gate activation messaging, local move UI entry, retreat penalties).

## Bug triage and fixes from codebase review

### Goal
Resolve critical bugs, balance issues, illogical mechanics, and UI dead-ends identified in the code review.

### Steps
1. Fix global resource loss when unloading cargo by preventing `sync_from_colonies` from wiping non-colony resources and add regression coverage.
2. Consume colony ships on successful colony founding and add turn-report/log messaging to reflect the ship loss.
3. Implement handlers for “Emergency Stop” and “Return Home,” or remove them from contextual actions when unsupported; ensure the UI provides feedback for “Continue Mining.”
4. Align freight route cancellation with ship state (clear `mission`/assignment) and validate freight mission cleanup.
5. Add a UI entry point for manual encounter result import/export to make manual resolution reachable.
6. Rebalance mining or add operating costs/fuel usage so miners do not generate free resources indefinitely.

## Encounter export uses pending entries

### Goal
Ensure encounter spec exports use existing pending encounter data without creating duplicates.

### Steps
1. Add a GameState helper to export a pending encounter by encounter_id without appending new pending entries.
2. Update the encounter screen export button to call the new helper with the pending encounter id.
3. Verify the export path/filename remains `exports/encounters/EncounterSpec.json` and no duplicate pending entries are created.

## Colony stockpile cargo unload alignment

### Goal
Ensure ship cargo unloads (mining, UI actions) deposit into colony stockpiles with storage caps and keep UI behavior consistent.

### Steps
1. Update mining and GameState unload logic to add cargo to colony stockpiles with caps.
2. Route fleet screen and galaxy map unload/deliver actions through the updated GameState helper.
3. Validate global resource syncing still reflects colony stockpiles after unloads.

## Freighter class checks across fleet, trade, and actions

### Goal
Treat all freighter variants consistently for cargo actions, trade route assignment, and fleet styling.

### Steps
1. Update FleetManager contextual actions to detect freighter variants for load/unload actions.
2. Align trade route freighter selection with logistics screen filtering rules.
3. Adjust fleet screen class color mapping for freighter variants.

## Persisted spend operations across turn resource sync

### Goal
Ensure resource spending for maintenance and shipyard actions is reflected in colony stockpiles so turn sync does not overwrite costs.

### Steps
1. Add resource spending helpers that deduct from colony stockpiles while keeping global/per-system totals consistent.
2. Update maintenance and shipyard/orbital build call sites to use colony-aware spending.
3. Align shipyard UI affordance checks with colony stockpiles and adjust tests accordingly.

## Preserve non-colony resource deltas across sync

### Goal
Ensure combat loot and diplomacy rewards persist by syncing resource deltas into colony stockpiles (or global buffer) before colony-based resource sync, with coverage.

### Steps
1. Add colony-aware resource delta helpers in game state and use them for spend/add rewards.
2. Update combat/diplomacy reward paths to use the colony-aware helpers.
3. Add regression test: grant combat loot, process turn, and assert resources persist.

## Escort target selection flow

### Goal
Add an escort target selection popup to the ship context menu and validate escort targets in game state handling.

### Steps
1. Build the escort target selection popup in the galaxy map ship context menu and pass target ship IDs with the escort order.
2. Validate escort targets in the game state handler (existence, not self, same system) and surface failures to the UI.

## Logistics route editor expansion

### Goal
Expand the logistics route UI to support multiple waypoints, multi-rule cargo handling per waypoint, and optional wait turns.

### Steps
1. Redesign the freight route creation popup to manage a list of waypoints with editable cargo rules, thresholds, and wait turns.
2. Validate multi-waypoint inputs in the UI and create routes with the configured waypoints and rules.
3. Update route detail rendering to show wait turns and cargo rule thresholds per waypoint.

## Galaxy map action handling and menu alignment

### Goal
Ensure ship context menus only show actions with UI/state handlers and add notices for unimplemented actions.

### Steps
1. Add handler checks in FleetManager contextual actions and remove unsupported action entries.
2. Add missing action dispatch/notice logic in the galaxy map action executor.
3. Expose a ship action handler availability helper in game state for UI gating.

## Colony trait effects in production and stability

### Goal
Apply world trait modifiers for exotics production and stability adjustments during turn processing and reporting.

### Steps
1. Add trait-aware stability adjustments in colonies with persisted offsets and report hooks.
2. Add exotics chance/bonus handling in colony production using deterministic RNG per turn.
3. Surface trait-driven production/stability updates in turn reports where applicable.

## Encounter resolution branching + UI toggle

### Goal
Add encounter resolution branching in `resolve_encounter` and expose an in-game UI control to switch modes.

### Steps
1. Update encounter resolution flow to branch on auto/manual/tactical and apply results/export specs as required.
2. Add an in-game settings control that calls `set_encounter_resolution_mode`.
3. Verify encounter logging/reporting is preserved for each resolution path.

## Return Home nearest reachable colony

### Goal
Update the Return Home ship action to target the nearest reachable colony by gate path length and provide feedback when no colony is reachable, keeping the UI action text aligned.

### Steps
1. Update Return Home action handling to select the shortest reachable colony path.
2. Add feedback (log entry) when no reachable colony exists.
3. Align the Return Home action description with the new behavior.

## Population resource + realistic system generation

### Recon summary (current structure)
- Colony stats/live state: `gate_horizons/game/colonies.py` (Colony + ColonyManager, per-turn growth in `Colony.process_turn()`).
- Resources/stockpiles/trade: `gate_horizons/game/resources.py` (global/per-system), `gate_horizons/game/trade.py` (abstract routes/shipments), `gate_horizons/game/logistics.py` (freighter routes).
- Galaxy/system/world data: `gate_horizons/game/galaxy.py` (Planet/StarSystem/GalaxyMap), demo data in `gate_horizons/data/galaxy_templates/demo_galaxy.json`.
- Save/load schema + migrations: `gate_horizons/game/state.py` (`CURRENT_SCHEMA_VERSION`, `from_dict` migrations), SQLite wrapper in `gate_horizons/game/save_load.py` (no schema_version column yet).

### Goal
Add population-as-a-resource mechanics + deterministic, realistic system generation (with hardcoded Sol) while keeping save compatibility, offline-only constraints, and UI integration.

### Steps
1. **Population system core**: add population attributes, policy knobs, and deterministic per-turn dynamics; integrate POP transfers through trade/logistics and colony founding requirements.
2. **System generation**: introduce `astro/` known-system registry + procedural generator; add Sol data JSON and wire to galaxy generation and demo galaxy data.
3. **Persistence + migrations**: add SQLite schema_versioning + migrate existing saves; bump game schema version and backfill new colony fields.
4. **UI + tests + docs**: expose population metrics and POP trade in Kivy UI, add deterministic tests (population, migration, Sol fixture, generator rules), and update README/DESIGN_SUMMARY/PROJECT_PLAN with tuning knobs.

### Risks
- **Save compatibility**: new fields in colonies + SQLite versioning could break older saves.
- **Balance sensitivity**: population dynamics can destabilize if constants are off.
- **Generator regressions**: galaxy/system generation changes may break existing assumptions/tests.
- **UI clutter**: additional population/pollution/education data could reduce readability.

## Colonization starter cargo gating + UI clarity

### Goal
Make colonization actionable by surfacing the starter cargo requirement in the UI
and preventing colony orders when the colony ship lacks required cargo.

### Steps
1. Add preflight validation for "Establish Colony" orders to block queueing when
   starter cargo is missing.
2. Surface starter cargo requirements and missing amounts in the system view
   colonization button/confirmation flow.
3. Add tests covering order validation and UI messaging.

### Acceptance
- "Establish Colony" orders fail fast if the colony ship lacks starter cargo.
- System view colonization UI displays starter cargo requirements and disables the
  action when cargo is missing.
- Tests cover both order validation and UI copy presence.

## Colony starter cargo requirement

### Goal
Require colony ships to carry a starter cargo kit before founding a colony, consume that cargo on establishment, and log/report the usage.

### Steps
1. Define the starter cargo requirement alongside colony founding costs.
2. Validate colony ship cargo and deduct the starter kit during colony establishment.
3. Record the starter cargo consumption in colony founding logs/ship action summaries.

### Acceptance
- Founding fails if the colony ship lacks the starter cargo requirement.
- Required cargo is removed from the colony ship when the outpost is created.
- Colony founding logs mention the starter cargo usage.

## Refuel uses fuel resource

### Goal
Switch refueling costs to use the fuel production resource, sourcing it from colony production inventory and supporting trade shipments.

### Steps
1. Update refuel action costs and state handling to spend fuel from colony production inventory.
2. Extend trade route handling to move fuel via production inventories and update UI manifests to include fuel.
3. Adjust refuel-related UI text/cost displays to show fuel usage.

### Acceptance
- Refueling consumes fuel from the hosting colony’s production inventory.
- Trade routes can ship fuel to colonies and the trade UI supports fuel in manifests.
- Refuel actions display fuel costs in the action menu and summary output.

## Colony ship requirement for founding outposts

### Goal
Require an in-system ship with the `establish_colony` ability to found colonies, expose an explicit ship action, and consume the colony ship on success with player-visible logging.

### Steps
1. Update colony validation to require a qualifying ship and optional resource checks.
2. Add colony ship action in ship context menus and dispatch handling in game state.
3. Consume the colony ship on successful founding and log the tradeoff.
4. Update UI/system checks and tests to account for the ship requirement.

### Acceptance
- Founding fails without a colony-capable ship in the target system.
- “Establish Colony” appears for colony ships and routes through the ship action dispatch.
- On success, the colony ship is removed and the log/turn report reflects the tradeoff.

## STAB-01 + NEXT3: Regression hardening and next roadmap triad

### Regression risk list (top 10)
1. Gravity well map navigation fails to return to galaxy map or loses breadcrumb state.
2. Intra-system movement incorrectly advances the turn or bypasses travel validation.
3. Encounter pipeline writes malformed ResultSpec payloads and fails to apply consequences.
4. Tactical combat returns inconsistent victory/defeat results or leaves encounters pending.
5. Diplomacy actions apply relation deltas but do not persist across save/load.
6. Ship order execution fails for refuel/repair when colony or spaceport is missing.
7. Turn processor skips ship orders or applies them twice on multi-turn loops.
8. Save/load regression drops missions, diplomacy, or pending encounter state.
9. Trade routes ignore gate capacity or negative gate status, causing invalid shipments.
10. Event engine re-triggers one-time events after being queued.

### Bugfix checklist + acceptance tests
- Validate encounter branch outputs and ResultSpec application.
  - Acceptance: `pytest gate_horizons/tests/test_encounter_contract.py gate_horizons/tests/test_encounter_branching.py`
- Validate intra-system movement does not advance turns or skip travel rules.
  - Acceptance: `pytest gate_horizons/tests/test_intra_system_movement.py`
- Confirm ship order execution and refuel/repair handlers are deterministic and validated.
  - Acceptance: `pytest gate_horizons/tests/test_ship_construction.py gate_horizons/tests/test_audit_fixes.py`
- Save/load round-trip preserves diplomacy, missions, encounters, and logistics.
  - Acceptance: `pytest gate_horizons/tests/test_save_load_roundtrip.py gate_horizons/tests/test_save_load_sqlite.py`
- UI encounter loop smoke (encounter -> branch -> return -> save/load) via manual Kivy run.
  - Acceptance: manual smoke test steps in release notes.

### Next 3 selection rule
- Source docs: `README.md`, `PROJECT_PLAN.md`, `DESIGN_SUMMARY.md`, `docs/FEATURE_STATUS.md`, `docs/ROADMAP.md`.
- Select highest-priority items that are planned and not shipped, with minimal dependencies.
- Confirm each item is explicitly listed as planned in docs and not marked Shipped.

### NEXT3 (priority + rationale)
1. **Resource flow visualisation** — P1 in `docs/ROADMAP.md`; uses existing trade/logistics data without a new data model, so it meets the minimal-dependency rule. References: `docs/ROADMAP.md`, `docs/FEATURE_STATUS.md`, `PROJECT_PLAN.md`.
2. **Planet comparison view** — P2 in `docs/ROADMAP.md`; UI-only comparison using existing planet metadata, low dependency. References: `docs/ROADMAP.md`, `docs/FEATURE_STATUS.md`, `PROJECT_PLAN.md`.
3. **Fog of war visualization on system map** — P2 in `docs/ROADMAP.md`; scoped to visual treatment and survey flags already present in system data. References: `docs/ROADMAP.md`, `docs/FEATURE_STATUS.md`, `PROJECT_PLAN.md`.

**Deferrals:** Fleet group management remains pending because it requires a new data model for fleet grouping and command batching, which violates the minimal-dependency rule for this NEXT3 batch. References: `docs/ROADMAP.md`.

### Milestones and file lists

#### Milestone 0 — STAB-01 Regression hardening
- Focus: fix regressions after most recent merge; add tests as needed.
- Target files (as needed):
  - `gate_horizons/game/state.py`
  - `gate_horizons/game/turn.py`
  - `gate_horizons/ui/screens/encounter_screen.py`
  - `gate_horizons/ui/screens/tactical_screen.py`
  - `gate_horizons/tests/*`
  - Docs: `README.md`, `docs/FEATURE_STATUS.md`, `docs/CHANGELOG.md`

#### Milestone 1 — Resource flow visualisation (NEXT3 1/3)
- Show trade/logistics flows as line overlays between colonies on the galaxy map.
- Acceptance criteria:
  - Trade routes render directionally with per-resource color or legend key.
  - Lines reflect active routes only and update after turn processing.
  - Overlay can be toggled on/off without affecting turn flow.
  - Tests cover overlay data mapping from trade routes.
- Docs: `README.md`, `PROJECT_PLAN.md`, `docs/FEATURE_STATUS.md`, `docs/CHANGELOG.md`, `docs/ROADMAP.md`.

#### Milestone 2 — Planet comparison view (NEXT3 2/3)
- Add a comparison panel for 2–3 selected planets with key stats.
- Acceptance criteria:
  - Player can select up to 3 planets/bodies and open a comparison view.
  - Comparison shows resources, habitability, gravity, and traits.
  - View exits back to the previous map without losing selection state.
  - Tests validate comparison data extraction for multiple bodies.
- Docs: `README.md`, `PROJECT_PLAN.md`, `docs/FEATURE_STATUS.md`, `docs/CHANGELOG.md`, `docs/ROADMAP.md`.

#### Milestone 3 — Fog of war visualization on system map (NEXT3 3/3)
- Show unsurveyed bodies as silhouettes with hidden details until surveyed.
- Acceptance criteria:
  - Unsurveyed bodies display with placeholder visuals and redacted labels.
  - Surveyed bodies display full details and normal visuals.
  - Toggle respects save/load and does not alter game state.
  - Tests cover survey flag mapping to render state.
- Docs: `README.md`, `PROJECT_PLAN.md`, `docs/FEATURE_STATUS.md`, `docs/CHANGELOG.md`, `docs/ROADMAP.md`.

### Out of scope
- Android build + Buildozer packaging.
- Real-time tactical runtime integration.
- New gameplay systems beyond the NEXT3 list.
- Economy overhaul, piracy systems, or procedural narrative generation.

### Rollback plan
- Each milestone is an isolated commit for targeted revert.
- If stability regresses, revert Milestone 1–3 commits independently; keep STAB-01 fixes.

## PHASE1-TACTICAL-TRIAD: Hex combat + Diplomacy + Encounter Branching

### Acceptance criteria
**Feature 1 — Tactical Encounters (Hex Combat MVP)**
- Launch tactical encounter from an in-game encounter event via “Start Tactical”.
- Fixed-size hex grid with at least 2 terrain types and movement/accuracy modifiers.
- Player ship + at least 1 enemy ship, each with HP, movement points, basic weapon, wait/end turn.
- Deterministic, turn-based loop with victory/defeat result object.
- Tactical screen with grid view, selected unit info, action buttons, end turn.
- Result payload includes winner, damage, losses, salvage (optional), and summary message.
- Tests: grid movement constraints, deterministic attack resolution, win/lose termination payload.

**Feature 2 — Diplomacy Foundation (Relations + Outcomes)**
- Diplomacy model with relation score/tier for factions.
- At least 2 actions that change relations; outcomes applied deterministically.
- Diplomacy options available in encounter resolution; relation display UI exists.
- Relations persist across save/load.
- Tests: relation score changes, persistence round-trip, diplomacy modifies encounter options.

**Feature 3 — Encounter Branching + Contract Hook**
- Unified encounter pipeline with Tactical/Diplomacy/Evasion branches.
- EncounterSpec/ResultSpec schema consistently used (or documented if updated).
- Consequences applied to game state: ship damage/loss, resources, relations.
- Tests: EncounterSpec serializes/validates, ResultSpec applies changes, branch routing.

### File list (expected touchpoints)
- `gate_horizons/game/combat.py`
- `gate_horizons/game/state.py`
- `gate_horizons/game/turn.py`
- `gate_horizons/game/diplomacy.py` (new)
- `gate_horizons/game/tactical.py` (new)
- `gate_horizons/ui/screens/tactical_screen.py` (new)
- `gate_horizons/ui/screens/encounter_screen.py` (new)
- `gate_horizons/ui/widgets/notification.py`
- `gate_horizons/ui/screens/galaxy_map.py`
- `gate_horizons/main.py`
- Tests: `gate_horizons/tests/test_tactical_combat.py` (new), `gate_horizons/tests/test_diplomacy.py` (new), `gate_horizons/tests/test_encounter_branching.py` (new)
- Docs: `README.md`, `PROJECT_PLAN.md`, `DESIGN_SUMMARY.md`, `docs/ENCOUNTER_CONTRACT.md`, `docs/FEATURE_STATUS.md`, `docs/CHANGELOG.md` (new)

### Test plan per feature
- Feature 1: `python -m unittest gate_horizons.tests.test_tactical_combat -v`
- Feature 2: `python -m unittest gate_horizons.tests.test_diplomacy -v`
- Feature 3: `python -m unittest gate_horizons.tests.test_encounter_branching -v`
- Final: `python -m unittest discover -s gate_horizons/tests -v`

### UI touchpoints per feature
- Feature 1: Tactical screen + “Start Tactical” from encounter resolution.
- Feature 2: Encounter resolution options + relations display screen/panel.
- Feature 3: Encounter branching screen/popup + results summary.

### Doc update checklist per feature
- Update README “Implemented vs Future”.
- Update `docs/FEATURE_STATUS.md` with shipped status + file references.
- Sync `PROJECT_PLAN.md` + `DESIGN_SUMMARY.md` to match implemented scope.
- Add CHANGELOG entry after each feature.

### Out of scope
- Procedural galaxy generation, piracy economy, large tech tree expansion.
- Real-time tactical sim loops or non-deterministic combat.
- New giant gameplay systems beyond encounter branching + diplomacy + tactical MVP.

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

## ExecPlan — Centralized ship context action dispatcher (2026-02-10)

### Goal
Centralize gameplay execution for ship context actions behind a public API on `GameState`, then have all UI screen entrypoints call that API while retaining per-screen menu/popup/refresh behavior.

### Steps
1. Add a `GameState` dispatcher method for ship context actions with structured outcomes (executed vs UI follow-up needed).
2. Migrate `galaxy_map.py`, `fleet_screen.py`, and `gravity_well_map.py` to use the dispatcher and keep local UI concerns local.
3. Add parity tests that run the same action via each screen entrypoint and assert identical resulting game-state effects.
4. Run focused pytest coverage for the new parity tests.

### Validation
- New tests verify the same action (`Emergency Jettison`) has identical cargo outcomes through Galaxy, Fleet, and Gravity Well screen entrypoints.

## PR: Explicit numeric validation feedback for trade/logistics route editors

### Goal
Replace silent numeric coercion in trade/logistics route creation popups with explicit user-facing validation errors, and add regression coverage for invalid manifest paths.

### Steps
1. Add manifest parsing validation in `CreateRoutePopup._on_create` that collects invalid resource fields, shows a clear expected-format message, and blocks route creation.
2. Add explicit status feedback for invalid logistics numeric entries (wait turns and cargo rule integer fields) instead of silently coercing invalid values to zero.
3. Add tests covering invalid manifest input handling and logistics numeric validation behavior.

## PR: Fleet mining/trade quick actions use GameState commands

### Goal
Route Fleet screen mining toggle and trade unassign quick actions through explicit `GameState` commands so invariants, logging, and turn-report entries match centralized action dispatch behavior.

### Steps
1. Add `GameState` command methods for toggling mining and unassigning a ship from trade routes, including invariant cleanup and action logging/report entries.
2. Update Fleet screen handlers to call those methods and show notice feedback when a command fails.
3. Add parity tests that compare Fleet quick-action entrypoints against Galaxy action dispatch for equivalent state transitions.

## PR: Hierarchical system-map body rendering and declutter

### Goal
Render system bodies with explicit planet→moon hierarchy, draw moons as local sub-orbits, add zoom/collision decluttering while preserving accurate tap hitboxes, and cover with targeted UI tests.

### Steps
1. Add render-prep helpers in `SystemMapWidget` that split star orbiters vs moons and attach moons to parent planets via `body_type`/`orbit_index` rules.
2. Refactor `SystemMapWidget._redraw` to render parent planets on star orbits and moons on local parent-centric sub-orbits, while tracking hitboxes for all rendered bodies.
3. Add declutter helpers for zoom-level detail and collision-aware icon/label suppression without breaking interaction selection.
4. Add focused tests for hierarchy mapping assumptions and declutter-safe tap hitbox behavior.

## PR: Fleet-group release-readiness foundation

### Goal
Add a default-off runtime feature flag surface for fleet groups, a typed telemetry adapter with roadmap-stable event schemas, safe no-op command behavior when disabled, release-check documentation, and regression tests for the flag/telemetry contract.

### Steps
1. Extend settings/config to include a runtime-loadable `enable_fleet_groups` flag and wire app startup initialization for global query access in UI/gameplay paths.
2. Add centralized telemetry event definitions and a typed adapter that validates required payload keys before dispatch.
3. Introduce fleet-group foundation command helpers that gate create/dispatch via the feature flag and fail safely when disabled.
4. Document local release checks for schema compatibility, flag-off behavior, and telemetry payload validation under `docs/`.
5. Add tests proving default-off behavior, fleet-group UI/action suppression when off, and required telemetry keys for emitted roadmap events.


## PR: Centralize UI strategic movement through GameState submission API

### Goal
Route ship strategic movement initiated from Fleet, Galaxy Map, and Gravity Well screens through one validated `GameState` API so preconditions, logs/action hooks, and failure semantics stay consistent.

### Steps
1. Add/confirm a `GameState` strategic movement submission method that validates ship/destination/path state, blocks local-transit conflicts, and records movement action hooks/messages.
2. Refactor UI movement callbacks in `fleet_screen.py`, `galaxy_map.py`, and `gravity_well_map.py` to call the centralized API and surface result messaging while preserving refresh behavior.
3. Update parity/regression tests to ensure UI movement entrypoints go through `GameState` movement submission and that invalid transitions (e.g., active local transit) fail consistently.
4. Run focused pytest coverage for updated movement dispatch tests.

## PR: Targeted gameplay/UI parity fixes for transfer actions and system-view gating

### Goal
Fix three parity bugs by making ship cargo/colonist context actions report truthful transfer outcomes, aligning gate-activation affordability checks with tech-discounted effective cost, and ensuring ship-build UI affordance/failure feedback matches colony buildability constraints.

### Steps
1. Update `GameState.dispatch_ship_context_action` transfer branches to derive success/no-op messages from actual transfer results and local preconditions.
2. Refine `SystemViewScreen` gate activation affordability/cost state to use the same discounted effective cost path as `GameState.activate_gate()`.
3. Ensure system-view ship build buttons require both affordability and colony buildability and display a notice when `_on_build_ship` fails.
4. Add/adjust focused tests for each fix and run targeted pytest coverage.

## PR: Parameterized transfer manifests across ship action entrypoints

### Goal
Allow partial cargo/colonist load/unload through parameterized manifests in ship context actions, surface those options consistently in System View/Fleet/Gravity Well UI entrypoints, and add parity tests that verify identical transfer outcomes/messages.

### Steps
1. Extend `GameState` transfer helpers/dispatcher to accept validated per-resource manifests and colonist amounts for both load and unload actions.
2. Add shared transfer-parameter popup helpers and wire Fleet, Gravity Well, and System View ship action handlers to pass parameterized manifests into dispatch.
3. Add/expand parity tests to assert message/state equivalence for transfer actions (default and parameterized) across all ship-action entrypoints.
4. Run focused pytest coverage for ship action dispatch and transfer regressions.
