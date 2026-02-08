# Feature Status

| Feature | Designed In | Implemented In | Status | Evidence | Notes |
| --- | --- | --- | --- | --- | --- |
| EncounterSpec/ResultSpec handshake | `docs/ENCOUNTER_CONTRACT.md` | `gate_horizons/game/combat.py`, `gate_horizons/game/state.py`, `gate_horizons/tests/test_encounter_contract.py`, `gate_horizons/tests/test_encounter_branching.py` | Shipped | — | Contract schema exists; results apply resources, stability, and relations. |
| Auto-resolve combat | `PROJECT_PLAN.md` | `gate_horizons/game/combat.py`, `gate_horizons/game/turn.py` | Shipped | — | Deterministic-ish auto-resolve with variance, tied to encounters. |
| Tactical hex combat MVP | `PROJECT_PLAN.md` | `gate_horizons/game/tactical.py`, `gate_horizons/ui/screens/tactical_screen.py`, `gate_horizons/ui/screens/encounter_screen.py` | Shipped | — | Hex grid combat with tactical screen and encounter launch. |
| Diplomacy foundation | `PROJECT_PLAN.md` | `gate_horizons/game/diplomacy.py`, `gate_horizons/ui/screens/relations_screen.py`, `gate_horizons/ui/screens/encounter_screen.py` | Shipped | — | Relation scores, diplomacy actions, persistence. |
| Colony logistics loop | `PROJECT_PLAN.md`, `DESIGN_SUMMARY.md` | `gate_horizons/game/colonies.py`, `gate_horizons/game/trade.py`, `gate_horizons/game/turn.py` | Shipped | — | Production/consumption + trade latency + tests. |
| Physical freighter routes | `DESIGN_SUMMARY.md` | `gate_horizons/game/logistics.py`, `gate_horizons/ui/screens/logistics_screen.py` | Shipped | — | Waypoint-based freight routes. |
| Shipyard production | `DESIGN_SUMMARY.md` | `gate_horizons/game/shipyard.py`, `gate_horizons/ui/screens/shipyard_screen.py` | Shipped | — | Orbital facilities + ship build queue. |
