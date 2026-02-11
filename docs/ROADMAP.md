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

## Prioritization Scoring Model

Use this model for all backlog candidates before assigning a release bucket.

### Scoring dimensions
- **Retention impact (1-5):** Expected effect on session depth and return rate. 5 = strongest expected lift.
- **Implementation risk (1-5):** Complexity and uncertainty in delivery. 5 = highest risk.
- **Testability (1-5):** Ease of validating behavior via automated/manual checks. 5 = easiest to test.
- **Save migration risk (1-5):** Risk of save incompatibility or migration bugs. 5 = highest risk.
- **Mobile performance cost (1-5):** Runtime/battery/thermal impact on mobile. 5 = highest cost.

### Weighted priority score
`Priority Score = (Retention Impact × 3) + (Testability × 2) - (Implementation Risk × 2) - (Save Migration Risk × 2) - (Mobile Performance Cost × 1)`

- **Interpretation:**
  - `>= 7`: candidate for **next patch** or **next minor** depending on team capacity.
  - `1 to 6`: candidate for **next minor**.
  - `<= 0`: **long-term** unless strategic reasons override.

### Current candidate scoring

| Candidate | Retention Impact | Implementation Risk | Testability | Save Migration Risk | Mobile Perf Cost | Priority Score | Release Bucket |
|---|---:|---:|---:|---:|---:|---:|---|
| Fleet Group Management | 5 | 3 | 3 | 2 | 2 | 8 | Next patch |
| Real-Time System Animation | 3 | 3 | 3 | 1 | 4 | 1 | Next minor |
| Sound Effects and Music | 4 | 3 | 4 | 1 | 2 | 8 | Next minor |
| Sub-Body Objects (Moons, Stations, Asteroid Mining) | 4 | 5 | 2 | 5 | 3 | -9 | Long-term |

> Buckets are reviewed each milestone. A lower-scoring item can move up only with explicit rationale (e.g., prerequisite for core strategy loop).

### P0 — High Impact, Low Risk
No P0 items currently pending.

### P1 — High Impact, Medium Risk

#### 5. Fleet Group Management
- **Why:** Late-game fleet management is tedious with many individual ships.
- **Acceptance criteria:** Select multiple ships and issue group orders (move, patrol). Show fleet strength summary.
- **Effort:** L
- **Risk:** Medium — requires new data model for fleet groups.
- **Release bucket:** Next patch.
- **Post-release success metrics (first 14 days):**
  - +10% median ships commanded per turn in sessions with `fleet_group_created`.
  - +8% turn completion rate for saves with >20 ships.
  - +5% median session length in strategy-heavy sessions.
- **Minimum telemetry hooks (required):**
  - `fleet_group_created`, `fleet_group_order_issued`, `fleet_group_disbanded`.
  - Context properties: `save_id_hash`, `turn_number`, `ship_count`, `group_size`, `platform`.
- **Rollback criterion (required):** Roll back if turn processing errors increase by >=2% for saves using groups, or if turn completion rate drops >=5% versus control after 7 days.

### P2 — Medium Impact

### P3 — Future / Larger Scope

#### 11. Sub-Body Objects (Moons, Stations, Asteroid Mining)
- **Why:** Third map level (Moon/Body) has limited content since data model lacks moons.
- **Acceptance criteria:** Planets can have moons[] sub-array. Gas giants have moon systems. Asteroid belts have mining spots.
- **Effort:** L
- **Risk:** High — data model change, save migration needed.
- **Release bucket:** Long-term.
- **Post-release success metrics (first 30 days):**
  - +15% feature usage: sessions with `sub_body_view_opened`.
  - +7% median session length for players reaching body-level maps.
  - Migration success >=99.5% for eligible legacy saves.
- **Minimum telemetry hooks (required):**
  - `sub_body_view_opened`, `moon_selected`, `asteroid_mining_started`, `save_migration_sub_body_result`.
  - Context properties: `save_schema_from`, `save_schema_to`, `system_id`, `body_id`, `platform`.
- **Rollback criterion (required):** Roll back if save migration failure exceeds 0.5% or crash-free session rate falls by >=1% in migrated saves.

#### 12. Real-Time System Animation
- **Why:** Orbital motion would make system view more visually engaging.
- **Acceptance criteria:** Planets slowly orbit the star. Moons orbit planets. Animation rate adjustable.
- **Effort:** M
- **Risk:** Medium — performance; touch target stability.
- **Release bucket:** Next minor.
- **Post-release success metrics (first 14 days):**
  - +12% system-map dwell time in sessions with animation enabled.
  - No more than +5% median frame-time increase on supported mobile devices.
  - +3% turn completion rate from players who keep animation enabled.
- **Minimum telemetry hooks (required):**
  - `system_animation_toggled`, `system_animation_rate_changed`, `system_map_frame_time_sample`.
  - Context properties: `platform`, `device_tier`, `fps_bucket`, `animation_rate`, `battery_saver_mode`.
- **Rollback criterion (required):** Roll back if P95 frame time worsens by >20% on mid-tier mobile or tap mis-selection rate rises >=3%.

#### 13. Sound Effects and Music
- **Why:** Audio feedback improves immersion.
- **Acceptance criteria:** UI click sounds, ambient space music, alert sounds for events/combat.
- **Effort:** L
- **Risk:** Medium — asset licensing, Kivy audio backend on Android.
- **Release bucket:** Next minor.
- **Post-release success metrics (first 14 days):**
  - +8% feature usage: sessions with audio enabled for >50% of playtime.
  - +4% median session length among users not muting immediately.
  - No regression in turn completion rate on Android.
- **Minimum telemetry hooks (required):**
  - `audio_setting_changed`, `sfx_played`, `music_track_started`, `audio_backend_error`.
  - Context properties: `platform`, `output_mode`, `muted`, `volume_bucket`, `device_model`.
- **Rollback criterion (required):** Roll back if `audio_backend_error` exceeds 1% of sessions or Android ANR/crash rates increase >=0.5%.

## Feature Planning Gate (Mandatory)

Every planned feature in this roadmap must include all four before entering active implementation:
1. **Scoring row** using the prioritization model above.
2. **Release bucket** (`next patch`, `next minor`, `long-term`).
3. **Minimum telemetry hooks** (event names + context payload).
4. **One explicit rollback criterion** tied to measurable thresholds.
