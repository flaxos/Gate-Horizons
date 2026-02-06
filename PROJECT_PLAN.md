# Gate Horizons: Project Plan & Game Design Document

## Version 0.1 — Demo Slice
## Genre: Turn-Based Space Exploration & Empire Management Sim
## Platform: Android (Kivy/Python) — Landscape Orientation
## Developer: Solo

---

## 1. Concept & Vision

### High Concept
Humanity discovers that a dormant asteroid in the Sol system is actually a disabled jump gate — part of an ancient intergalactic transit network. Through reverse engineering and bold exploration, players guide humanity's expansion into a galaxy already teeming with civilizations, trade routes, and dangers.

### Core Fantasy
You are the strategic mind behind humanity's first steps onto the galactic stage. Every jump through a gate is a decision: what do you send, what do you risk, and what do you bring back?

### Design Pillars
1. **Hard Sci-Fi Grounding** — Mass/energy costs, logistics chains, signal delays, realistic constraints
2. **Exploration as Discovery** — The galaxy is a puzzle; each gate opened reveals more of the ancient network
3. **Empire as a Machine** — Factorio-style satisfaction of building efficient resource/trade networks
4. **Meaningful Choices** — Every ship sent, every route opened, every first contact matters
5. **Mobile-First Design** — Deep gameplay in 5-15 minute sessions via turn-based mechanics

### Tone & Aesthetic
- Hard sci-fi with a sense of wonder (think Expanse meets Stellaris meets FTL)
- UI: Clean, functional, data-rich (think submarine/mission control aesthetic)
- Placeholder art initially — geometric shapes, color-coded by function
- Later: AI-generated art swapped in for ships, planets, gates, portraits

---

## 2. Core Gameplay Loop

### Per-Session Loop (5-15 minutes)
```
Check notifications/events from last session
  → Review empire status (mini-map, resource summary)
    → Issue orders to ships (move, scan, mine, trade, colonize, engage)
      → Resolve encounters (auto or manual tactical mini-game)
        → Process turn (all actions resolve, economy ticks, events fire)
          → Repeat or save & exit
```

### Strategic Loop (Multi-Session)
```
Explore frontier (Level 3) → Discover resources & contacts
  → Establish outposts (Level 2) → Build infrastructure
    → Develop into core worlds (Level 1) → Generate surplus
      → Fund deeper exploration → Expand sphere of influence
```

---

## 3. The World Tier System

### Level 1 — Core Worlds
- **Status:** Self-sustaining, generates surplus resources
- **Player Attention:** Low — mostly automated, occasional policy decisions
- **Produces:** Manufactured goods, trained population, credits, advanced ships
- **Events:** Political/social (labor disputes, cultural shifts, elections)
- **Visual:** Bright, developed, multiple orbital structures

### Level 2 — Developing Worlds
- **Status:** Active construction, resource-hungry, partially dependent on Level 1
- **Player Attention:** Medium-High — this is where you optimize
- **Produces:** Refined materials, fuel, intermediate goods
- **Needs:** Population, manufactured goods, protection from threats
- **Events:** Construction milestones, supply shortages, pirate raids, environmental hazards
- **Promotion:** Becomes Level 1 when all infrastructure categories reach threshold
- **Visual:** Scaffolding, partial structures, active mining operations

### Level 3 — Frontier
- **Status:** Unexplored or minimally surveyed, temporary outposts only
- **Player Attention:** High — every action is a decision
- **Produces:** Intel, rare resources, alien artifacts, first contact opportunities
- **Needs:** Survey ships, fuel, brave crews
- **Events:** Anomalies, alien encounters, environmental dangers, discovery moments
- **Promotion:** Becomes Level 2 when outpost established and basic resource extraction begins
- **Visual:** Dark, unknown, scanner overlay aesthetic

---

## 4. Game Systems

### 4.1 Star Map & Navigation
- **Structure:** Node-based graph; each node is a star system, edges are gate connections
- **Fog of War:** Unexplored systems show as unknown nodes; surveying reveals details
- **Gate Mechanics:**
  - Gates have activation costs (energy/exotic materials)
  - Some gates are damaged — require repair before use
  - Gate capacity limits: mass throughput per turn
  - Strategic chokepoints where gates converge
- **Mini-Map:** Zoomed out view showing sphere of influence with color-coded tiers

### 4.2 Ship System
Ships are your primary agency in the world. Each has capabilities that determine available contextual actions.

#### Ship Classes (Demo Slice — 4 types)
| Class | Role | Key Stats | Contextual Actions |
|-------|------|-----------|-------------------|
| **Scout** | Exploration, intel | Fast, low cargo, sensors | Scan, Probe Deploy, Investigate, Retreat |
| **Freighter** | Trade, resource transport | Slow, high cargo, minimal weapons | Load/Unload, Set Trade Route, Emergency Jettison |
| **Miner** | Resource extraction | Medium speed, mining equipment | Prospect, Extract, Refine (basic), Set Auto-Mine |
| **Corvette** | Military, escort | Fast, armed, low cargo | Patrol, Escort, Engage, Intercept, Blockade |

#### Ship Stats
- **Hull Points** — Damage capacity
- **Speed** — Nodes traversed per turn
- **Cargo Capacity** — Resource/goods carrying limit
- **Sensor Range** — Detection radius (nodes)
- **Fuel** — Turns of operation before refueling required
- **Crew Morale** — Affects efficiency, can cause mutiny at very low levels
- **Maintenance Cost** — Per-turn upkeep in credits

### 4.3 Resource System (Demo Slice — 5 resources)
| Resource | Source | Used For |
|----------|--------|----------|
| **Energy** | Solar/fusion at colonies, fuel depots | Gate activation, ship fuel, manufacturing |
| **Metals** | Asteroid mining, planetary extraction | Ship construction, infrastructure |
| **Exotics** | Rare deposits, alien trade, anomalies | Gate repair, advanced tech research |
| **Credits** | Trade, taxation of colonies | Ship maintenance, diplomacy, recruitment |
| **Intel** | Scout missions, probes, signal intercepts | Tech tree unlocks, map reveals, diplomatic advantage |

### 4.4 Colony Management
- **Infrastructure Categories:** Housing, Industry, Defense, Research, Spaceport
- **Each has 5 levels** (0-4); Level 2 world needs most at level 2+; Level 1 needs all at 3+
- **Population:** Grows naturally, can be transported; workers assigned to infrastructure
- **Happiness:** Affected by defense level, trade goods availability, overcrowding
- **Production Queues:** Queue buildings, ships, improvements per colony

### 4.5 Trade Routes
- **Physical Routes:** Actual freighter ships traveling gate paths on fixed schedules
- **Setup:** Assign freighter(s) to a route between two systems
- **Capacity:** Based on number/size of freighters assigned
- **Vulnerability:** Can be raided, disrupted by gate damage, blockaded
- **Auto-Management:** Once set, trade routes operate automatically each turn
- **Supply/Demand:** Colonies generate and consume different resources; surpluses traded

### 4.6 Encounter System
Encounters trigger when ships interact with points of interest or hostile entities.

#### Auto-Resolve
- Compare fleet strength vs encounter difficulty
- Base win probability shown to player (e.g., 73%)
- Roll result ± 15% variance
- Quick resolution, standard rewards

#### Manual Tactical Mode (Mini-Game)
- **Grid:** 8×6 hex grid
- **Turn-Based:** Move → Action → Enemy Turn
- **Ship Placement:** Position your ships at start
- **Actions:** Fire weapons, use abilities (scan, shield boost, ram), move
- **Terrain:** Asteroids (cover), nebula (stealth), gate proximity (escape route)
- **Rewards:** Manual wins give 20% bonus loot/intel + possible special finds
- **Encounter Types:**
  - Combat (pirates, hostile aliens, rival factions)
  - Evasion (escape superior forces, navigate hazard)
  - Diplomacy (negotiate with aliens — dialogue choices affect outcome)
  - Salvage (explore derelict — risk/reward room-by-room)

### 4.7 Tech Tree
- **Unlocked with Intel resource** + turn investment
- **4 Branches:**
  - **Propulsion:** Ship speed, fuel efficiency, gate cost reduction
  - **Engineering:** Ship hulls, mining efficiency, construction speed
  - **Sensors:** Scan range, anomaly detection, tactical bonuses
  - **Xenology:** Diplomacy bonuses, alien tech integration, cultural understanding
- **Demo Slice:** ~20 techs total (5 per branch, 3 tiers each)

### 4.8 Events & Narrative
- **Pre-generated content library** (built with LLM during development, stored as JSON)
- **Event Categories:**
  - Exploration discoveries (anomalies, derelicts, signals)
  - Colony events (political, social, economic)
  - Encounter narratives (first contact, pirate demands, distress signals)
  - Gate network lore (ancient builder story told through fragments)
- **Event Structure:** Title, description text, 2-4 player choices, outcomes per choice
- **Context-Sensitive:** Events filtered by game state (world tier, tech level, faction relations)

---

## 5. Technical Architecture

### 5.1 Tech Stack
| Component | Technology |
|-----------|-----------|
| **Language** | Python 3.11+ |
| **UI Framework** | Kivy 2.3+ |
| **Data Storage** | SQLite (save games) + JSON (game data/content) |
| **Build/Deploy** | Buildozer (Kivy → Android APK) |
| **Architecture** | MVC — Model (game state), View (Kivy UI), Controller (game logic) |

### 5.2 Project Structure
```
gate_horizons/
├── main.py                     # Entry point, App class
├── buildozer.spec              # Android build config
│
├── game/                       # Game logic (Model + Controller)
│   ├── __init__.py
│   ├── state.py                # Master game state container
│   ├── galaxy.py               # Star map, nodes, edges (gates)
│   ├── ships.py                # Ship classes, stats, movement
│   ├── colonies.py             # Colony management, infrastructure, population
│   ├── resources.py            # Resource tracking, production, consumption
│   ├── trade.py                # Trade route logic
│   ├── combat.py               # Auto-resolve + tactical mini-game logic
│   ├── tech.py                 # Tech tree state and unlocks
│   ├── events.py               # Event engine — selection, resolution
│   ├── turn.py                 # Turn processing — tick all systems
│   └── save_load.py            # SQLite save/load
│
├── ui/                         # Kivy UI (View layer)
│   ├── __init__.py
│   ├── screens/
│   │   ├── main_menu.py        # Title screen, load/new game
│   │   ├── galaxy_map.py       # Star map view (primary screen)
│   │   ├── system_view.py      # Zoomed into a single system
│   │   ├── colony_screen.py    # Colony management detail
│   │   ├── fleet_screen.py     # Ship list, assignments
│   │   ├── tech_screen.py      # Tech tree browser
│   │   ├── event_screen.py     # Event popup / narrative display
│   │   ├── tactical_screen.py  # Combat mini-game
│   │   └── trade_screen.py     # Trade route management
│   ├── widgets/
│   │   ├── context_menu.py     # Contextual action menu for ships/systems
│   │   ├── resource_bar.py     # Top-bar resource display
│   │   ├── mini_map.py         # Zoomed-out empire overview
│   │   ├── ship_card.py        # Ship info card widget
│   │   └── notification.py     # Event/alert notifications
│   └── styles/
│       └── theme.kv            # Kivy style definitions
│
├── data/                       # Static game data (JSON)
│   ├── galaxy_templates/       # Pre-built galaxy layouts
│   │   └── demo_galaxy.json    # 12-system demo map
│   ├── ships.json              # Ship class definitions
│   ├── tech_tree.json          # Tech tree structure
│   ├── resources.json          # Resource definitions
│   ├── events/                 # Pre-generated narrative content
│   │   ├── exploration.json    # ~50 exploration events
│   │   ├── colony.json         # ~30 colony events
│   │   ├── encounters.json     # ~40 encounter narratives
│   │   └── lore.json           # ~20 gate network lore fragments
│   └── factions.json           # Alien faction definitions
│
├── assets/                     # Art, sound (placeholder)
│   ├── placeholder/            # Geometric placeholder sprites
│   └── ai_art/                 # Folder for future AI-generated art
│
└── tests/                      # Unit tests
    ├── test_galaxy.py
    ├── test_combat.py
    ├── test_economy.py
    └── test_turns.py
```

### 5.3 Key Design Decisions
1. **Kivy for UI** — Native widget set, good touch support, compiles to Android via Buildozer
2. **Landscape orientation** — More screen real estate for star map and tactical grid
3. **Turn-based** — Lower battery/CPU, perfect for mobile sessions, easier to balance
4. **JSON for game data** — Easy to edit, extend, and pre-generate with LLM tools
5. **SQLite for saves** — Robust, single-file, built into Python, works on Android
6. **MVC separation** — Game logic testable without UI; UI swappable

---

## 6. Demo Slice Scope (Phase 1)

### What's Playable
- **12-system star map** connected by gates (pre-designed layout)
- **Sol system** as starting point with the dormant gate
- **4 ship types** buildable and commandable
- **5 resources** tracked with production/consumption
- **Contextual menus** on ships and systems
- **Basic colony management** (build infrastructure, assign population)
- **Trade routes** between owned systems
- **Auto-resolve combat** with probability display
- **10-15 pre-generated events** that fire based on game state
- **Simple tech tree** (10 unlocks across 2 branches)
- **Turn processing** that ticks all systems forward
- **Save/Load** functionality
- **Mini-map** with sphere of influence visualization

### What's NOT in Demo Slice
- Tactical mini-game (Phase 2)
- Full tech tree (Phase 2)
- Alien diplomacy system (Phase 2)
- AI-generated art (Phase 3)
- Sound/music (Phase 3)
- Android APK build (Phase 2 — develop on desktop first)
- Multiplayer (not planned)

---

## 7. Phased Development Plan

### Phase 1: Playable Demo Slice (Target: 2-3 weeks)
**Goal:** Complete gameplay loop on desktop with placeholder art

| Week | Focus | Deliverables |
|------|-------|-------------|
| 1 | Core engine & data | Galaxy graph, ship movement, resource tracking, turn processing, save/load |
| 1 | Star map UI | Kivy galaxy map with node rendering, ship indicators, fog of war |
| 2 | Interaction systems | Contextual menus, colony management screen, basic economy |
| 2 | Events & encounters | Event engine, auto-resolve combat, 10-15 narrative events |
| 3 | Polish & loop | Trade routes, mini-map, tech tree (basic), tutorial flow, balancing |

### Phase 2: Feature Complete (Target: 3-4 weeks after Phase 1)
- Tactical hex combat mini-game
- Full tech tree (20-30 techs)
- Alien factions with diplomacy
- Expanded event library (100+ events)
- Galaxy generation (procedural)
- Android build via Buildozer
- Performance optimization for mobile

### Phase 3: Art & Polish (Target: 2-3 weeks after Phase 2)
- AI-generated ship/planet/portrait art
- UI visual overhaul
- Sound effects and ambient music
- Tutorial improvements
- Balance pass based on playtesting

### Phase 4: Expansion (Ongoing)
- More ship types, resources, tech
- Story campaign mode
- Expanded galaxy sizes
- Achievements system

---

## 8. Content Pre-Generation Plan

All narrative content will be pre-generated using Claude/LLM and stored as JSON files.

### Content Manifest
| Category | Count | Format |
|----------|-------|--------|
| Exploration events | 50 | JSON: title, description, choices[], outcomes[] |
| Colony events | 30 | JSON: title, description, choices[], requirements{} |
| Encounter narratives | 40 | JSON: type, description, options[], difficulty |
| Lore fragments | 20 | JSON: title, text, discovery_context |
| Planet descriptions | 30 | JSON: name, type, description, resource_hints[] |
| Alien faction profiles | 5 | JSON: name, description, traits[], disposition |
| Ship flavor text | 20 | JSON: class, name_options[], description |
| Anomaly descriptions | 25 | JSON: title, scan_text, investigate_text, outcomes[] |

### Generation Strategy
- Use Claude to generate batches with consistent tone/lore
- Include tags for filtering (tier_requirement, tech_requirement, faction_involved)
- Each event has multiple outcome branches for replayability
- Lore fragments form a coherent meta-narrative about the gate builders

---

## 9. UI/UX Design Notes

### Primary Screens (Landscape)
1. **Galaxy Map** (home screen) — Nodes, edges, ship positions, fog of war; tap node to zoom
2. **System View** — Orbiting bodies, stationed ships, local resources; tap objects for context menu
3. **Colony Screen** — Infrastructure grid, population, production queues, happiness meter
4. **Fleet Screen** — Ship roster, stats, assignments, build queue
5. **Tech Screen** — Visual tech tree, costs, unlock status
6. **Event Popup** — Narrative text, choice buttons, outcome display

### Interaction Model
- **Tap node/ship** → Contextual radial menu with available actions
- **Drag** → Pan the star map
- **Pinch** → Zoom in/out (galaxy ↔ system view)
- **Long press** → Info tooltip
- **Top bar** — Always visible: Turn counter, resource totals, notification badges
- **Bottom bar** — Navigation: Map | Fleet | Tech | Colony | End Turn button

### Color Palette (Placeholder Phase)
| Element | Color | Hex |
|---------|-------|-----|
| Background (space) | Near black | #0A0E17 |
| Gates (active) | Cyan | #00E5FF |
| Gates (dormant) | Dim gray | #3A3A4A |
| Level 1 worlds | Gold | #FFD700 |
| Level 2 worlds | Blue | #4A90D9 |
| Level 3 / frontier | Red-orange | #FF6B35 |
| Player ships | Green | #00FF88 |
| Enemy/unknown | Red | #FF3333 |
| Resources text | White | #E8E8E8 |
| UI panels | Dark blue-gray | #1A2233 |

---

## 10. Balancing Guidelines (Initial Values)

### Turn Economy
- 1 turn ≈ 1 month of game time
- Scout moves 3 nodes/turn; Freighter 1 node/turn; Corvette 2 nodes/turn; Miner 1 node/turn
- Colony infrastructure: 3-5 turns per level
- Tech research: 2-8 turns depending on tier
- Population growth: ~5% per turn at full happiness

### Resource Rates (Per Turn, Per Source)
| Source | Energy | Metals | Exotics | Credits |
|--------|--------|--------|---------|---------|
| Basic colony (L1 infrastructure) | +10 | +5 | +0 | +15 |
| Asteroid mining op | +0 | +8 | +1 | +0 |
| Trade route (per freighter) | varies | varies | varies | +5 |
| Scout survey bonus | +0 | +0 | +0-2 | +0 |

### Ship Costs (Credits / Metals / Turns to Build)
| Ship | Credits | Metals | Build Turns |
|------|---------|--------|-------------|
| Scout | 50 | 20 | 2 |
| Freighter | 80 | 40 | 3 |
| Miner | 60 | 35 | 3 |
| Corvette | 100 | 50 | 4 |

---

## 11. Open Questions & Future Considerations

1. **Signal Delay Mechanic** — Should messages between distant colonies take turns to arrive? Adds realism but complexity. (Phase 2 decision)
2. **Gate Builder Meta-Story** — What happened to them? Options: Ascended, civil war, still watching, natural disaster. (Define during content gen)
3. **Permadeath for Ships** — Lost ships are gone forever, or can crews eject/be rescued? (Leaning toward permanent loss with rescue chance)
4. **Faction Aggression AI** — How proactive should alien factions be? (Phase 2 — start with reactive/scripted)
5. **Difficulty Levels** — Modify resource rates, encounter difficulty, alien aggression? (Phase 3)
6. **Procedural Galaxy Generation** — Algorithm for balanced, interesting maps? (Phase 2)
