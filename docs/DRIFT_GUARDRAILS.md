# Drift Guardrails

## Purpose
Prevent concept drift between Gate Horizons (meta) and Spaceship Sim (tactical). This document defines rules for changes, maturity stages, and acceptable sources of truth.

## Anti-Drift Rules
1. **Contract-only integration**
   - Only `EncounterSpec.json` and `ResultSpec.json` are exchanged.
   - No shared runtime logic, no direct control of ship systems, and no hidden back‑channels.
2. **Timescale separation**
   - Strategic changes must not imply tactical control.
   - Tactical changes must not rewrite strategic state outside the ResultSpec.
3. **Canon first**
   - If a change conflicts with `docs/CANON.md`, it is rejected or versioned.
4. **Explicit non-goals**
   - Gate Horizons does **not** manage ship subsystems.
   - Spaceship Sim does **not** manage factions, economy, or the canon timeline.

## Maturity Stages
1. **Manual**
   - Encounter creation and results are authored or curated by humans.
   - Validation is manual against canon constraints.
2. **Templated**
   - EncounterSpec/ResultSpec are produced from templates with strict fields.
   - Automated validation checks for missing or invalid fields.
3. **LLM-assisted**
   - LLMs may propose encounters and narrative flavour only within templates.
   - All outputs must be validated against canon and contract rules.
   - LLMs never change canon directly and cannot bypass validation.

## Operational Checks
- Every encounter must declare:
  - Strategic intent (why this mission exists).
  - Tactical scope (what is possible locally).
  - Canon references (which canon clauses it depends on).
- Any change that blurs meta/tactical ownership is blocked until rewritten.
