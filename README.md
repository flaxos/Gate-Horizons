# Gate-Horizons
Genre: Turn-Based Space Exploration &amp; Empire Management Sim Platform: Android (Kivy/Python) — Landscape Orientation

Developer: Solo
# 🌌 Gate Horizons

**A Turn-Based Space Exploration & Empire Management Sim**

*Humanity discovers an ancient jump gate network. You decide what happens next.*

---

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
- Colony management with 5 infrastructure types
- Trade routes between systems
- Auto-resolve combat with probability display
- Pre-generated narrative events
- Basic tech tree (10 unlocks)
- Save/Load via SQLite
- Full turn processing loop

### Architecture
```
MVC Pattern:
  game/    → Model + Controller (pure Python, no Kivy imports)
  ui/      → View (Kivy screens and widgets)
  data/    → Static game content (JSON)
  assets/  → Art and sound (placeholder → AI-generated)
```

### Key Design Decisions
- **Turn-based** — Mobile-friendly, battery-efficient, "one more turn" addictive
- **Kivy** — Native Android support via Buildozer, good touch handling
- **Pre-generated content** — No runtime API dependency, fully offline playable
- **Placeholder art** — Ship fast, swap in AI-generated art in Phase 3
- **Hard sci-fi tone** — Grounded, plausible, sense of wonder

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
