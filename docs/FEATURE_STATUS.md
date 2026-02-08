# Feature Status

| Feature | Designed In (doc) | Implemented In (files) | Status (Shipped/Partial/Future) | Notes |
| --- | --- | --- | --- | --- |
| EncounterSpec/ResultSpec handshake | `docs/ENCOUNTER_CONTRACT.md` | `gate_horizons/game/combat.py`, `gate_horizons/game/state.py`, `gate_horizons/tests/test_encounter_contract.py`, `gate_horizons/tests/test_encounter_branching.py` | Shipped | Contract schema exists; results apply resources, stability, relations, and gate impact. |
| Auto-resolve combat | `PROJECT_PLAN.md` | `gate_horizons/game/combat.py`, `gate_horizons/game/turn.py` | Shipped | Deterministic auto-resolve with variance tied to encounter resolution. |
| Tactical hex combat MVP | `PROJECT_PLAN.md` | `gate_horizons/game/tactical.py`, `gate_horizons/ui/screens/tactical_screen.py`, `gate_horizons/ui/screens/encounter_screen.py` | Shipped | Hex grid combat with tactical screen and encounter launch. |
| Diplomacy foundation | `PROJECT_PLAN.md`, `docs/RELEASE_PLAN_GAMEPLAY_FEATURES.md` | `gate_horizons/game/diplomacy.py`, `gate_horizons/ui/screens/relations_screen.py`, `gate_horizons/ui/screens/encounter_screen.py` | Shipped | Relation scores, diplomacy actions, persistence. |
| Missions (auto-generated + progress tracking) | `docs/RELEASE_PLAN_ENGAGEMENT.md` | `gate_horizons/game/missions.py`, `gate_horizons/game/turn.py`, `gate_horizons/ui/screens/mission_screen.py` | Shipped | Auto-generated missions with progress + rewards. |
| Ship order execution + action handlers | `docs/RELEASE_PLAN_ENGAGEMENT.md` | `gate_horizons/game/state.py`, `gate_horizons/game/turn.py` | Shipped | Validated ship orders executed during turn resolution. |
| Refuel/repair actions | `docs/RELEASE_PLAN_ENGAGEMENT.md` | `gate_horizons/game/state.py`, `gate_horizons/game/ships.py` | Shipped | Resource-backed refuel/repair handlers with failure reasons. |
| Colony logistics loop | `PROJECT_PLAN.md`, `DESIGN_SUMMARY.md` | `gate_horizons/game/colonies.py`, `gate_horizons/game/trade.py`, `gate_horizons/game/turn.py` | Shipped | Production/consumption + trade latency + tests. |
| Physical freighter routes | `DESIGN_SUMMARY.md` | `gate_horizons/game/logistics.py`, `gate_horizons/ui/screens/logistics_screen.py` | Shipped | Waypoint-based freight routes. |
| Shipyard production | `DESIGN_SUMMARY.md` | `gate_horizons/game/shipyard.py`, `gate_horizons/ui/screens/shipyard_screen.py` | Shipped | Orbital facilities + ship build queue. |
| Tech tree (24 techs, queueing, effects) | `PROJECT_PLAN.md`, `docs/RELEASE_PLAN_GAMEPLAY_FEATURES.md` | `gate_horizons/game/tech.py`, `gate_horizons/data/tech_tree.json`, `gate_horizons/ui/screens/tech_screen.py` | Shipped | Tech effects drive logistics, sensors, and construction. |
| Exploration event library (105 events) | `PROJECT_PLAN.md` | `gate_horizons/game/events.py`, `gate_horizons/data/events/exploration.json`, `gate_horizons/data/events/exploration_extra.json`, `gate_horizons/ui/screens/event_screen.py` | Shipped | Event engine + exploration events, one-time gating. |
| Gravity well map (system/body detail) | `docs/DESIGN_gravity_well_map.md` | `gate_horizons/ui/screens/gravity_well_map.py`, `gate_horizons/ui/widgets/map_camera.py` | Shipped | Hierarchical map view with breadcrumb navigation and camera reset. |
| Intra-system movement (no turn cost) | `docs/ROADMAP.md` | `gate_horizons/game/ships.py`, `gate_horizons/game/state.py`, `gate_horizons/tests/test_intra_system_movement.py` | Shipped | In-system moves resolve instantly without advancing the turn. |
| Deterministic test save generator | `docs/ROADMAP.md` | `tools/generate_test_saves.py`, `saves/test_midgame_50pct_tech.json`, `saves/test_lategame_100pct_tech.json`, `saves/test_sandbox_small.json` | Shipped | Generates midgame/lategame/sandbox saves with seeded RNG. |
| Map camera keyboard shortcuts | `docs/ROADMAP.md` | `gate_horizons/ui/widgets/map_camera.py`, `gate_horizons/ui/screens/gravity_well_map.py` | Shipped | Pan/zoom/reset via keyboard; Escape now steps back to the previous map level. |
| Zoom-threshold auto-level switching | `docs/ROADMAP.md` | `gate_horizons/ui/screens/gravity_well_map.py` | Shipped | Auto-switch between system and body levels based on zoom thresholds. |
| Mini-map overlay | `PROJECT_PLAN.md`, `docs/ROADMAP.md` | `gate_horizons/ui/screens/gravity_well_map.py` | Shipped | Compact galaxy context overlay when viewing a system. |
| Turn report summary screen | `docs/ROADMAP.md` | `gate_horizons/ui/screens/turn_report_screen.py`, `gate_horizons/ui/screens/galaxy_map.py` | Shipped | Full-screen summary with section shortcuts replacing the popup. |
| Fog of war visualization on system map | `docs/ROADMAP.md` | — | Future | Unsurveyed bodies shown as silhouettes until surveyed. |
| Mini-map + sphere-of-influence overlay | `PROJECT_PLAN.md` | — | Future | Planned for demo slice polish. |
| Piracy/trade disruption events | `PROJECT_PLAN.md`, `README.md` | — | Future | Planned as part of broader event coverage. |
| Diplomacy-based trade agreements | `PROJECT_PLAN.md`, `README.md` | — | Future | Planned diplomacy extension beyond current relations/actions. |
| Selection highlight ring animation | `docs/ROADMAP.md` | `gate_horizons/ui/screens/gravity_well_map.py` | Shipped | Pulsing selection rings for bodies and ships on the system view. |
| Ship movement lines on system map | `docs/ROADMAP.md` | `gate_horizons/ui/screens/gravity_well_map.py` | Shipped | Dashed movement line from ship row to gate when a path is active. |
| Procedural galaxy generation | `PROJECT_PLAN.md`, `docs/RELEASE_PLAN_GAMEPLAY_FEATURES.md` | `gate_horizons/game/galaxy.py`, `gate_horizons/game/state.py`, `gate_horizons/tests/test_galaxy_generation.py` | Shipped | Seeded generator with deterministic connectivity. |
| Expanded event library (100+ events) | `PROJECT_PLAN.md`, `docs/RELEASE_PLAN_GAMEPLAY_FEATURES.md` | `gate_horizons/data/events/exploration.json`, `gate_horizons/data/events/exploration_extra.json`, `gate_horizons/game/events.py`, `gate_horizons/tests/test_event_library_content.py` | Shipped | 100+ exploration events loaded via event engine. |
