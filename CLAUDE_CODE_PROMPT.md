# Gate Horizons — Claude Code Build Prompt

## INSTRUCTIONS FOR CLAUDE CODE

You are building "Gate Horizons," a turn-based space exploration and empire management game in Python using Kivy for Android (landscape orientation). This document is your complete build specification. Read the accompanying PROJECT_PLAN.md for full game design context.

---

## PROJECT SETUP

### Step 1: Initialize Project
```bash
mkdir -p gate_horizons/{game,ui/screens,ui/widgets,ui/styles,data/galaxy_templates,data/events,assets/placeholder,assets/ai_art,tests}
cd gate_horizons
touch game/__init__.py ui/__init__.py ui/screens/__init__.py ui/widgets/__init__.py
pip install kivy buildozer
```

### Step 2: Verify Kivy Installation
```python
# Quick test
from kivy.app import App
from kivy.uix.label import Label
class TestApp(App):
    def build(self):
        return Label(text='Gate Horizons')
TestApp().run()
```

---

## PHASE 1 BUILD ORDER

Build in this exact order. Each step should result in runnable code. Test after each step.

### STEP 1: Data Models & Game State (game/state.py, game/galaxy.py, game/ships.py, game/resources.py)

**game/galaxy.py — Star Map Graph**
```
Create a StarSystem class and GalaxyMap class.

StarSystem:
  - id: str (unique, e.g., "sol", "alpha_centauri")
  - name: str
  - x, y: float (position for rendering, normalized 0-1)
  - discovered: bool (fog of war)
  - surveyed: bool (details revealed)
  - tier: int (0=unexplored, 1=core, 2=developing, 3=frontier)
  - planets: list[Planet]  # sub-locations within system
  - stationed_ships: list[ship_id]
  - colony: Colony or None
  - gate_connections: list[str]  # IDs of connected systems
  - gate_active: bool
  - gate_activation_cost: dict (resource costs to activate dormant gate)
  - anomalies: list[dict]  # undiscovered features

Planet (dataclass):
  - id: str
  - name: str
  - type: str (rocky, gas_giant, ice, volcanic, oceanic, barren)
  - resources: dict  # {resource_type: yield_per_turn}
  - colonizable: bool
  - description: str

GalaxyMap:
  - systems: dict[str, StarSystem]
  - load_from_json(filepath) — load galaxy template
  - get_neighbors(system_id) -> list[StarSystem]
  - get_path(from_id, to_id) -> list[str]  # BFS shortest path through active gates
  - get_distance(from_id, to_id) -> int  # path length
  - activate_gate(system_id) -> bool  # check cost, activate
  - get_systems_by_tier(tier) -> list[StarSystem]
```

**game/ships.py — Ship System**
```
Create Ship class and Fleet manager.

Ship:
  - id: str (uuid)
  - name: str
  - ship_class: str (scout, freighter, miner, corvette)
  - location: str (system_id)
  - destination: str or None
  - path: list[str]  # remaining waypoints
  - stats: ShipStats dataclass
  - cargo: dict  # {resource: amount}
  - fuel: int (turns remaining)
  - hull: int (current HP)
  - morale: int (0-100)
  - mission: str or None  # current assignment
  - trade_route: TradeRoute or None

ShipStats (dataclass, loaded from ships.json):
  - max_hull: int
  - speed: int  # nodes per turn
  - cargo_capacity: int
  - sensor_range: int
  - fuel_capacity: int
  - combat_power: int
  - maintenance_cost: int  # credits per turn
  - abilities: list[str]  # determines contextual menu options

FleetManager:
  - ships: dict[str, Ship]
  - create_ship(ship_class, location, name=None) -> Ship
  - move_ship(ship_id, destination_id) -> bool  # validates path exists
  - process_movement(ship_id) -> MovementResult  # advance along path by speed
  - get_ships_at(system_id) -> list[Ship]
  - get_contextual_actions(ship_id) -> list[Action]  # KEY METHOD — see below
  - destroy_ship(ship_id)
  - repair_ship(ship_id, amount)
```

**Contextual Actions Logic (critical system):**
```
get_contextual_actions(ship_id) should return available actions based on:
  1. Ship class abilities
  2. Current location properties (has colony? has asteroids? has anomaly?)
  3. Current mission status
  4. Resource availability

Examples:
  Scout at unexplored system: [Scan System, Deploy Probe, Investigate Anomaly, Move To, Return Home]
  Scout at explored system: [Move To, Investigate Anomaly (if any), Patrol]
  Freighter at colony: [Load Cargo, Unload Cargo, Set Trade Route, Move To]
  Freighter in transit: [Continue, Reroute, Emergency Stop]
  Miner at asteroid field: [Begin Mining, Prospect, Set Auto-Mine Route, Move To]
  Miner mining: [Continue Mining, Load Cargo, Move To]
  Corvette anywhere: [Patrol, Move To, Escort (select ship), Intercept (if hostiles)]
  Corvette at hostile: [Engage, Retreat, Hail]
  Any ship at colony with shipyard: [Repair, Refuel]
```

**game/resources.py — Resource Manager**
```
ResourceManager:
  - global_resources: dict  # {resource_type: amount} — empire-wide totals
  - per_system_resources: dict[str, dict]  # per-colony breakdown
  - resource_types: [energy, metals, exotics, credits, intel]
  - add(resource, amount, system_id=None)
  - spend(resource, amount, system_id=None) -> bool  # returns False if insufficient
  - can_afford(cost_dict) -> bool
  - get_income_summary() -> dict  # per-turn production minus consumption
  - process_turn()  # calculate all production/consumption, apply
```

**game/state.py — Master Game State**
```
GameState:
  - galaxy: GalaxyMap
  - fleet: FleetManager
  - resources: ResourceManager
  - tech: TechTree
  - events: EventEngine
  - turn_number: int
  - game_time: str  # "Month Year" representation
  - difficulty: str
  - log: list[str]  # turn-by-turn history log
  
  - new_game() -> GameState  # initialize fresh game
  - save(filepath)
  - load(filepath) -> GameState
  - to_dict() -> dict  # serializable
  - from_dict(data) -> GameState
```

### STEP 2: Game Data Files (data/*.json)

**data/galaxy_templates/demo_galaxy.json**
```
Create a 12-system galaxy with this layout:

Sol (center, starting system, Level 1)
├── Gate to Alpha Centauri (active, nearby)
├── Gate to Tau Ceti (active, nearby)
└── Gate to Barnard's Star (dormant — requires activation)

Alpha Centauri (Level 3, frontier)
├── Gate to Sol
├── Gate to Sirius (active)
└── 2 rocky planets, 1 asteroid belt

Tau Ceti (Level 3, frontier)
├── Gate to Sol
├── Gate to Epsilon Eridani (active)
└── 1 oceanic planet (highly colonizable), 1 gas giant

Barnard's Star (Level 3, frontier, requires gate repair)
├── Gate to Sol (dormant)
├── Gate to Luyten's Star (active)
└── Rich asteroid fields, no habitable planets

Sirius (Level 3, deeper)
├── Gate to Alpha Centauri
├── Gate to Procyon (active)
├── Gate to Vega (dormant)
└── 1 volcanic planet (exotics), 1 barren

Epsilon Eridani (Level 3, deeper)
├── Gate to Tau Ceti
├── Gate to 61 Cygni (active)
└── 2 rocky planets, good for colonization

Luyten's Star (Level 3, deep)
├── Gate to Barnard's Star
├── Gate to Ross 128 (dormant)
└── Ice planet, interesting anomaly

Procyon (Level 3, deep)
├── Gate to Sirius
└── Gas giant system, fuel depot potential

Vega (Level 3, very deep, mysterious)
├── Gate to Sirius (dormant)
└── Ancient structure detected, alien artifact signals

61 Cygni (Level 3, deep)
├── Gate to Epsilon Eridani
├── Gate to Kapteyn's Star (active)
└── Binary star system, unusual readings

Ross 128 (Level 3, very deep)
├── Gate to Luyten's Star (dormant)
└── Possible alien contact signals

Kapteyn's Star (Level 3, furthest)
├── Gate to 61 Cygni
└── Edge of known network, ancient gate hub ruins

Positions should form a roughly radial graph from Sol outward.
Include x,y coordinates normalized 0-1 for rendering.
```

**data/ships.json**
```json
{
  "scout": {
    "name": "Pathfinder-class Scout",
    "max_hull": 30,
    "speed": 3,
    "cargo_capacity": 10,
    "sensor_range": 3,
    "fuel_capacity": 12,
    "combat_power": 5,
    "maintenance_cost": 3,
    "build_cost": {"credits": 50, "metals": 20},
    "build_turns": 2,
    "abilities": ["scan", "probe_deploy", "investigate", "retreat_boost"]
  },
  "freighter": {
    "name": "Hauler-class Freighter",
    "max_hull": 50,
    "speed": 1,
    "cargo_capacity": 100,
    "sensor_range": 1,
    "fuel_capacity": 8,
    "combat_power": 2,
    "maintenance_cost": 5,
    "build_cost": {"credits": 80, "metals": 40},
    "build_turns": 3,
    "abilities": ["load_cargo", "unload_cargo", "set_trade_route", "emergency_jettison"]
  },
  "miner": {
    "name": "Excavator-class Miner",
    "max_hull": 40,
    "speed": 1,
    "cargo_capacity": 60,
    "sensor_range": 1,
    "fuel_capacity": 10,
    "combat_power": 3,
    "maintenance_cost": 4,
    "build_cost": {"credits": 60, "metals": 35},
    "build_turns": 3,
    "abilities": ["prospect", "extract", "basic_refine", "auto_mine"]
  },
  "corvette": {
    "name": "Sentinel-class Corvette",
    "max_hull": 60,
    "speed": 2,
    "cargo_capacity": 15,
    "sensor_range": 2,
    "fuel_capacity": 10,
    "combat_power": 20,
    "maintenance_cost": 7,
    "build_cost": {"credits": 100, "metals": 50},
    "build_turns": 4,
    "abilities": ["patrol", "escort", "intercept", "blockade", "engage"]
  }
}
```

**data/tech_tree.json**
```json
{
  "propulsion": {
    "tier1": {
      "efficient_drives": {
        "name": "Efficient Drives",
        "description": "Improve fuel efficiency for all ships by 20%",
        "cost": {"intel": 10, "turns": 3},
        "effect": {"fuel_efficiency": 1.2},
        "prerequisites": []
      },
      "gate_resonance": {
        "name": "Gate Resonance Tuning",
        "description": "Reduce gate activation energy cost by 30%",
        "cost": {"intel": 15, "turns": 4},
        "effect": {"gate_cost_reduction": 0.3},
        "prerequisites": []
      }
    },
    "tier2": {
      "burst_drives": {
        "name": "Burst Acceleration",
        "description": "+1 speed for Scout and Corvette classes",
        "cost": {"intel": 25, "exotics": 5, "turns": 5},
        "effect": {"speed_bonus": {"scout": 1, "corvette": 1}},
        "prerequisites": ["efficient_drives"]
      }
    }
  },
  "engineering": {
    "tier1": {
      "reinforced_hulls": {
        "name": "Reinforced Hulls",
        "description": "+20% hull points for all ships",
        "cost": {"intel": 10, "turns": 3},
        "effect": {"hull_bonus": 1.2},
        "prerequisites": []
      },
      "rapid_construction": {
        "name": "Rapid Construction",
        "description": "-1 turn for all ship and building construction",
        "cost": {"intel": 12, "turns": 3},
        "effect": {"build_time_reduction": 1},
        "prerequisites": []
      }
    },
    "tier2": {
      "advanced_mining": {
        "name": "Advanced Mining Rigs",
        "description": "+50% mining yield for Miner-class ships",
        "cost": {"intel": 20, "exotics": 3, "turns": 4},
        "effect": {"mining_yield": 1.5},
        "prerequisites": ["reinforced_hulls"]
      }
    }
  },
  "sensors": {
    "tier1": {
      "deep_scan": {
        "name": "Deep Scanning Arrays",
        "description": "+1 sensor range for all ships, reveal hidden anomalies",
        "cost": {"intel": 10, "turns": 3},
        "effect": {"sensor_bonus": 1, "reveal_hidden": true},
        "prerequisites": []
      }
    },
    "tier2": {
      "predictive_analysis": {
        "name": "Predictive Threat Analysis",
        "description": "+15% combat auto-resolve accuracy",
        "cost": {"intel": 20, "turns": 4},
        "effect": {"combat_accuracy_bonus": 0.15},
        "prerequisites": ["deep_scan"]
      }
    }
  },
  "xenology": {
    "tier1": {
      "signal_decryption": {
        "name": "Signal Decryption",
        "description": "Can decode alien transmissions, unlocking diplomacy events",
        "cost": {"intel": 15, "turns": 4},
        "effect": {"unlock_diplomacy": true},
        "prerequisites": []
      }
    },
    "tier2": {
      "cultural_exchange": {
        "name": "Cultural Exchange Protocols",
        "description": "+30% favorable diplomacy outcomes",
        "cost": {"intel": 25, "exotics": 5, "turns": 5},
        "effect": {"diplomacy_bonus": 0.3},
        "prerequisites": ["signal_decryption"]
      }
    }
  }
}
```

**data/events/exploration.json — Create 15 exploration events with this structure:**
```json
[
  {
    "id": "exp_001",
    "title": "Derelict Station",
    "description": "Your scout detects a massive structure orbiting the third planet — a station of clearly alien construction, powered down but structurally intact. Faint energy readings suggest some systems could be reactivated.",
    "requirements": {"ship_class": "scout", "system_surveyed": false},
    "choices": [
      {
        "text": "Send a boarding team to investigate",
        "outcomes": [
          {"probability": 0.6, "result": "success", "description": "Your team finds a cache of exotic materials and data fragments about the gate network.", "rewards": {"exotics": 5, "intel": 8}},
          {"probability": 0.3, "result": "partial", "description": "The station's automated defenses activate briefly. Minor hull damage but you recover some useful data.", "rewards": {"intel": 3}, "costs": {"hull_damage": 10}},
          {"probability": 0.1, "result": "failure", "description": "A catastrophic power surge forces emergency evacuation. The station destabilizes and breaks apart.", "rewards": {}, "costs": {"hull_damage": 20}}
        ]
      },
      {
        "text": "Scan from a safe distance",
        "outcomes": [
          {"probability": 0.9, "result": "success", "description": "Long-range scans reveal the station's general layout and composition. Useful data, but you'll need to return for a deeper look.", "rewards": {"intel": 4}},
          {"probability": 0.1, "result": "partial", "description": "Your scans trigger a brief transmission from the station — a looping message in an unknown language.", "rewards": {"intel": 6}}
        ]
      },
      {
        "text": "Mark location and move on",
        "outcomes": [
          {"probability": 1.0, "result": "success", "description": "You log the coordinates for a future expedition. Sometimes discretion is the better part of valor.", "rewards": {"intel": 1}}
        ]
      }
    ],
    "tags": ["anomaly", "derelict", "alien_tech"],
    "tier_requirement": 3,
    "one_time": true
  }
]
```
Generate 14 more events following this exact structure, with varied scenarios:
- Ancient probe discovery
- Unusual energy signature from a gas giant
- Abandoned mining colony (non-human)
- Distress signal from unknown source
- Crystalline asteroid with exotic properties
- Dormant alien vessel adrift
- Planetary surface ruins detected
- Unstable wormhole fragment near a gate
- Biological anomaly on a moon
- Encrypted data beacon
- Gravitational anomaly
- Comet with unusual composition
- Evidence of recent alien activity
- Hidden gate fragment

### STEP 3: Colony System (game/colonies.py)

```
Colony:
  - system_id: str
  - planet_id: str
  - name: str
  - population: int
  - happiness: int (0-100)
  - infrastructure: dict
    {
      "housing": {"level": int, "building": bool, "turns_remaining": int},
      "industry": {"level": int, "building": bool, "turns_remaining": int},
      "defense": {"level": int, "building": bool, "turns_remaining": int},
      "research": {"level": int, "building": bool, "turns_remaining": int},
      "spaceport": {"level": int, "building": bool, "turns_remaining": int}
    }
  - build_queue: list[dict]  # queued construction orders
  - production_output: dict  # calculated per turn
  - consumption: dict  # calculated per turn
  
  - get_tier() -> int:
      # Level 1: all infrastructure >= 3
      # Level 2: any infrastructure >= 1 AND established colony
      # Level 3: outpost only, minimal infrastructure
  
  - calculate_production() -> dict:
      # Based on population assigned to each infrastructure
      # Industry level → metals production
      # Research level → intel generation
      # Spaceport level → ship build speed, trade capacity
  
  - calculate_consumption() -> dict:
      # Population consumes energy and credits
      # Infrastructure maintenance costs
  
  - process_turn():
      # Advance construction
      # Apply population growth (base 5%, modified by happiness/housing)
      # Calculate and apply production/consumption
      # Check for tier promotion
      # Trigger colony events if applicable

ColonyManager:
  - colonies: dict[str, Colony]
  - establish_colony(system_id, planet_id, name, initial_pop) -> Colony
  - abandon_colony(system_id) -> bool
  - get_total_production() -> dict
  - get_total_consumption() -> dict
  - process_all_turns()
```

### STEP 4: Trade Route System (game/trade.py)

```
TradeRoute:
  - id: str
  - source_system: str
  - destination_system: str
  - assigned_ships: list[str]  # freighter ship IDs
  - resource_manifest: dict  # what to carry each direction
    {
      "outbound": {"metals": 20, "energy": 10},  # source → destination
      "inbound": {"exotics": 5, "credits": 30}   # destination → source
    }
  - active: bool
  - efficiency: float  # based on distance, ship speed, route safety
  
  - calculate_throughput() -> dict:
      # Per-turn resource transfer based on freighter count and capacity
  
TradeManager:
  - routes: dict[str, TradeRoute]
  - create_route(source, dest, ships, manifest) -> TradeRoute
  - cancel_route(route_id)
  - process_turn():
      # Move trade goods
      # Check for route disruptions (pirate events)
      # Update efficiency based on current conditions
  - get_route_summary() -> list[dict]  # for UI display
```

### STEP 5: Combat Auto-Resolve (game/combat.py)

```
CombatResolver:
  - calculate_odds(attacker_ships: list[Ship], defender: EncounterData) -> float:
      # Sum combat power of attackers
      # Compare to defender strength
      # Apply tech bonuses
      # Return win probability 0.0 to 1.0
  
  - auto_resolve(attacker_ships, defender, odds) -> CombatResult:
      # Roll against odds with ±15% variance
      # Calculate damage distribution
      # Determine loot/rewards
      # Return CombatResult with all details
  
CombatResult:
  - victory: bool
  - attacker_damage: dict[ship_id, int]  # damage per ship
  - ships_destroyed: list[str]
  - loot: dict  # resources gained
  - intel_gained: int
  - narrative: str  # flavor text for the outcome
  - xp_gained: int  # future use

EncounterData:
  - type: str (pirates, alien_patrol, hazard, derelict_defense)
  - strength: int
  - description: str
  - loot_table: dict
  - flee_difficulty: float  # chance to escape
```

### STEP 6: Event Engine (game/events.py)

```
EventEngine:
  - available_events: list[Event]  # loaded from JSON
  - triggered_events: list[str]  # IDs of one-time events already triggered
  - event_queue: list[Event]  # events waiting for player resolution
  
  - load_events(directory)  # load all event JSON files
  
  - check_triggers(game_state) -> list[Event]:
      # Each turn, evaluate which events can fire
      # Filter by requirements (ship location, tier, tech level, etc.)
      # Random selection weighted by relevance
      # Return 0-3 events per turn
  
  - resolve_event(event_id, choice_index) -> EventOutcome:
      # Player picks a choice
      # Roll against outcome probabilities
      # Apply rewards/costs to game state
      # Return outcome for display
  
Event:
  - id, title, description, choices, tags, requirements
  - Loaded directly from JSON structure defined above

EventOutcome:
  - event_id: str
  - choice_made: str
  - result: str  # success/partial/failure
  - description: str
  - rewards_applied: dict
  - costs_applied: dict
```

### STEP 7: Turn Processing (game/turn.py)

```
TurnProcessor:
  - process_turn(game_state) -> TurnReport:
      # Execute in this order:
      1. Process ship movements (advance all ships along paths)
      2. Process mining operations (ships set to auto-mine)
      3. Process trade routes (move goods along routes)
      4. Process colony production/consumption
      5. Process construction queues (colonies and ships)
      6. Process tech research (advance active research)
      7. Apply maintenance costs (ship upkeep from credits)
      8. Check event triggers
      9. Apply population growth
      10. Update fog of war (systems within sensor range of player ships)
      11. Check victory/milestone conditions
      12. Increment turn counter
      
      Return TurnReport with summary of everything that happened

TurnReport:
  - turn_number: int
  - ships_moved: list[dict]
  - resources_gained: dict
  - resources_spent: dict
  - construction_completed: list[str]
  - events_triggered: list[Event]
  - combat_encounters: list[CombatResult]
  - discoveries: list[str]
  - warnings: list[str]  # low fuel, low resources, unhappy colonies
  - milestone_reached: str or None
```

### STEP 8: Save/Load System (game/save_load.py)

```
Use SQLite with a single save table approach:

Schema:
  saves table:
    - id: INTEGER PRIMARY KEY
    - save_name: TEXT
    - timestamp: TEXT (ISO format)
    - turn_number: INTEGER
    - game_data: TEXT (JSON blob of entire GameState.to_dict())
    - thumbnail_data: TEXT (optional — base64 mini-map snapshot)

SaveManager:
  - db_path: str  # path to saves.db
  - save_game(game_state, save_name) -> int  # returns save ID
  - load_game(save_id) -> GameState
  - list_saves() -> list[dict]  # id, name, timestamp, turn for display
  - delete_save(save_id)
  - auto_save(game_state)  # save to "autosave" slot
```

### STEP 9: Kivy UI — Galaxy Map (PRIMARY SCREEN)

**ui/screens/galaxy_map.py**
```
This is the main game screen. Build it with these elements:

1. STAR MAP (center, ~70% of screen):
   - Render system nodes as circles color-coded by tier
   - Render gate connections as lines (cyan=active, gray=dormant)
   - Render ship icons at their current locations
   - Tap a system node → zoom/select, show system info panel
   - Tap a ship icon → show ship info, contextual actions
   - Pan with touch drag
   - Pinch zoom (or +/- buttons)
   - Fog of war: undiscovered systems shown as dim "?" markers
   - Discovered but unsurveyed: basic info shown
   - Fully surveyed: full detail

2. TOP BAR (persistent):
   - Turn counter: "Turn 1 — January 2157"
   - Resources: ⚡ Energy | 🔩 Metals | 💎 Exotics | 💰 Credits | 🔍 Intel
   - Each showing current amount and per-turn delta (+/-)
   - Notification badge (count of pending events)

3. BOTTOM BAR (persistent):
   - Navigation buttons: [Map] [Fleet] [Tech] [Colonies]
   - [END TURN] button (prominent, right side)
   - Turn processing shows a brief "Processing..." overlay

4. SIDE PANEL (slides in on selection):
   - When system selected: name, tier badge, planets list, ships present, actions
   - When ship selected: stats, cargo, mission, contextual action buttons

Use Kivy Canvas for the star map rendering (draw circles, lines).
Use Kivy widgets for UI panels.
Color scheme from PROJECT_PLAN.md section 9.
```

### STEP 10: Kivy UI — Additional Screens

**ui/screens/system_view.py**
- Zoomed view of a single system
- Shows planets as larger circles in orbital arrangement
- Click planet for details, resources, colonization option
- Ships shown with status indicators
- Build ship button (if spaceport exists)

**ui/screens/colony_screen.py**
- Infrastructure grid: 5 categories, each showing level bars
- Build button for each (grayed if can't afford)
- Population display with growth indicator
- Happiness meter
- Production summary (what this colony produces/consumes)
- Build queue list

**ui/screens/fleet_screen.py**
- List of all ships with: name, class icon, location, mission status, hull bar
- Tap ship → detail view with full stats
- Assign mission button → contextual options
- Build ship section (if at system with spaceport)

**ui/screens/tech_screen.py**
- Visual tree layout: 4 branches shown as columns
- Researched techs highlighted, available techs bright, locked techs dim
- Tap tech → info popup with cost, effect, prerequisites
- "Research" button on available techs
- Active research shown with progress bar

**ui/screens/event_screen.py**
- Modal popup overlay
- Event title and description text (scrollable if long)
- Choice buttons (2-4 options)
- After choice: outcome description, rewards/costs applied
- "Continue" button to dismiss

**ui/screens/main_menu.py**
- Title: "GATE HORIZONS"
- Subtitle: "A Space Exploration & Empire Management Sim"
- Buttons: [New Game] [Continue (loads autosave)] [Load Game] [Settings]
- Background: simple starfield (can be kivy canvas dots)

### STEP 11: Context Menu Widget

**ui/widgets/context_menu.py**
```
This is a CRITICAL UI element. When the player taps a ship or system,
a contextual menu appears with available actions.

Implementation:
- Radial or list menu that appears at tap location
- Actions populated by get_contextual_actions() from game logic
- Each action is a button with icon placeholder + text
- Tapping an action triggers the corresponding game logic
- Menu dismisses on action selection or tap-away

Actions should clearly show:
- Action name
- Resource cost (if any)
- Estimated turns (if movement)
- Risk level (if encounter possible)
```

### STEP 12: Turn Report & Notifications

**ui/widgets/notification.py**
```
After END TURN processing:
1. Show a Turn Report summary screen/overlay:
   - "Turn 5 — May 2157"
   - Bulleted summary of key events
   - "3 ships arrived at destinations"
   - "Mining operation produced: 8 Metals, 1 Exotic"
   - "Colony growth: +120 population at Tau Ceti"
   - "EVENT: Distress Signal Detected" (tap to view)
2. Pending events shown as cards that must be resolved
3. Warnings shown for critical issues (low fuel, attacks)
```

---

## CRITICAL IMPLEMENTATION NOTES

### Architecture Rules
1. **Game logic must NEVER import from ui/**: Keep model/controller completely separate from view
2. **UI reads from game state**: All UI screens reference GameState to render
3. **Actions go through GameState methods**: UI calls game_state.fleet.move_ship(), never modifies state directly
4. **All game data loaded from JSON**: Never hardcode game content in Python; always load from data/ files
5. **Save/Load must capture ENTIRE state**: If it exists in GameState, it must serialize

### Kivy-Specific Notes
1. Use `kivy.config.Config.set('graphics', 'orientation', 'landscape')` in main.py
2. Use `ScreenManager` for navigation between screens
3. The galaxy map should use `kivy.graphics.Canvas` for drawing nodes/edges
4. Use `ScatterLayout` or custom touch handling for pan/zoom on the star map
5. Use `Popup` widget for event screens and confirmations
6. Use `kivy.clock.Clock.schedule_once` for deferred UI updates after turn processing
7. All touch targets minimum 48dp for mobile usability

### Performance Considerations
1. Only render visible nodes on the star map (frustum culling)
2. Cache path calculations (BFS results) until galaxy topology changes
3. Limit event checks per turn to prevent lag
4. SQLite saves should be <1MB for the demo scope
5. Target 30fps minimum on the star map screen

### Testing Approach
1. Unit test all game logic (no Kivy dependency)
2. Test galaxy graph pathfinding
3. Test resource economy (does it balance over 100 turns?)
4. Test save/load round-trip (save → load → save → compare)
5. Test event engine filtering and resolution
6. Manual playtest: Can you play 50 turns without breaking?

---

## QUICK START COMMAND

After reading this document and PROJECT_PLAN.md, begin building in this order:

```bash
# 1. Set up project structure
# 2. Create all JSON data files first (ships, tech, galaxy, events)
# 3. Build game/ modules in order: galaxy → ships → resources → colonies → trade → combat → events → turn → state → save_load
# 4. Create a simple test harness that runs 10 turns headless (no UI) and prints results
# 5. Build Kivy UI starting with main_menu → galaxy_map → system_view → colony_screen
# 6. Wire UI to game state
# 7. Playtest and iterate
```

The test harness (step 4) is your proof that the engine works before touching UI. It should:
- Create a new game
- Print starting state
- Auto-issue some orders (send scout to Alpha Centauri, build a miner)
- Process 10 turns
- Print end state with full resource summary
- Save and reload, verify state matches
