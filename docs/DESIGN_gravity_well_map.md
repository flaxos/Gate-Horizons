# Gravity Well Map System - Design Notes

## Overview
Three-level hierarchical map view reusing the Galaxy Map's camera/input system.

## Map Levels
1. **Galaxy Map** (existing) - Star systems as nodes, gate connections as edges
2. **System Map** (new) - Star at center, planets/bodies in orbital view with pan/zoom
3. **Body Detail** (new) - Planet-centric view with surface regions/local detail

## Level Transitions
- **Breadcrumb navigation** at top: `Galaxy / [Star Name] / [Planet Name]`
- Click a system node on Galaxy Map -> opens System Map
- Click a planet on System Map -> opens Body Detail
- Breadcrumb click navigates back up

## Camera Controller Reuse
The `StarMapWidget` camera controller (pan offset, scale, pinch zoom, wheel zoom)
is extracted into a reusable `MapCameraController` mixin/base that all three
map levels share. This ensures identical gesture handling.

## Body Type Iconography
| Body Type    | Visual                              | Color             |
|-------------|-------------------------------------|-------------------|
| Star        | Large glowing circle + corona rays  | Spectral color    |
| Planet      | Circle + optional ring/atmos haze   | Type-based color  |
| Moon        | Smaller circle, crescent shadow     | Gray/silver       |
| Asteroid    | Cluster of small irregular dots     | Brown/gray        |
| Station     | Diamond/hex shape                   | Cyan/white        |

## Intra-System Movement
- `is_intra_system_move(origin, destination)` checks if both bodies share the same `system_id`
- Intra-system moves resolve immediately without advancing the turn counter
- Strategic (inter-system) moves retain current turn-cost behavior
- Ships track both `system_id` (which star system) and optionally `body_id` (which planet/body)

## Save Generation
- Script at `tools/generate_test_saves.py`
- Uses seeded RNG for deterministic output
- Creates midgame (~50% tech, 6 colonies) and lategame (100% tech, 10+ colonies) saves
- Validates by loading through `GameState.from_dict()`
