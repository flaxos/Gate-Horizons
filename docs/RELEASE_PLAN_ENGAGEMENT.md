# Release Plan: Engagement Systems

## Status Update (Reality Sync)
- Encounter contracts are implemented and used in encounter branching.
- Order execution, refuel/repair, and action handlers are shipped.
- Mission system is shipped with anomaly/diplomacy gating hooks.
- Gate damage/capacity mechanics are implemented.

The engagement roadmap phases below are now considered shipped MVPs; future work
should move into a new engagement release plan once NEXT3 items land.

## Execution Plan
1. **Confirm Phase 1: Order Execution + Refuel/Repair + Action Handlers (Shipped)**
   - Order execution flow with validation and resolution steps.
   - Refuel/repair loops as baseline ship sustainment actions.
   - Action handler framework for engagement actions.
2. **Confirm Phase 2: Mission System + Anomaly/Diplomacy Gating (Shipped)**
   - Mission definitions, generation, and resolution flows.
   - Anomaly and diplomacy gating rules tied to narrative data.
   - Mission outcomes integrated with action handlers.
3. **Confirm Phase 3: Encounter Contract + Gate Damage/Capacity (Shipped)**
   - Encounter contracts with terms, rewards, and outcomes.
   - Gate damage and capacity mechanics affecting encounter availability.
   - Contract outcomes feed back into missions and order execution flows.
4. **Docs + Next Release Plan**
   - Update engagement documentation as phases complete.
   - Create the next gameplay/feature-focused release plan based on the upcoming roadmap.

## Phase 1: Order Execution + Refuel/Repair + Action Handlers
**Scope**
- Implement order execution flow with validation and resolution steps.
- Add refuel and repair loops as baseline ship sustainment actions.
- Establish action handler framework to unify engagement actions.

**Success criteria**
- Orders execute end-to-end with clear preconditions and outcomes.
- Refuel/repair actions update resources and states reliably.
- Action handlers can register and execute multiple engagement actions consistently.

**Dependencies / notes**
- Depends on baseline ship state and resource models.
- Requires clear action lifecycle events for telemetry and UI hooks.

## Phase 2: Mission System + Anomaly/Diplomacy Gating
**Scope**
- Introduce mission system with mission definitions, acceptance, and resolution.
- Add anomaly and diplomacy gating to control access and outcomes.

**Success criteria**
- Missions can be created, accepted, and resolved with consistent state transitions.
- Gating rules prevent invalid mission access and reflect narrative constraints.
- Mission outcomes integrate with existing action handlers.

**Dependencies / notes**
- Depends on Phase 1 action handler framework.
- Requires narrative data and gate condition definitions.

## Phase 3: Encounter Contract + Gate Damage/Capacity
**Scope**
- Implement encounter contracts to formalize engagement terms and rewards.
- Add gate damage and capacity systems to impact encounter availability.

**Success criteria**
- Encounters can be issued as contracts with clear terms and results.
- Gate damage/capacity meaningfully affect encounter availability and risk.
- Contract outcomes feed back into mission and order execution flows.

**Dependencies / notes**
- Depends on Phase 2 mission system and gating rules.
- Requires balancing guidelines for gate capacity and damage thresholds.
