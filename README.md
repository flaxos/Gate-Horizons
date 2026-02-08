# Gate-Horizons
Genre: Turn-Based Space Exploration &amp; Empire Management Sim Platform: Android (Kivy/Python) — Landscape Orientation

Developer: Solo
# 🌌 Gate Horizons

**A Turn-Based Space Exploration & Empire Management Sim**

*Humanity discovers an ancient jump gate network. You decide what happens next.*

---

## Canon & Lore Pack (Source of Truth)
Gate Horizons is a canon-owned setting for hard-sci strategy, narrative, and visual development. This repository is the **source of truth** for canon, aesthetics, and storyboard continuity across the project. Strategic traversal via gates/wormholes runs on months-scale timelines, while tactical missions are real-time in the Spaceship Sim layer. Refer to the canon pack for all lore, visuals, and prequel material:

- `canon/CANON.md`
- `canon/TIMELINE.md`
- `canon/STYLE_BIBLE.md`
- `canon/STORYBOARD.md`
- `canon/IMAGE_PROMPT_TEMPLATE.md`
- `canon/AI_AGENT_RULES.md`
- `lore/prequel_novella/CH01_The_Moon_That_Lied.md`

## Quick Start for Development

### Prerequisites
- Python 3.11+
- Kivy 2.3+
- Buildozer (for Android builds, Phase 2)

### Project Documents

| Document | Purpose |
|----------|---------|
| `PROJECT_PLAN.md` | Full game design document — vision, mechanics, systems, UI, balancing |
| `CLAUDE_CODE_PROMPT.md` | Step-by-step build instructions for Claude Code to execute |
| `CONTENT_GENERATION_PROMPTS.md` | LLM prompts for pre-generating all narrative content |

### Build Order (Phase 1 — Demo Slice)

1. **Set up project structure** and install dependencies
2. **Generate content** — Run prompts from CONTENT_GENERATION_PROMPTS.md to create JSON data files
3. **Build game engine** — Follow CLAUDE_CODE_PROMPT.md steps 1-8 (no UI)
4. **Test headless** — Run 10-turn simulation, verify all systems work
5. **Build Kivy UI** — Steps 9-12, starting with galaxy map
6. **Wire up & playtest** — Connect UI to game state, iterate

### Demo Slice Scope
- 12 star systems connected by jump gates
- 4 ship types (Scout, Freighter, Miner, Corvette)
- 5 resources (Energy, Metals, Exotics, Credits, Intel)
- Colony management with 8 infrastructure types (housing, industry, defense, research, spaceport, power, mining, logistics)
- Colony levels (Outpost -> Settlement -> Colony -> Hub City)
- Abstracted logistics network with latency-based trade routes
- Per-colony stockpiles with storage caps
- Colony founding (tech-gated) and upgrade mechanics
- World traits (Hub, Frontier, Mineral Rich, Volatile)
- Shortage penalties and stability system
- Auto-resolve combat with probability display
- 100+ pre-generated exploration events
- Tech tree with 24 unlocks (including Colonisation, Logistics I/II/III)
- Save/Load via SQLite
- Full turn processing loop with deterministic 5-phase resolution

### Architecture
```
MVC Pattern:
  game/    → Model + Controller (pure Python, no Kivy imports)
  ui/      → View (Kivy screens and widgets)
  data/    → Static game content (JSON)
  assets/  → Art and sound (placeholder → AI-generated)
```

## Two-layer Design (Meta vs Tactical)
Gate Horizons is the **meta game**: exploration, colonisation, logistics, research, factions, canon timeline, and encounter generation. It now ships with a **turn-based tactical hex combat MVP** for encounter resolution. The long-term plan still includes external integration with Flaxos Spaceship Sim (real‑time ship simulation), but Gate Horizons remains fully playable with the built-in tactical layer. The timescale separation is deliberate: Gate Horizons advances in weeks/months via gates/wormholes, while tactical missions unfold locally in short, discrete turns.

### Contract-only Integration (Non-negotiable)
Integration is **contract only** (used by the tactical MVP, encounter branching, and any external runtime):

- Gate Horizons outputs `EncounterSpec.json` (mission request).
- Spaceship Sim returns `ResultSpec.json` (mission outcomes).

There is no shared runtime logic, no direct ship control from Gate Horizons, and no tactical system ownership by Gate Horizons. Conversely, Spaceship Sim does not own factions, economy, or canon. The conceptual contract lives in `docs/ENCOUNTER_CONTRACT.md`.

### LLM Usage Guardrails
LLMs may assist with lore or encounter proposals **only** within canon constraints and after validation. Allowed usage:

- Drafting flavour text that cites canon sections.
- Proposing encounter outlines that fit the EncounterSpec template.

Disallowed usage:

- Introducing new technology or timeline changes without canon versioning.
- Bypassing the EncounterSpec/ResultSpec contract.
- Expanding tactical rules or ship systems (owned by Spaceship Sim).

Canon stability beats novelty. See `docs/CANON.md`, `docs/DRIFT_GUARDRAILS.md`, and `docs/AI_AGENT_RULES.md`.

### Key Design Decisions
- **Turn-based** — Mobile-friendly, battery-efficient, "one more turn" addictive
- **Kivy** — Native Android support via Buildozer, good touch handling
- **Pre-generated content** — No runtime API dependency, fully offline playable
- **Placeholder art** — Ship fast, swap in AI-generated art in Phase 3
- **Hard sci-fi tone** — Grounded, plausible, sense of wonder

---

## Colony Expansion & Logistics

**Not Factorio: abstracted logistics.** Resources flow as per-turn quantities, not individual items on belts.

### How Colony Logistics Works
- **Stockpiles**: Each colony has local storage for all 5 resources, with caps based on colony level and logistics infrastructure
- **Trade Routes**: Abstract links between colonies with `capacity_per_turn`, `latency_turns`, and `risk_factor`
- **In-Transit Queue**: Shipped goods take N turns to arrive (simulating distance)
- **Shortages**: If a colony can't cover its consumption, stability drops and growth halts

### Turn Resolution Order (Deterministic)
1. **Apply arrivals** from in-transit queue -> add to colony stockpiles
2. **Compute production** -> add to stockpiles (respect storage caps)
3. **Compute consumption/upkeep** -> subtract from stockpiles; record shortages
4. **Apply shortage penalties** -> stability/growth modifiers
5. **Compute trade flows** -> create in-transit shipments with latency

### Colony Levels
| Level | Name | Max Infra Slots | Storage Mult | Route Cap Mult |
|-------|------|-----------------|--------------|----------------|
| 0 | Outpost | 3 | 0.5x | 0.5x |
| 1 | Settlement | 5 | 1.0x | 1.0x |
| 2 | Colony | 7 | 1.5x | 1.5x |
| 3 | Hub City | 8 | 2.0x | 2.0x |

### Running the Headless Logistics Demo
```bash
python -m gate_horizons.tests.test_colony_logistics
```
This creates a Hub world + Frontier outpost, sets up a trade route with latency,
runs 30 turns, and prints the per-turn stockpile progression. Also runs the full
test suite for the logistics system.

### What is Implemented vs Future
**Implemented now**: Colony levels, stockpiles, storage caps, trade routes with
latency/capacity, shortage penalties, stability system, world traits (hub/frontier),
tech-gated colonisation, logistics infrastructure, tactical hex combat MVP, diplomacy
relations, encounter branching, 24-tech research tree, physical freighter routes,
shipyard production, procedural galaxy generation (seeded), 100+ exploration events,
gravity well system map, intra-system movement (no turn cost), zoom-threshold auto-level
switching, mini-map overlay, turn report summary screen, deterministic test saves, and
full headless test suite.

**Future (not implemented)**: Mini-map with sphere-of-influence overlay, piracy/trade
disruption events, diplomacy-based trade agreements.

---

## The Story

An asteroid in humanity's solar system turns out to be a dormant jump gate — part of an 
ancient intergalactic transit network built by a mysterious collective called The Convergence. 
The network was shut down 100,000 years ago for reasons humanity must discover.

As you reactivate gates and push into the unknown, you'll build colonies, establish trade 
routes, encounter alien civilizations, piece together the gate builders' story, and decide 
humanity's place in a galaxy that's been watching the stars far longer than we have.

---

*Built with Python, Kivy, and a lot of ambition.*
