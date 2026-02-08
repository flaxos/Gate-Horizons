# Gate Horizons — Prioritised Improvement Backlog

## Recently Completed
- [x] Gravity Well Map (3-level hierarchical system view)
- [x] Intra-system movement (no turn cost)
- [x] Test save generation (midgame, lategame, sandbox)
- [x] Camera reset button on gravity well view
- [x] Map keyboard shortcuts (WASD/arrows, +/-/Home, Esc/back)
- [x] Selection highlight ring animation (system view bodies + ships)
- [x] Ship movement lines on system map (dashed path to gate)

## Priority Backlog

### P0 — High Impact, Low Risk
No P0 items currently pending.

### P1 — High Impact, Medium Risk

#### 4. Zoom-Threshold Auto-Level Switching
- **Why:** Natural zoom UX — zooming deep into a system could auto-switch to body detail.
- **Acceptance criteria:** At scale > 2.5x on a planet, auto-switch to body detail. At scale < 0.5x, auto-switch back to system view.
- **Effort:** M
- **Risk:** Medium — edge cases with rapid zoom, needs good thresholds and debounce.

#### 5. Fleet Group Management
- **Why:** Late-game fleet management is tedious with many individual ships.
- **Acceptance criteria:** Select multiple ships and issue group orders (move, patrol). Show fleet strength summary.
- **Effort:** L
- **Risk:** Medium — requires new data model for fleet groups.

#### 6. Resource Flow Visualisation
- **Why:** Hard to understand where resources go. Trade/logistics flows invisible.
- **Acceptance criteria:** Animated flow lines between colonies showing active trade routes and resource direction.
- **Effort:** M
- **Risk:** Medium — performance with many routes; needs throttling.

### P2 — Medium Impact

#### 7. Mini-Map Overlay
- **Why:** When zoomed into a system, lose context of galaxy position.
- **Acceptance criteria:** Small galaxy overview in corner showing current system highlighted. Click to jump.
- **Effort:** M
- **Risk:** Low-Medium.

#### 8. Turn Report Summary Screen
- **Why:** Current turn report popup is small. Lots of info gets missed.
- **Acceptance criteria:** Full-screen turn summary with sections: Research, Production, Colonies, Fleet, Events. Clickable entries that navigate to relevant screen.
- **Effort:** M
- **Risk:** Low.

#### 9. Planet Comparison View
- **Why:** When choosing where to colonise, comparing planets is manual.
- **Acceptance criteria:** Side-by-side comparison of 2-3 planets showing resources, habitability, gravity, traits.
- **Effort:** M
- **Risk:** Low.

#### 10. Fog of War Visualization on System Map
- **Why:** Unsurveyed systems show bodies but this isn't indicated visually.
- **Acceptance criteria:** Unsurveyed bodies shown as "?" silhouettes. Body details hidden until surveyed.
- **Effort:** S
- **Risk:** Low.

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
