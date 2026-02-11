# AI Helper Operating Model

## Purpose
This document defines how AI helpers collaborate on gameplay and content work while preserving release quality, balance stability, and canon consistency.

## Workflow Baseline
1. **Classify scope before implementation.**
   - If work spans multiple modules/systems, create or update an **ExecPlan in `PLANS.md` first**.
   - Single-file or isolated edits may proceed without a full ExecPlan, but should still log assumptions in the task notes.
2. **Assign role owners** for planning, implementation, QA, balance review, and canon validation.
3. **Run handoffs using standardized artifacts** (see role sections below).
4. **Gate merge on Definition of Done checklists** for the relevant feature type(s).
5. **Escalate blockers immediately** using the escalation matrix in this document.

## Role Definitions

### 1) Planner
**Primary focus:** release sequencing and dependency tracking.

**Required inputs**
- Request/problem statement and target player outcome.
- Current feature status and roadmap references.
- Dependency map (code modules, content files, tests, migrations, UI surfaces).
- Known risks (save compatibility, UI parity, economy impact).

**Required outputs**
- Execution sequence with milestones and owners.
- Dependency graph and critical path.
- Risk register with mitigation tasks.
- ExecPlan entry in `PLANS.md` for multi-module work.

**Handoff artifact format: `PLAN_HANDOFF`**
```text
PLAN_HANDOFF
- Objective:
- Scope (in/out):
- Affected modules:
- Dependency chain:
- Milestones:
- Risks + mitigations:
- Validation strategy:
- ExecPlan reference (PLANS.md section/link):
```

### 2) Implementer
**Primary focus:** code/content changes aligned to the plan.

**Required inputs**
- Approved `PLAN_HANDOFF`.
- Acceptance criteria and DoD checklist category.
- Data/schema constraints (including save compatibility expectations).
- UI behavior notes and controller mappings (if applicable).

**Required outputs**
- Minimal, traceable change set.
- Updated tests/content fixtures/docs as needed.
- Implementation notes and unresolved questions.

**Handoff artifact format: `IMPLEMENTATION_HANDOFF`**
```text
IMPLEMENTATION_HANDOFF
- Plan reference:
- Changes made (file-level):
- Behavior delta:
- Tests added/updated:
- Migration/save impact:
- Known limitations:
- Reviewer focus areas:
```

### 3) QA Auditor
**Primary focus:** static review and test verification.

**Required inputs**
- `IMPLEMENTATION_HANDOFF`.
- Relevant test commands and expected pass criteria.
- Static analysis/lint rules and regression hotspots.

**Required outputs**
- Test execution summary.
- Regression and risk findings (severity-tagged).
- Pass/fail recommendation with required fixes.

**Handoff artifact format: `QA_AUDIT_REPORT`**
```text
QA_AUDIT_REPORT
- Build/test matrix:
- Static checks run:
- Results summary:
- Defects (severity, reproduction, owner):
- Regression risk assessment:
- Release recommendation (GO / NO-GO / GO-WITH-RISKS):
```

### 4) Balance Analyst
**Primary focus:** resource and turn-economy stability.

**Required inputs**
- `IMPLEMENTATION_HANDOFF` and feature design intent.
- Baseline economy metrics (resource income/spend, progression speed, win conditions).
- Scenario definitions (early/mid/late game or equivalent slices).

**Required outputs**
- Delta analysis vs baseline metrics.
- Outlier findings and tuning recommendations.
- Risk statement for exploitation loops or pacing collapse.

**Handoff artifact format: `BALANCE_REVIEW`**
```text
BALANCE_REVIEW
- Feature under review:
- Baseline metrics:
- Post-change metrics:
- Notable deltas:
- Exploit/pacing risks:
- Tuning recommendations:
- Decision (ACCEPT / RETUNE / BLOCK):
```

### 5) Narrative/Canon Validator
**Primary focus:** lore continuity, tone, and canon compliance.

**Required inputs**
- Content/text diff or narrative behavior summary.
- Canon references and style constraints.
- Continuity-sensitive entities (factions, timeline events, named systems/characters).

**Required outputs**
- Canon compliance decision.
- Continuity conflicts and correction suggestions.
- Tone/style alignment notes.

**Handoff artifact format: `CANON_VALIDATION_REPORT`**
```text
CANON_VALIDATION_REPORT
- Scope reviewed:
- Canon references used:
- Continuity findings:
- Tone/style findings:
- Required edits:
- Decision (PASS / PASS-WITH-EDITS / FAIL):
```

## Definition of Done (DoD) Checklists

### A) Mechanics Features
- [ ] ExecPlan exists in `PLANS.md` if work spans multiple modules.
- [ ] Rules are deterministic and documented.
- [ ] Unit/integration tests cover happy path + edge cases.
- [ ] Save/load behavior validated for changed state.
- [ ] Balance Analyst review completed and accepted.
- [ ] QA Auditor recommendation is GO or GO-WITH-RISKS with explicit sign-off.

### B) UI Quality-of-Life Features
- [ ] ExecPlan exists in `PLANS.md` if work spans multiple UI/controller modules.
- [ ] UI behavior matches controller/input mappings (no drift).
- [ ] Visual states and accessibility expectations are verified.
- [ ] Existing navigation/shortcuts are regression-checked.
- [ ] QA Auditor validates key flows and reports outcome.
- [ ] User-facing docs/help text updated when behavior changes.

### C) Content Features
- [ ] ExecPlan exists in `PLANS.md` if work spans multiple content pipelines/systems.
- [ ] Content schema/contract is valid.
- [ ] Narrative/Canon Validator has PASS or PASS-WITH-EDITS (edits applied).
- [ ] Trigger conditions and rewards/outcomes are test-covered or fixture-validated.
- [ ] Balance implications are reviewed for progression/economy impact.
- [ ] Localization/style constraints are respected where applicable.

## ExecPlan Policy (Mandatory for Multi-Module Work)
- Any feature touching multiple modules/systems must start with an ExecPlan entry in `PLANS.md`.
- Planner owns initial ExecPlan creation.
- Implementer must reference the ExecPlan section in `IMPLEMENTATION_HANDOFF`.
- QA Auditor verifies delivered scope matches ExecPlan milestones.
- If scope changes materially, Planner updates the ExecPlan before additional implementation proceeds.

## Blocker Escalation Rules
Escalate blockers immediately when identified; do not defer to end-of-cycle QA.

### 1) Save Migration Risks
**Trigger examples**
- Schema/state shape change may break existing saves.
- Backward compatibility behavior is undefined.

**Escalation path**
1. Implementer flags blocker in `IMPLEMENTATION_HANDOFF`.
2. Planner opens mitigation task in ExecPlan (migration strategy + rollback).
3. QA Auditor marks release status **NO-GO** until migration validation passes.

### 2) UI/Controller Drift
**Trigger examples**
- UI action differs from controller command behavior.
- Input mapping or affordance inconsistencies appear after feature merge.

**Escalation path**
1. QA Auditor logs severity and repro in `QA_AUDIT_REPORT`.
2. Implementer patches parity gaps and updates tests.
3. Planner re-sequences release if patch impacts milestone order.

### 3) Economy Instability
**Trigger examples**
- Resource inflation/deflation beyond accepted thresholds.
- Turn-economy exploit loops or progression stalls.

**Escalation path**
1. Balance Analyst issues `BALANCE_REVIEW` decision **RETUNE** or **BLOCK**.
2. Planner adds retuning workstream to ExecPlan with measurable targets.
3. Release remains blocked until post-retune metrics return to accepted range.

## Artifact Naming and Storage
- Store handoff artifacts in task notes, PR description, or linked issue comments.
- Use the exact section labels in this document to keep reviews machine-parseable.
- Every multi-module feature must include at minimum: `PLAN_HANDOFF`, `IMPLEMENTATION_HANDOFF`, and `QA_AUDIT_REPORT`.
