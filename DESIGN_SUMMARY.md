# Gate Horizons — Production & Logistics Loop: Design Summary

## Overview

This document describes the production, logistics, and shipbuilding systems added to
Gate Horizons. The goal is a coherent core loop: **mine raw resources -> refine ->
manufacture components -> build infrastructure and ships** with physical freight routes
connecting colonies.

This document does not cover the tactical combat MVP or diplomacy systems, which now live
in dedicated gameplay docs and code modules.

---

## 1. Resource Taxonomy

### Tier 0 — Raw Resources (extracted from worlds)
| ID | Notes |
|---|---|
| `ore_iron` | Metals (terrestrial, belts) |
| `silicates` | Glass/ceramics base (terrestrial, belts) |
| `water_ice` | Water (terrestrial, ice bodies) |
| `fissiles` | Rare terrestrial fissiles |
| `gas_h2` | Hydrogen (gas giants) |
| `gas_he3` | Helium-3 (gas giants, rare) |
| `gas_d2` | Deuterium (tech-gated) |
| `volatiles` | Ice body volatiles |
| `organics` | Biosource feedstocks (terrestrial/ice) |
| `rare_metals` | Strategic metals |
| `exotics` | Story/tech-gated rare materials |

### Tier 1 — Processed Materials (factory recipes)
| ID | Inputs | Time |
|---|---|---|
| `metal_alloys` | 3 ore_iron | 1 tick |
| `polymers` | 3 organics | 1 tick |
| `fuel` | 2 gas_h2 + 1 water_ice | 1 tick |
| `electronics` | 2 rare_metals + 2 silicates | 2 ticks |

### Tier 2 — Components (factory recipes)
| ID | Inputs | Time |
|---|---|---|
| `hull_plating` | 4 metal_alloys + 2 silicates | 2 ticks |
| `drive_assemblies` | 2 metal_alloys + 2 electronics + 1 fuel | 3 ticks |
| `avionics` | 2 electronics + 1 rare_metals | 2 ticks |
| `hab_modules` | 3 polymers + 2 metal_alloys | 2 ticks |
| `cargo_frames` | 3 metal_alloys + 1 polymers | 2 ticks |

Legacy resources (energy, metals, exotics, credits, intel) are preserved and
continue to work through the existing colony stockpile system.

---

## 2. World-Type Resource Availability

Planets map to **world categories** that constrain extraction. The data lives in
`data/production_config.json` under `world_types` with a `planet_type_map` mapping.

| World Category | Extraction Focus | Notes |
|---|---|---|
| Terrestrial | metals, silicates, fissiles, water | Organics/rare_metals as secondary |
| Gas Giant | hydrogen, helium-3 | Deuterium is tech-gated |
| Ice Body | volatiles, water | Organics as secondary |
| Exotic | exotics | Always rare, tech/story gated |

When a colony is founded, extraction sites are auto-generated from the world category
using a deterministic hash of the planet ID.

---

## 3. Production Chain Tiers

```
                 EXTRACTION (Tier 0)
                 ore_iron, silicates, water_ice, gas_h2, volatiles, rare_metals
                         |
                    FACTORY (Tier 1)
                 metal_alloys, polymers, fuel, electronics
                         |
                    FACTORY (Tier 2)
                 hull_plating, drive_assemblies, avionics, hab_modules, cargo_frames
                         |
              ORBITAL SHIPYARD (Assembly)
                 scouts, freighters, corvettes, colony ships
```

Each colony has:
- **Extraction Sites** — produce raw resources per tick (scaled by mining infra + tech)
- **Factories** — run recipes from a queue, consuming inputs from local inventory
- **Production Inventory** — separate from legacy stockpiles; holds all 20 production resources

---

## 4. Freight Routing Model

### Routes
- Player defines **FreighterRoutes** with ordered waypoints (A -> B -> C -> A)
- Each waypoint has **cargo rules**: load/unload specific resources with thresholds
- A ship is **assigned** to a route and cycles through waypoints automatically

### Execution (per tick)
1. If ship is at current waypoint: execute cargo rules, then set course for next waypoint
2. If ship is in transit: skip (movement handled by FleetManager)
3. If ship is idle elsewhere: reposition to current waypoint

### Capacity & Thresholds
- Ship cargo capacity (mass units) is enforced — cannot overload
- `min_threshold`: only load if source has more than this amount
- `max_threshold`: only unload if destination has less than this amount
- `amount`: max to transfer per stop (0 = unlimited within capacity)

### Travel Time
- Based on BFS hop count through gate network and ship speed
- Fuel consumed per hop

### Failure Handling
- If no cargo available: ship continues to next waypoint
- If no path exists: ship idles (reported as "no_path")

### Abstract Trade Routes (colony stockpiles)
- Trade routes can be assigned **freighter capacity units** from fleet ships.
- Effective capacity per turn = base infrastructure cap + sum of assigned freighter capacity,
  scaled by logistics tech bonuses.
- Latency is handled via the in-transit queue (turns-to-arrival).
- Routes support **auto-deficit policies** with allowlists and per-resource caps to
  move goods based on destination needs each turn.
- Each turn records a **colony resource ledger** (production, consumption, imports,
  exports, net) and surfaces bottlenecks in the colony UI.

---

## 5. Shipyard / Ship Build Rules

### Orbital Facilities (built at colonies)

| Facility | Purpose | Build Cost | Build Turns | Prerequisite |
|---|---|---|---|---|
| **Spaceport** | Docking + storage, receives ships | 10 alloys, 4 hull plating, 100cr | 5 | None |
| **Drydock** | Builds scouts, freighters, miners, corvettes | 20 alloys, 8 hull plating, 4 avionics, 200cr | 8 | Spaceport |
| **Orbital Yard** | Builds all ships including colony ships | 40 alloys, 16 hull plating, 8 avionics, 4 drive assemblies, 400cr | 12 | Drydock |

### Ship Blueprints (component-based construction)

| Ship | Components | Credits | Build Turns | Required Facility |
|---|---|---|---|---|
| Scout | 2 hull plating, 1 drive, 1 avionics | 50 | 2 | Drydock |
| Miner | 3 hull plating, 1 drive, 2 cargo, 1 avionics | 60 | 3 | Drydock |
| Small Freighter | 4 hull plating, 1 drive, 4 cargo, 1 avionics | 60 | 4 | Drydock |
| Medium Freighter | 8 hull plating, 2 drive, 8 cargo, 2 avionics | 120 | 6 | Drydock |
| Corvette | 6 hull plating, 2 drive, 2 avionics, 1 cargo | 100 | 4 | Drydock |
| Colony Ship | 16 hull plating, 4 drive, 8 hab, 6 cargo, 2 avionics | 300 | 12 | Orbital Yard |
| Large Freighter | 12 hull plating, 3 drive, 12 cargo, 2 avionics | 220 | 8 | Orbital Yard |

### Concurrent Build Limits & Queues
- Drydock: 1 ship at a time (per level), with queued orders waiting behind it
- Orbital Yard: 2 ships at a time (per level)
- Queue actions: **cancel** (partial refund) and **rush** (credit cost)

---

## 6. Balance Levers

All rates, costs, and times are in `data/production_config.json`. Key tuning points:

### Extraction
- `extraction_balance.base_power_per_site`: power cost per extraction site
- `extraction_balance.mining_level_bonus`: yield bonus per mining infrastructure level (0.5)
- `extraction_balance.advanced_mining_tech_mult`: tech multiplier (1.5x)
- `extraction_balance.max_extraction_sites_per_colony`: cap at 6

### Factories
- `factory_balance.max_factories_per_colony_level`: {0: 1, 1: 2, 2: 3, 3: 4}
- `factory_balance.base_throughput`: base factory ticks per turn (1)
- `factory_balance.throughput_per_colony_level`: +1 per colony level
- `factory_balance.throughput_per_industry_level`: +1 per industry level
- `factory_balance.factory_build_cost`: 50cr + 10 alloys
- `factory_balance.factory_maintenance_per_turn`: 2 credits

### Production Storage
- `production_storage.base_caps`: raw/processed/components caps per colony
- `production_storage.colony_level_mult`: storage multiplier per colony level
- `production_storage.industry_level_mult`: storage multiplier per industry level

### Shipyard Balance
- `shipyard_balance.cancel_refund_ratio`: component/credit refund fraction
- `shipyard_balance.rush_cost_per_turn`: credits per rushed turn

### Fleet Operations
- `fleet_ops_balance.fuel_cost_per_hop`: 1 fuel per gate hop
- `fleet_ops_balance.maintenance_scaling`: 1.1x scaling with fleet size
- `fleet_ops_balance.freighter_ops_cost_per_trip`: 3 credits per trip

### Recipes
Each recipe in `recipes` has tunable `inputs`, `outputs`, `time`, and `power_cost`.

### Ship Blueprints
Each blueprint has tunable `components`, `credits`, `build_turns`.

### Orbital Facilities
Each facility type has tunable `build_cost`, `build_turns`, `max_concurrent_builds`.

---

## 7. Suggested Balance Table (starting numbers)

| Category | Value | Notes |
|---|---|---|
| Extraction base yield | 4 metals / 3 silicates | Terrestrial baseline |
| Fissiles availability | 20% | Terrestrial only |
| Gas giant hydrogen | 6 | Baseline for gas_h2 |
| Volatiles yield | 5 | Ice body baseline |
| Factory throughput | 1 + colony level + industry level | Per turn cap |
| Factory upkeep | 2 credits | Per active factory per turn |
| Production storage caps | 140/90/60 | Raw/processed/components base caps |
| Spaceport build time | 5 turns | 10 alloys + 4 hull plating |
| Drydock build time | 8 turns | 20 alloys + 8 hull plating + 4 avionics |
| Orbital yard build time | 12 turns | 40 alloys + 16 hull plating + 8 avionics + 4 drive |
| Small freighter build | 4 turns | 4 hull plating + 1 drive + 4 cargo + 1 avionics |
| Colony ship build | 12 turns | 16 hull plating + 4 drive + 8 hab + 6 cargo |
| Rush build cost | 25 credits / turn | Per active order |
| Cancel refund | 50% | Components + credits |

## 8. Progression Design

### Early Game (turns 1-20)
- Start with Earth colony (level 2) with 2 extraction sites + spaceport
- Can immediately extract ore_iron and silicates
- Build a factory -> produce metal_alloys
- Build a drydock (requires spaceport + alloys + hull plating + avionics)
- Build a small freighter at drydock

### Mid Game (turns 20-60)
- Establish 2nd colony at a resource-rich world
- Set up freight routes between colonies (raw -> processed)
- Bottleneck: electronics require rare_metals (scarce)
- Bottleneck: shipyard throughput (1-2 concurrent builds)

### Late Game (turns 60+)
- Build orbital yard -> colony ships (12 turns, expensive)
- Multiple freight routes, multiple factories per colony
- Scaling limited by:
  - Fleet maintenance costs
  - Factory maintenance costs
  - Electronics/rare_metals scarcity
  - Shipyard concurrent build limits

---

## Feature Status Table

| Feature | Before | After |
|---|---|---|
| Colony resource production | 5 abstract resources via infrastructure | + 20 production resources via extraction sites |
| Factory / processing | None | Recipes with tiered inputs/outputs and queue |
| Freight routes | Abstracted trade routes (capacity + latency) | + Physical freighter routes with waypoints and cargo rules |
| Orbital facilities | Spaceport infrastructure (1 infra slot) | Spaceport + Drydock + Orbital Yard (orbital objects) |
| Ship construction | Credits + metals at spaceport | + Component-based construction at orbital facilities |
| Ship types | 4 (scout, freighter, miner, corvette) | + 4 (small/medium/large freighters, colony ship) |
| Production inventory | None | Per-colony inventory for 20 production resources |
| Save/load | Schema v3 | Schema v4 with migration for new fields |
| Tests | 32 tests | Expanded production/logistics + trade capacity coverage |
| UI screens | 8 screens | + 3 screens (production, logistics, shipyard) |

---

## How to Run Tests

```bash
# Run all tests
python -m unittest discover -s gate_horizons/tests -v

# Run only production/logistics tests
python -m unittest gate_horizons.tests.test_production_logistics_loop -v

# Run the headless integration harness
python -m gate_horizons.tests.test_harness
```

### Expected Output
```
OK
```

---

## Tuning Notes

To adjust game balance, edit `gate_horizons/data/production_config.json`:

- **Make early game easier**: Increase `base_yield` for rocky body types, reduce
  `factory_build_cost`, reduce recipe `time` values
- **Make mid game harder**: Reduce `rare_metals` probability, increase `electronics`
  recipe time, reduce `max_concurrent_builds`
- **Slow down colony ship production**: Increase `colony_ship` component costs and
  `build_turns`, increase `orbital_yard` build cost
- **Adjust freight economics**: Change `freighter_ops_cost_per_trip` and
  `fuel_cost_per_hop`
- **Scale difficulty**: Adjust `maintenance_scaling` for fleet upkeep curve
