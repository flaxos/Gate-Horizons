# Gate Horizons — Content Generation Prompts

## Purpose
Use these prompts with Claude to pre-generate all narrative content for the game.
Output should be valid JSON files saved to the data/events/ directory.

---

## PROMPT 1: Exploration Events (50 total)

```
You are a content writer for a hard sci-fi turn-based strategy game called "Gate Horizons." 
Humanity has discovered that a dormant asteroid in Sol is actually a disabled jump gate — part 
of an ancient intergalactic transit network. Players explore the galaxy through these gates.

Generate 50 exploration events as a JSON array. Each event represents something a scout or 
survey ship might encounter while exploring a new star system.

TONE: Hard sci-fi, grounded, sense of wonder. Think Expanse meets Stellaris. No fantasy, no 
magic. Technology should feel plausible even when alien. Maintain a sense that space is vast, 
dangerous, and full of mysteries.

STRUCTURE for each event:
{
  "id": "exp_XXX",  // sequential numbering
  "title": "Short evocative title",
  "description": "2-4 sentences describing what the ship encounters. Written in second person 
    ('Your scout detects...'). Include sensory details and tactical information.",
  "requirements": {
    "ship_class": "scout",  // or "any", "miner", "corvette"
    "system_surveyed": false,  // or true, or omit if no requirement
    "min_tier": 3,  // minimum system tier (3=frontier, 2=developing)
    "tech_required": null  // or a tech ID like "deep_scan"
  },
  "choices": [
    {
      "text": "Short action description (player-facing, imperative)",
      "outcomes": [
        {
          "probability": 0.6,  // probabilities in a choice must sum to 1.0
          "result": "success",  // success, partial, failure, or critical
          "description": "2-3 sentences describing what happens.",
          "rewards": {"exotics": 5, "intel": 8},  // resources gained
          "costs": {}  // or {"hull_damage": 10}, {"fuel_cost": 2}, {"morale_loss": 5}
        }
      ]
    }
  ],
  "tags": ["anomaly", "alien_tech"],  // for filtering: anomaly, derelict, alien_tech, 
    // natural_phenomenon, signal, ruins, biological, hazard, resource_deposit, mystery
  "tier_requirement": 3,
  "one_time": true,  // false for events that can repeat
  "weight": 1.0  // relative probability of being selected (0.5 = half as likely)
}

VARIETY REQUIREMENTS:
- At least 10 events involving ancient alien technology/ruins
- At least 8 events involving natural space phenomena (pulsars, nebulae, rogue planets)
- At least 5 events involving biological discoveries (alien life, ecosystems)
- At least 5 events involving signals or transmissions
- At least 5 events involving derelict ships or stations
- At least 5 events involving resource discoveries
- At least 5 hazardous/dangerous events
- At least 3 events that hint at the gate builders' story
- Mix of one-time and repeatable events
- Each event should have 2-4 choices with 2-3 outcomes each
- Risk/reward should scale — cautious choices are safer but less rewarding

RESOURCE REWARDS GUIDELINES:
- Small: 1-5 of any resource
- Medium: 5-15 of any resource
- Large: 15-30 (rare, high-risk only)
- Intel is the most valuable for progression
- Exotics are rare and should feel special
- Hull damage ranges: minor (5-10), moderate (15-25), severe (30+)

Output ONLY the JSON array, no other text.
```

---

## PROMPT 2: Colony Events (30 total)

```
Generate 30 colony events for "Gate Horizons." These events occur at established colonies 
(Level 1 and Level 2 worlds). They represent the social, political, and economic challenges 
of managing human settlements in distant star systems.

Same JSON structure as exploration events, but with colony-specific requirements:

"requirements": {
  "colony_tier": 2,  // minimum colony tier
  "min_population": 1000,  // or null
  "infrastructure_requirement": {"industry": 2},  // specific infrastructure needed, or null
  "has_trade_route": true  // or false, or null
}

CATEGORIES (mix these):
- Labor/workforce issues (strikes, skilled worker shortages, automation debates)
- Political events (governance disputes, independence movements, elections)
- Social events (cultural festivals, crime waves, immigration waves)
- Economic events (market crashes, resource booms, trade opportunities)
- Environmental events (terraforming setbacks, ecological discoveries, weather systems)
- Infrastructure events (system failures, upgrade opportunities, sabotage)
- Population events (disease outbreaks, baby booms, refugee arrivals)
- External threats (pirate sightings, alien diplomats, mysterious visitors)

TONE: Focus on the human element. These should feel like the messy, complicated reality 
of building civilization among the stars. Reference the challenges of isolation, supply 
dependencies, cultural identity far from Earth.

Choices should often involve tradeoffs between:
- Short-term vs long-term benefit
- Individual rights vs collective safety
- Economic growth vs sustainability
- Autonomy vs central control

Rewards/costs can include: population changes, happiness changes, resource bonuses/losses,
infrastructure damage/upgrades, special unlocks.

Output ONLY the JSON array, no other text.
```

---

## PROMPT 3: Encounter Narratives (40 total)

```
Generate 40 encounter narratives for "Gate Horizons." These describe situations where player 
ships encounter other entities — hostile, neutral, or friendly.

Structure:
{
  "id": "enc_XXX",
  "type": "combat",  // combat, evasion, diplomacy, salvage, trade
  "title": "Short title",
  "description": "2-4 sentences setting the scene. Second person.",
  "enemy_type": "pirate_raiders",  // pirate_raiders, alien_patrol, rogue_ai, natural_hazard,
    // merchant_convoy, alien_trader, research_vessel, refugee_fleet, ancient_guardian
  "difficulty": 3,  // 1-5 scale, affects combat power needed
  "choices": [
    {
      "text": "Engage the hostiles",
      "type": "combat",  // combat triggers auto-resolve or tactical mode
      "difficulty_modifier": 0,  // adjusts difficulty for this specific choice
      "outcomes": { /* same structure as exploration events */ }
    },
    {
      "text": "Attempt to negotiate",
      "type": "diplomacy",
      "skill_check": "xenology",  // tech branch that gives bonus
      "outcomes": { /* ... */ }
    },
    {
      "text": "Try to slip away undetected",
      "type": "evasion",
      "skill_check": "sensors",
      "outcomes": { /* ... */ }
    }
  ],
  "tags": ["hostile", "pirate"],
  "tier_requirement": 3,
  "location_type": "any",  // or "asteroid_field", "near_gate", "deep_space", "near_colony"
  "one_time": false,
  "weight": 1.0
}

ENCOUNTER VARIETY:
- 12 combat encounters (pirates, hostile aliens, automated defenses)
- 8 diplomacy encounters (alien traders, emissaries, stranded travelers)
- 6 evasion encounters (overwhelming forces, natural hazards to navigate)
- 8 salvage encounters (derelicts, wreckage fields, abandoned cargo)
- 6 trade encounters (merchant convoys, black market dealers, alien bazaars)

IMPORTANT:
- Every encounter should have at least one non-combat option
- Difficulty should scale appropriately for the scenario
- Trade encounters can offer rare resources at credit costs
- Diplomacy encounters should hint at the larger galactic community
- Some encounters should be recurring (pirates respawn, traders revisit)

Output ONLY the JSON array, no other text.
```

---

## PROMPT 4: Gate Builder Lore Fragments (20 total)

```
Generate 20 lore fragments for "Gate Horizons" that gradually reveal the story of the 
ancient civilization that built the intergalactic gate network.

THE META-NARRATIVE (for your reference, players discover this piece by piece):
The gate builders were a collective of multiple species called "The Convergence" — they 
believed that connecting all intelligent life across the galaxy was a moral imperative. 
They built the gate network over millions of years. The network was shut down approximately 
100,000 years ago when a faction within The Convergence discovered that the gates were 
slowly destabilizing the fabric of spacetime. A civil war erupted between those who wanted 
to repair the network and those who wanted to shut it down permanently. The shutdown faction 
won, but at great cost — most of The Convergence's knowledge was lost. Some gates were 
disabled, others destroyed, a few hidden. The gates humanity found were among those that 
were merely disabled — a compromise by the shutdown faction who couldn't bring themselves 
to destroy everything. Some members of The Convergence may still exist in diminished form.

STRUCTURE:
{
  "id": "lore_XXX",
  "title": "Fragment title",
  "text": "3-6 sentences of the lore itself, written as if translated from alien records, 
    archaeological analysis, or decoded transmissions. Should feel ancient, significant, 
    and slightly mysterious.",
  "discovery_context": "Where/how this fragment is found: 'Decoded from derelict station 
    data core', 'Inscribed on gate mechanism housing', etc.",
  "narrative_order": 1,  // 1-20, the intended order of revelation
  "requirements": {
    "min_systems_explored": 3,  // how much of the map must be explored
    "tech_required": null  // or specific tech needed to decode
  },
  "tags": ["gate_builders", "history"]
}

PACING:
- Fragments 1-5: Hints that the gates are artificial, built by someone
- Fragments 6-10: Evidence of a vast civilization, multiple species working together
- Fragments 11-15: Signs of conflict, debate, something went wrong
- Fragments 16-18: The truth about spacetime destabilization
- Fragments 19-20: The shutdown, the compromise, the lingering presence

Each fragment should feel like a genuine archaeological discovery. Use specific but 
alien-sounding terminology. Reference physical artifacts, data patterns, and architectural 
details rather than exposition dumps.

Output ONLY the JSON array, no other text.
```

---

## PROMPT 5: Planet Descriptions (30 total)

```
Generate 30 planet descriptions for "Gate Horizons" as a JSON array.

Structure:
{
  "id": "planet_XXX",
  "name": "Planet name (realistic astronomical naming + common name)",
  "type": "rocky",  // rocky, gas_giant, ice, volcanic, oceanic, barren, desert, toxic, garden
  "description": "2-3 sentences. Hard sci-fi. Include key physical characteristics, 
    atmosphere composition, notable features.",
  "resource_potential": {
    "metals": 3,  // 0-5 scale
    "energy": 2,
    "exotics": 0
  },
  "colonizable": true,
  "colonization_difficulty": 3,  // 1-5, affects setup cost
  "flavor_text": "One evocative sentence a survey officer might include in their report.",
  "hazards": ["radiation", "seismic"],  // or empty. Options: radiation, seismic, toxic_atmo,
    // extreme_temp, low_gravity, storms, volcanic, biological
  "points_of_interest": ["ancient_ruins", "mineral_deposits"]  // optional unique features
}

REQUIREMENTS:
- 8 rocky planets (varied — Mars-like to Mercury-like)
- 5 gas giants (resource-rich moons and atmospheres)
- 4 ice worlds (some with subsurface oceans)
- 3 volcanic (dangerous but exotic-rich)
- 3 oceanic (highly colonizable)
- 2 garden worlds (rare, Earth-like, major prizes)
- 3 barren/desert (challenging but mineral-rich)
- 2 toxic (extreme hazards, unique resources)

Names should mix real astronomical conventions (catalog numbers, Greek letters) 
with evocative common names that colonists might give them.

Output ONLY the JSON array, no other text.
```

---

## PROMPT 6: Alien Faction Profiles (5 total)

```
Generate 5 alien faction profiles for "Gate Horizons." These are civilizations humanity 
encounters through the gate network. Some are also newcomers to the network; others have 
been using it longer.

Structure:
{
  "id": "faction_XXX",
  "name": "Faction name",
  "species_name": "Species name",
  "description": "3-5 sentences describing the faction — their biology (briefly), 
    culture, government, and relationship to the gate network.",
  "disposition_to_humans": "curious",  // hostile, suspicious, curious, neutral, friendly
  "traits": ["traders", "territorial"],  // 2-4 traits from: traders, expansionist, 
    // isolationist, territorial, scientific, spiritual, militant, diplomatic, 
    // nomadic, ancient, newcomer, industrial, ecological
  "technology_level": "comparable",  // primitive, comparable, advanced, vastly_superior
  "gate_network_status": "active_user",  // newcomer, active_user, ancient_user, builder_remnant
  "trade_specialties": ["exotics", "intel"],  // what they're willing to trade
  "diplomatic_style": "2-3 sentences on how they negotiate and what they value.",
  "conflict_triggers": ["territorial_expansion"],  // what makes them hostile
  "lore_connection": "How they relate to the gate builder narrative",
  "first_contact_event_hint": "Brief description of how humanity first encounters them"
}

FACTION VARIETY (one of each archetype):
1. Traders/Merchants — friendly, wants commerce, useful early contact
2. Territorial Empire — suspicious, controls several systems, potential rival
3. Scientific Collective — curious about humans, values knowledge exchange
4. Nomadic Fleet — no fixed territory, moves through gate network, unpredictable
5. Ancient Remnant — connected to gate builders, vastly advanced but diminished, mysterious

Each should feel genuinely alien — not just "humans with funny faces." 
Their motivations, communication styles, and values should reflect non-human perspectives.

Output ONLY the JSON array, no other text.
```

---

## USAGE INSTRUCTIONS

1. Run each prompt separately through Claude
2. Save outputs to the corresponding files in data/events/ and data/
3. Validate JSON syntax after generation
4. Review for consistency — faction names referenced in events should match faction profiles
5. Adjust difficulty numbers and resource rewards based on playtesting
6. Content can be regenerated/expanded later with follow-up prompts
