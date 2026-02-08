# Encounter Contract (Conceptual)

## Purpose
Define the strict, contract‑only integration between Gate Horizons (meta) and Flaxos Spaceship Sim (tactical). This is the only supported interface.

## Contract Rules
- Gate Horizons outputs **EncounterSpec.json** (mission request).
- Spaceship Sim returns **ResultSpec.json** (mission outcomes).
- No other data exchange is allowed.
- Both sides must treat these files as immutable, versioned contracts.
- Default folders:
  - `exports/encounters/EncounterSpec.json`
  - `imports/results/ResultSpec.json`

## EncounterSpec (Mission Request)
**Owner:** Gate Horizons

**Conceptual fields** (example structure):
```json
{
  "contractVersion": "1.0",
  "encounterId": "enc-00123",
  "strategicContext": {
    "systemId": "Epsilon-Eridani",
    "factionContext": ["Civic Union", "Outer League"],
    "intent": "Recover derelict research vessel",
    "timeWindow": "3w"
  },
  "tacticalScope": {
    "location": "Inner asteroid belt",
    "allowedAssets": ["Scout", "Corvette"],
    "constraints": ["no FTL", "limited fuel", "civilian rules of engagement"]
  },
  "successCriteria": ["Retrieve black box", "Avoid civilian casualties"],
  "failureCriteria": ["Loss of all assets"],
  "rewards": {
    "intel": 4,
    "resources": {"metals": 80}
  },
  "canonRefs": ["CANON:v1.0.0#GateFTL", "CANON:v1.0.0#Factions"]
}
```

## ResultSpec (Mission Outcomes)
**Owner:** Spaceship Sim

**Conceptual fields** (example structure):
```json
{
  "contractVersion": "1.0",
  "encounterId": "enc-00123",
  "outcome": "partial_success",
  "missionTime": "2h15m",
  "assetStatus": {
    "Scout-01": "damaged",
    "Corvette-02": "operational"
  },
  "objectiveResults": {
    "Retrieve black box": true,
    "Avoid civilian casualties": false
  },
  "casualties": {
    "crew": 2,
    "civilians": 5
  },
  "loot": {
    "intel": 2,
    "resources": {"metals": 40}
  },
  "notes": "Black box recovered but civilian shuttle destroyed."
}
```

### Result interpretation (Gate Horizons)
- `loot.resources` may include negative numbers to represent resource losses.
- Outcome drives a small colony stability delta on the encounter system (success = +2, partial = +1, failure = -2, defeat = -3).

## Validation Expectations
- Contract versions must match the declared schema version.
- Any field outside the contract is ignored or rejected.
- Canon references are mandatory in EncounterSpec.
