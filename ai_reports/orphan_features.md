# Gate Horizons Audit Pack — Orphaned Core Features

Method used: targeted symbol search (no full repo scan) comparing controller/service entrypoints to UI references, plus UI handler inspection for no-op paths.

## A) Core systems with little/no UI entrypoint

| Core function/system | Where it exists | UI reference status | Evidence | Impact |
|---|---|---|---|---|
| `GameState.export_encounter_spec(...)` (non-pending encounter export constructor) | `gate_horizons/game/state.py` | no direct UI entrypoint (used by CLI/tests) | `rg -n "export_encounter_spec\("` finds state + tests + `cli.py`, while encounter UI calls `export_pending_encounter(...)`. | Core contract path exists but is not exposed from Kivy flow. |
| `GameState.resolve_encounter(...)` | `gate_horizons/game/state.py` | no direct UI call | Symbol search for `resolve_encounter(` in `gate_horizons/ui` returned no hits. | Tactical/manual resolution path is indirect only via turn processing/import. |
| `GameState.process_ship_orders(...)` | `gate_horizons/game/state.py` | no direct UI call | Symbol search in UI returned no references. | Harder to test/observe queued orders from UI explicitly. |
| `GameState.investigate_anomaly(...)` public helper | `gate_horizons/game/state.py` | not called directly by UI | UI routes anomaly via `issue_ship_order("Investigate Anomaly")`; no direct call to helper. | API surface duplication can drift. |
| `GameState.create_freighter_route(...)` | `gate_horizons/game/state.py` | no UI call found | Logistics UI calls `game_state.logistics.create_route(...)` directly. | Multiple creation paths may diverge. |

## B) UI elements wired to stubs / placeholder / no-op-ish behavior

| UI element/action | Current behavior | Evidence | Status |
|---|---|---|---|
| Ship actions: `Set Trade Route`, `Prospect`, `Set Auto-Mine` (context menu) | Shows notice “not implemented yet” only | `galaxy_map.py` `_execute_action` explicit branch at lines ~1151-1154. | stub/dead-end |
| Ship action: `Continue Mining` | Shows informational notice only | `_execute_action` branch: `_show_notice(f"{ship.name} continues mining...")`. | no-op-ish |
| Fleet screen action dispatch | Delegates to another screen’s private method | `fleet_screen.py`: `app.galaxy_map_screen._execute_action(...)`. | fragile coupling |
| Trade manual route inputs | Invalid numeric entries silently ignored | `trade_screen.py` has `except ValueError: pass`. | hidden failure path |

## C) Quick wins to reduce orphaning
1. Promote one canonical action-dispatch API (screen-agnostic) so Fleet/Galaxy Map stop cross-calling private methods.
2. Either remove dead-end context actions or add real handlers before surfacing.
3. Expose at least one debug/admin UI entry for non-UI core functions (`export_encounter_spec`, order processing introspection), or explicitly mark them CLI-only in docs.
