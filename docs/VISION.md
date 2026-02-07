# Gate Horizons Vision

## Purpose
Gate Horizons is the **meta game**: the long-term, strategic layer that spans months of in‑world time. It owns exploration, colonisation, logistics, research, factions, canon timeline, and encounter generation. This document locks the long‑term direction so future work does not drift into tactical execution. 

Flaxos Spaceship Sim is the **tactical runtime**: real‑time, local, in‑system missions where ships are flown and systems are simulated. It owns ship control, RCS/Epstein drive behaviour, crew stations, and the moment‑to‑moment mission experience.

## Design Pillars
1. **Two-layer separation**
   - **Meta (Gate Horizons)**: strategic planning, weeks/months between star systems via gates/wormholes.
   - **Tactical (Spaceship Sim)**: real‑time missions inside a system, minutes/hours of play.
   - Timescale separation is deliberate: it lets the meta game focus on decisions and consequences, while the tactical runtime focuses on execution and skill.
2. **Contract‑only integration**
   - The only integration is a data contract: `EncounterSpec.json` sent to Spaceship Sim, and `ResultSpec.json` returned to Gate Horizons.
   - No shared runtime logic, no direct control of ship systems, and no cross‑layer state mutation beyond the contract.
3. **Canon stability beats novelty**
   - Lore, factions, and timeline constraints are fixed by CANON.md and updated via explicit versioning.
   - New content must align with canon and be validated before use.

## Player Loop (Long-term)
1. Discover systems via gates/wormholes (strategic time).
2. Decide on exploration, colonisation, and logistics priorities.
3. Generate an encounter request (EncounterSpec).
4. Resolve the mission in Spaceship Sim (tactical time).
5. Apply ResultSpec outcomes to the strategic state.
6. Advance time, update factions, economy, and research.

## Non-goals
- Gate Horizons does **not** control ship systems or real‑time mission execution.
- Spaceship Sim does **not** own factions, economy, or canon timeline.
- There is **no** shared AI director that bypasses the contract.

## Integration Contract Location
See `docs/ENCOUNTER_CONTRACT.md` for the conceptual contract between Gate Horizons and Spaceship Sim.
