# Gate Horizons — Prioritised Improvement Backlog

## Recently Completed
- [x] Gravity Well Map (3-level hierarchical system view)
- [x] Intra-system movement (no turn cost)
- [x] Test save generation (midgame, lategame, sandbox)
- [x] Camera reset button on gravity well view
- [x] Map keyboard shortcuts (WASD/arrows, +/-/Home, Esc/back)
- [x] Selection highlight ring animation (system view bodies + ships)
- [x] Ship movement lines on system map (dashed path to gate)
- [x] Zoom-threshold auto-level switching (system ↔ body)
- [x] Mini-map overlay (system view context)
- [x] Turn report summary screen
- [x] Resource flow visualisation (trade route overlay)
- [x] Planet comparison view
- [x] Fog of war visualization on system map

## Priority Backlog

### P0 — High Impact, Low Risk
No P0 items currently pending.

### P1 — High Impact, Medium Risk

#### 5. Fleet Group Management
- **Why:** Late-game fleet management is tedious with many individual ships.
- **Acceptance criteria:** Select multiple ships and issue group orders (move, patrol). Show fleet strength summary.
- **Effort:** L
- **Risk:** Medium — requires new data model for fleet groups.

### P2 — Medium Impact

### P3 — Future / Larger Scope

#### 11. Sub-Body Objects (Moons, Stations, Asteroid Mining)
- **Why:** Third map level (Moon/Body) has limited content since data model lacks moons.
- **Acceptance criteria:** Planets can have moons[] sub-array. Gas giants have moon systems. Asteroid belts have mining spots.
- **Effort:** L
- **Risk:** High — data model change, save migration needed.

#### 12. Real-Time System Animation
- **Why:** Orbital motion would make system view more visually engaging.
- **Acceptance criteria:** Planets slowly orbit the star. Moons orbit planets. Animation rate adjustable.
- **Effort:** M
- **Risk:** Medium — performance; touch target stability.

#### 13. Sound Effects and Music
- **Why:** Audio feedback improves immersion.
- **Acceptance criteria:** UI click sounds, ambient space music, alert sounds for events/combat.
- **Effort:** L
- **Risk:** Medium — asset licensing, Kivy audio backend on Android.
