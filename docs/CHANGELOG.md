# Changelog

## Unreleased

### Stabilisation Pass
- Reality sync: update engagement release plan and feature status tracking.
- Refresh README implemented/future lists to match shipped systems.
- Align roadmap, plans, and feature status with gravity well map work and pending UX items.
- Add mini-map sphere-of-influence overlay for player colonies.
- Add deterministic encounter/event/mission RNG tied to saved state for repeatable outcomes.
- Harden EncounterSpec/ResultSpec import/export validation and JSON error handling.
- Prevent invalid EncounterSpec exports from queuing pending encounters.
- Sanitize ResultSpec numeric payloads and ignore invalid pending encounter entries on load.

### NEXT3 Milestone 1 — Resource flow visualisation
- Add trade route flow overlays to the galaxy map with directional arrows and legend.
- Map overlay segments to trade route throughput for active routes.

### NEXT3 Milestone 2 — Planet comparison view
- Add a comparison popup for up to three selected bodies with colonisation stats.
- Support multi-select of bodies in the gravity well system panel.

### NEXT3 Milestone 3 — Fog of war visualization on system map
- Render unsurveyed bodies as silhouettes and redact body details until surveyed.
- Add tests for survey flag handling in comparison data and UI source.

### NEXT3 Milestone 1 — Map keyboard shortcuts parity
- Add Escape/back keyboard navigation for gravity well map levels.
- Wire gravity well map widgets to handle back navigation on Escape.

### NEXT3 Milestone 2 — Selection highlight ring animation
- Add pulsing selection rings for bodies and brighter pulses for selected ships.

### NEXT3 Milestone 3 — Ship movement lines on system map
- Add dashed movement lines from ships to the gate when a travel path is set.

### NEXT3 Milestone 1 — Zoom-threshold auto-level switching
- Add zoom threshold auto-switching between system and body views with debounce.

### NEXT3 Milestone 2 — Mini-map overlay
- Add a compact galaxy overview widget with current system highlight.

### NEXT3 Milestone 3 — Turn report summary screen
- Replace the compact popup with a full-screen turn report summary and section shortcuts.

### NEXT3 Milestone 1 — Full tech tree
- Expanded tech tree to 24 techs with new tier upgrades and effects.

### NEXT3 Milestone 2 — Procedural galaxy generation
- Added seeded procedural galaxy generator with connectivity guarantees and tests.

### NEXT3 Milestone 3 — Expanded event library
- Expanded exploration event library to 100+ entries and added validation tests.

### Phase 1 Gameplay Features
- Feature 1: Tactical hex combat MVP (turn-based grid, tactical screen, encounter launch).
- Feature 2: Diplomacy foundation (relations, encounter diplomacy actions, persistence).
- Feature 3: Encounter branching (tactical/diplomacy/evasion) with contract plumbing.
