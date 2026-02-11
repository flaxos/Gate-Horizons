# Release Plan: Fleet Group Management

## Purpose and Scope
Fleet Group Management introduces reusable multi-ship groups that can receive shared orders while preserving the existing single-ship order flow.

This plan tracks delivery in five phases:
1. Data model
2. Command API
3. UI controls
4. Save migration
5. Balancing

The roadmap entry for this feature is tracked in `docs/ROADMAP.md`, and implementation status is tracked in `docs/FEATURE_STATUS.md`.

## Non-Negotiable Quality Gates

### Single-Ship Parity Testing (Required in Every Phase)
- Existing single-ship order behavior must remain unchanged for:
  - move
  - patrol
  - refuel
  - repair
- Add/maintain regression coverage proving that single-ship commands still:
  - validate under the same rules,
  - produce equivalent turn outcomes,
  - emit equivalent logs/telemetry semantics for non-group actions.
- No phase exits without parity sign-off against current single-ship order tests.

### Telemetry Baseline (Required in Every Phase)
At minimum, the following telemetry events must exist with stable names and required fields:
- `fleet_group_created`
  - Required fields: `group_id`, `ship_count`, `system_id`, `turn_index`
- `fleet_group_order_issued`
  - Required fields: `group_id`, `order_type`, `target_id`, `ship_count`, `turn_index`
- `fleet_group_order_result`
  - Required fields: `group_id`, `order_type`, `result` (`success`/`failure`), `reason` (nullable), `turn_index`

### Rollback Strategy Baseline (Required in Every Phase)
- All fleet-group behavior must be guarded by a runtime feature switch, e.g. `enable_fleet_groups`.
- Rollback operation must support:
  - disabling new group creation,
  - reverting command dispatch to single-ship pathways,
  - loading existing saves safely without hard failure.
- Rollback must not require save deletion.

---

## Phase 1 — Data Model

### Scope
- Add canonical group entities and membership references.
- Define ownership and lifecycle rules (create, update membership, disband).

### Entry Criteria
- Data shape for groups is reviewed and agreed.
- Group ID format and uniqueness constraints are defined.
- Feature switch scaffold (`enable_fleet_groups`) is available.

### Exit Criteria
- Group and membership fields exist in runtime state with unit tests.
- Membership invariants are enforced (no duplicate membership; no cross-faction membership).
- Telemetry `fleet_group_created` fires on successful create.
- Rollback behavior verified: with switch off, group-aware model reads but group creation is blocked.

### Telemetry Requirements
- `fleet_group_created`
- `fleet_group_order_issued` (stub instrumentation allowed if command layer not complete)
- `fleet_group_order_result` (stub instrumentation allowed if command layer not complete)

### Rollback Switch Strategy
- Keep `enable_fleet_groups` default off in this phase.
- When off:
  - ignore group command surfaces,
  - preserve serialized group data in memory without applying grouped logic.

---

## Phase 2 — Command API

### Scope
- Implement group-level order submission and validation.
- Map group orders onto existing order resolution primitives.

### Entry Criteria
- Phase 1 exit criteria complete.
- Order contract for group move/patrol is approved.

### Exit Criteria
- Group `move` and `patrol` commands validate and execute through turn resolution.
- Mixed-validity failure behavior is deterministic and documented.
- Telemetry emitted for issued and resolved group orders.
- Single-ship parity tests pass unchanged.

### Telemetry Requirements
- `fleet_group_order_issued` emitted at submission.
- `fleet_group_order_result` emitted on completion with success/failure and reason.
- `fleet_group_created` continuity retained from Phase 1.

### Rollback Switch Strategy
- Command dispatch checks `enable_fleet_groups` at API boundary.
- When off:
  - reject group-order endpoints with a controlled error,
  - preserve existing single-ship endpoints with no behavior drift.

---

## Phase 3 — UI Controls

### Scope
- Add selection and control affordances for creating/managing groups.
- Expose group order controls in relevant ship/fleet panels.

### Entry Criteria
- Phase 2 API is stable enough for UI integration.
- UX wireframe/interaction rules approved.

### Exit Criteria
- Players can create a group from multi-selection and issue supported group orders.
- Group status (size, order, destination/route summary) is visible.
- UI handles command failures with actionable messages.
- Telemetry confirms UI-issued group actions are captured.
- Single-ship command UI remains functionally unchanged.

### Telemetry Requirements
- `fleet_group_created` on UI group creation flow.
- `fleet_group_order_issued` from UI command actions.
- `fleet_group_order_result` surfaced for success/failure outcomes.

### Rollback Switch Strategy
- UI elements hidden/disabled when `enable_fleet_groups` is off.
- Existing single-ship controls remain the only visible path in rollback mode.

---

## Phase 4 — Save Migration

### Scope
- Add persistence for groups and membership.
- Define migration behavior for older saves and rollback compatibility.

### Entry Criteria
- Runtime model and command/UI semantics stabilized.
- Serialization format proposal reviewed.

### Exit Criteria
- Save/load supports group entities and membership fields.
- Older saves load with safe defaults (no groups) and no regression.
- Schema version bump implemented and documented.
- Migration tests cover forward load and rollback load scenarios.

### Save Compatibility Checklist
- [ ] Add group membership fields to ship/group save structures.
- [ ] Keep absent membership fields backward-compatible (default/null handling).
- [ ] Bump save schema version and document exact version transition.
- [ ] Verify pre-bump saves load without data loss in non-group features.
- [ ] Verify post-bump saves load when feature switch is off (groups inert, no crash).
- [ ] Define behavior when downgrading to a build without fleet-group awareness.
- [ ] Add regression tests for load/save round-trip including grouped and ungrouped fleets.

### Telemetry Requirements
- `fleet_group_created`, `fleet_group_order_issued`, `fleet_group_order_result` remain schema-stable across load boundaries.
- On load failure tied to migration, emit error telemetry with schema version and failure category.

### Rollback Switch Strategy
- Rollback mode must continue to parse persisted group fields.
- Group data remains stored but inactive when `enable_fleet_groups` is off.
- Emergency fallback: one-way "deactivate groups" migration path that retains ships and clears active group orders only.

---

## Phase 5 — Balancing and Hardening

### Scope
- Tune group command friction, clarity, and power relative to single-ship play.
- Harden edge cases and telemetry dashboards.

### Entry Criteria
- Phases 1–4 complete and feature is internally playable.
- Baseline telemetry dashboards available.

### Exit Criteria
- Balance pass completed with defined KPIs (order success rate, command churn, time-to-issue).
- No critical defects in group command execution for target release window.
- Parity tests and migration tests green in release pipeline.
- Go/No-Go review explicitly signs off rollback readiness.

### Telemetry Requirements
- Monitor event volume and outcome ratios for:
  - `fleet_group_created`
  - `fleet_group_order_issued`
  - `fleet_group_order_result` (success vs failure reasons)
- Establish alert thresholds for elevated failure rates and rollback trigger points.

### Rollback Switch Strategy
- Production rollback runbook includes:
  - switch disable procedure,
  - expected player-facing impact,
  - post-rollback telemetry checks,
  - criteria for re-enable.

---

## Release Readiness Checklist
- [ ] All five phases meet exit criteria.
- [ ] Single-ship parity tests pass in CI for release candidate.
- [ ] Save compatibility checklist is fully complete.
- [ ] Telemetry dashboards and alerts are active.
- [ ] Rollback dry run performed in staging.
- [ ] `docs/FEATURE_STATUS.md` updated from `Future` to `Partial`/`Shipped` as implementation progresses.
