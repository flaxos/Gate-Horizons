# Gate Horizons — Production & Logistics Loop: Design Summary

## Overview

This document describes the production, logistics, and shipbuilding systems added to
Gate Horizons. The goal is a coherent core loop: **mine raw resources -> refine ->
manufacture components -> build infrastructure and ships** with physical freight routes
connecting colonies.

---

## 1. Resource Taxonomy

### Tier 0 — Raw Resources (extracted from planets)
| ID | Source |
|---|---|
| `ore_iron` | Rocky, volcanic, barren, desert, asteroid belt |
| `silicates` | Rocky, volcanic, barren, desert, asteroid belt |
| `water_ice` | Ice, oceanic, garden |
| `gas_h2` | Gas giant, ice, toxic |
| `gas_he3` | Gas giant (rare) |
| `organics` | Garden, ice, oceanic, toxic |
| `rare_metals` | Rocky (rare), volcanic, barren, desert, asteroid belt, oceanic (rare) |

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
| `hull_segments` | 4 metal_alloys | 2 ticks |
| `reactor_parts` | 2 electronics + 2 metal_alloys | 3 ticks |
| `habitat_modules` | 3 polymers + 2 metal_alloys | 2 ticks |
| `cargo_frames` | 3 metal_alloys + 1 polymers | 2 ticks |

Legacy resources (energy, metals, exotics, credits, intel) are preserved and
continue to work through the existing colony stockpile system.

---

## 2. Body-Type Resource Availability

Each planet body type offers a set of extractable raw resources with base yields and
probability. The data lives in `data/production_config.json` under `body_type_resources`.

| Body Type | Primary Resources | Notable |
|---|---|---|
| Rocky | ore_iron, silicates | rare_metals at 20% |
| Garden | ore_iron, silicates, organics, water_ice | Broad but moderate |
| Ice | water_ice (high), organics, gas_h2 | Best water source |
| Gas Giant | gas_h2 (high) | gas_he3 at 30% (rare fuel) |
| Volcanic | ore_iron (high), silicates, rare_metals | Best rare_metals |
| Oceanic | water_ice, organics | rare_metals at 15% |
| Barren | ore_iron, silicates, rare_metals | 30% rare metals |
| Desert | silicates (high), ore_iron | Good for silicates |
| Toxic | organics, rare_metals, gas_h2 | Niche but valuable |
| Asteroid Belt | ore_iron (high), rare_metals, silicates | Best mining yields |

When a colony is founded, extraction sites are auto-generated from this table using
a deterministic hash of the planet ID.

---

## 3. Production Chain Tiers

```
                 EXTRACTION (Tier 0)
                 ore_iron, silicates, water_ice, gas_h2, organics, rare_metals
                         |
                    FACTORY (Tier 1)
                 metal_alloys, polymers, fuel, electronics
                         |
                    FACTORY (Tier 2)
                 hull_segments, reactor_parts, habitat_modules, cargo_frames
                         |
              ORBITAL SHIPYARD (Assembly)
                 scouts, freighters, colony ships
```

Each colony has:
- **Extraction Sites** — produce raw resources per tick (scaled by mining infra + tech)
- **Factories** — run recipes from a queue, consuming inputs from local inventory
- **Production Inventory** — separate from legacy stockpiles; holds all 15 production resources

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

---

## 5. Shipyard / Ship Build Rules

### Orbital Facilities (built at colonies)

| Facility | Purpose | Build Cost | Build Turns | Prerequisite |
|---|---|---|---|---|
| **Spaceport** | Docking + storage, receives ships | 10 alloys, 4 hull seg, 100cr | 5 | None |
| **Drydock** | Builds scouts, freighters, miners, corvettes | 20 alloys, 8 hull seg, 4 elec, 200cr | 8 | Spaceport |
| **Orbital Yard** | Builds all ships including colony ships | 40 alloys, 16 hull seg, 8 elec, 4 reactor parts, 400cr | 12 | Drydock |

### Ship Blueprints (component-based construction)

| Ship | Components | Credits | Build Turns | Required Facility |
|---|---|---|---|---|
| Small Freighter | 4 hull, 1 reactor, 4 cargo | 60 | 4 | Drydock |
| Medium Freighter | 8 hull, 2 reactor, 8 cargo | 120 | 6 | Drydock |
| Colony Ship | 16 hull, 4 reactor, 8 habitat, 6 cargo | 300 | 12 | Orbital Yard |

### Concurrent Build Limits
- Drydock: 1 ship at a time (per level)
- Orbital Yard: 2 ships at a time (per level)

### Legacy Ships
The original ship build system (credits + metals at spaceport) is preserved for
scouts, corvettes, miners, and haulers. The new component-based system adds the
orbital pathway for the three new ship types.

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
- `factory_balance.factory_build_cost`: 50cr + 10 alloys
- `factory_balance.factory_maintenance_per_turn`: 2 credits

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

## 7. Progression Design

### Early Game (turns 1-20)
- Start with Earth colony (level 2) with 2 extraction sites + spaceport
- Can immediately extract ore_iron and silicates
- Build a factory -> produce metal_alloys
- Build a drydock (requires spaceport + alloys + hull segments)
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
| Colony resource production | 5 abstract resources via infrastructure | + 15 production resources via extraction sites |
| Factory / processing | None | Recipes with tiered inputs/outputs and queue |
| Freight routes | Abstracted trade routes (capacity + latency) | + Physical freighter routes with waypoints and cargo rules |
| Orbital facilities | Spaceport infrastructure (1 infra slot) | Spaceport + Drydock + Orbital Yard (orbital objects) |
| Ship construction | Credits + metals at spaceport | + Component-based construction at orbital facilities |
| Ship types | 4 (scout, freighter, miner, corvette) | + 3 (small freighter, medium freighter, colony ship) |
| Production inventory | None | Per-colony inventory for 15 production resources |
| Save/load | Schema v3 | Schema v4 with migration for new fields |
| Tests | 32 tests | 58 tests (+26 production/logistics tests) |
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
Ran 58 tests in ~0.1s
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
