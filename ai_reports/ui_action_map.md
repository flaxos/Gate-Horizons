# Gate Horizons Audit Pack — UI Action Map (targeted)

Scope: top gameplay flow actions (map navigation, turn cycle, ship actions, encounters, trade/logistics).  
Status key: **wired** (UI -> handler -> controller path exists), **dead-end** (click path ends in notice/no-op), **missing** (UI advertises action but no concrete callable chain).

| # | UI Action | UI handler | Controller / service call | Status | Evidence |
|---|---|---|---|---|---|
| 1 | End Turn (command bar) | `GalaxyMapScreen._on_end_turn` | `GameState.process_turn()` | wired | `nav_menu.py` binds end turn callback; `galaxy_map.py` calls `process_turn()`. |
| 2 | Open Colonies (Empire menu) | `GalaxyMapScreen._on_nav_by_name` | `App.switch_screen("colony_screen")` | wired | Dropdown item maps to `colony_screen` then app switch. |
| 3 | Open Trade | `GalaxyMapScreen._on_nav_by_name` | `App.switch_screen("trade_screen")` | wired | `nav_menu.py` empire items include Trade. |
| 4 | Open Production | `GalaxyMapScreen._on_nav_by_name` | `App.switch_screen("production_screen")` | wired | `nav_menu.py` empire items include Production. |
| 5 | Open Logistics | `GalaxyMapScreen._on_nav_by_name` | `App.switch_screen("logistics_screen")` | wired | `nav_menu.py` empire items include Logistics. |
| 6 | Open Shipyard | `GalaxyMapScreen._on_nav_by_name` | `App.switch_screen("shipyard_screen")` | wired | `nav_menu.py` empire items include Shipyard. |
| 7 | Open Fleet | `GalaxyMapScreen._on_nav_by_name` | `App.switch_screen("fleet_screen")` | wired | `nav_menu.py` military menu wiring. |
| 8 | Open Encounters | `GalaxyMapScreen._on_nav_by_name` | `App.switch_screen("encounter_screen")` | wired | `nav_menu.py` military menu wiring. |
| 9 | Open Relations | `GalaxyMapScreen._on_nav_by_name` | `App.switch_screen("relations_screen")` | wired | `nav_menu.py` military menu wiring. |
|10| Open Technology | `GalaxyMapScreen._on_nav_by_name` | `App.switch_screen("tech_screen")` | wired | `nav_menu.py` intel menu wiring. |
|11| Open Missions | `GalaxyMapScreen._on_nav_by_name` | `App.switch_screen("mission_screen")` | wired | `nav_menu.py` intel menu wiring. |
|12| Toggle trade flow overlay | `GalaxyMapScreen._on_toggle_trade_flows` | `StarMapWidget.set_trade_flows_enabled()` | wired | View dropdown exposes only this toggle. |
|13| Ship action: Move To / Reroute | `GalaxyMapScreen._execute_action` | `_show_destination_menu` -> `fleet.move_ship(...)` | wired | Action branch handles both names. |
|14| Ship action: Reposition (Local) | `GalaxyMapScreen._execute_action` | `GameState.execute_local_move(...)` | wired | Explicit controller call with message handling. |
|15| Ship action: Scan/Probe/Patrol/... | `GalaxyMapScreen._execute_action` | `GameState.issue_ship_order(...)` -> ship action handlers | wired | Uses central dispatch path. |
|16| Ship action: Escort | `GalaxyMapScreen._execute_action` | `_show_escort_target_menu` -> `issue_ship_order("Escort")` | wired | Dedicated selection popup path exists. |
|17| Ship action: Begin Mining | `GalaxyMapScreen._execute_action` | direct `ship.mining=True`, `ship.mission="mining"` | wired (bypasses controller) | Implemented, but bypasses dispatch path. |
|18| Ship action: Continue Mining | `GalaxyMapScreen._execute_action` | `_show_notice(...)` only | dead-end | No controller call; UX-only notice. |
|19| Ship action: Deliver/Unload/Load cargo | `GalaxyMapScreen._execute_action` | `GameState.unload_ship_cargo_to_colony` / `load_ship_cargo_from_colony` | wired | Direct state helper calls. |
|20| Ship action: Emergency Stop | `GalaxyMapScreen._execute_action` | direct ship mutation | wired (bypasses controller) | No `GameState` handler path. |
|21| Ship action: Return Home | `GalaxyMapScreen._execute_action` | path search + `fleet.move_ship(...)` | wired | Includes no-reachable-colony log message. |
|22| Ship action: Set Trade Route | `GalaxyMapScreen._execute_action` | notice only | dead-end | Explicit “not implemented yet” notice. |
|23| Ship action: Prospect | `GalaxyMapScreen._execute_action` | notice only | dead-end | Explicit “not implemented yet” notice. |
|24| Ship action: Set Auto-Mine | `GalaxyMapScreen._execute_action` | notice only | dead-end | Explicit “not implemented yet” notice. |
|25| Trade: Create route | `TradeScreen._on_create_route` | popup -> `GameState.create_trade_route(...)` | wired | Route is created and ships assigned. |
|26| Trade: Pause/Resume route | `TradeScreen._toggle_route` | route enabled flag toggle (trade manager state) | wired | Toggle button per route card. |
|27| Trade: Cancel route | `TradeScreen._cancel_route` | `game_state.trade.cancel_route(...)` | wired | Cancel button per route card. |
|28| Logistics: Create freight route | `LogisticsScreen._new_route` popup submit | `game_state.logistics.create_route(...)` | wired | Waypoint editor sends to logistics manager. |
|29| Encounters: Export spec | `EncounterScreen._export_encounter_spec` | `GameState.export_pending_encounter(...)` | wired | Uses pending encounter id. |
|30| Encounters: Import result | `EncounterScreen._import_result_spec` | `GameState.import_result_spec(...)` | wired | Filename scoped by encounter id when present. |

## Notes on main flow coverage
- Core loop path (**map -> ship actions -> end turn -> turn report -> encounters**) is wired.
- Biggest flow risks are dead-end actions in ship context menus and direct model mutations from UI handlers.
