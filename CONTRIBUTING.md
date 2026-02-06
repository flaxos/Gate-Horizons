# Contributing to Gate Horizons

This document exists because **automated code agents have repeatedly broken the
game** by making partial or inconsistent changes. Every rule below comes from a
real crash. Follow them or the game will break.

---

## Quick Reference — Mandatory Checks

Before merging ANY change, run:

```bash
python -m pytest gate_horizons/tests/ -v
python -m gate_horizons.tests.test_harness
```

Both must pass. No exceptions.

---

## 1. Package Structure

```
gate_horizons/            <-- TOP-LEVEL PACKAGE
├── __init__.py
├── __main__.py           <-- imports main.py (requires Kivy)
├── main.py               <-- Kivy app entry point
├── game/                 <-- Pure Python game engine (NO Kivy imports)
│   ├── state.py          <-- GameState (master state container)
│   ├── clock.py          <-- GameClock (turn idempotency)
│   ├── turn.py           <-- TurnProcessor (12-step pipeline)
│   ├── galaxy.py
│   ├── ships.py
│   ├── resources.py
│   ├── colonies.py
│   ├── trade.py
│   ├── combat.py
│   ├── events.py
│   ├── tech.py
│   └── save_load.py
├── ui/                   <-- Kivy UI layer
│   ├── screens/
│   └── widgets/
├── data/                 <-- Static JSON data files
└── tests/                <-- Unit and integration tests
```

### The Separation Rule

- `game/` modules must NEVER import from `kivy` or `ui/`.
- `ui/` modules may import from `game/` using **absolute imports only**.
- `tests/` must work without Kivy installed (skip UI tests gracefully).

---

## 2. Import Rules — THE #1 SOURCE OF CRASHES

### ALWAYS use absolute imports for cross-package references

```python
# CORRECT — absolute import
from gate_horizons.game.colonies import INFRASTRUCTURE_TYPES

# WRONG — bare import (only works if cwd is gate_horizons/)
from game.colonies import INFRASTRUCTURE_TYPES

# WRONG — triple-dot relative that escapes the package
from ...game.colonies import INFRASTRUCTURE_TYPES
```

### Within the same sub-package, single-dot relative is OK

```python
# CORRECT — within game/ package
from .clock import GameClock
from .galaxy import GalaxyMap

# CORRECT — within ui/screens/ referencing ui/widgets/
from ..widgets.resource_bar import TopBar
```

### NEVER use relative imports that go more than 2 levels up

The `...` (triple-dot) prefix goes 3 levels up from the current file. For a
file in `ui/screens/`, that goes ABOVE `gate_horizons/` and causes
`ImportError`. This exact bug has crashed the game twice (PR #6, PR #8).

---

## 3. Data File Loading — Traversable Paths

All data files are loaded via `importlib.resources`:

```python
from importlib import resources
path = resources.files("gate_horizons").joinpath("data", "ships.json")
```

This returns a `Traversable` object, NOT a plain string. Every `load_from_json`
or `load_templates` method MUST handle both:

```python
from importlib.resources.abc import Traversable
from typing import Union

def load_from_json(self, filepath: Union[str, Traversable]) -> None:
    if hasattr(filepath, "read_text"):
        data = json.loads(filepath.read_text(encoding="utf-8"))
    else:
        with open(filepath, "r", encoding="utf-8") as f:
            data = json.load(f)
```

**This exact pattern is already used in:** `galaxy.py`, `tech.py`, `events.py`,
`ships.py`. If you add a new data loader, copy this pattern.

Failure to handle `Traversable` will work on desktop but **crash on Android**.

---

## 4. Serialization — from_dict() Safety

### ALWAYS filter dict keys in from_dict()

Save files may contain keys from newer or older versions. If `from_dict()`
passes unknown keys as `**kwargs` to `__init__()`, it crashes with `TypeError`.

```python
# CORRECT — filter to known fields
_INIT_FIELDS = {"id", "name", "cost", "effect"}

@classmethod
def from_dict(cls, data: dict) -> "MyClass":
    return cls(**{k: v for k, v in data.items() if k in cls._INIT_FIELDS})

# WRONG — crashes if save data has extra keys
@classmethod
def from_dict(cls, data: dict) -> "MyClass":
    return cls(**data)
```

For dataclasses, you can use `cls.__dataclass_fields__` instead of a manual set.

### ALWAYS update `_INIT_FIELDS` when adding constructor parameters

If you add a new parameter to `__init__()`, you MUST also add it to
`_INIT_FIELDS` (or `to_dict`/`from_dict`). Otherwise the field won't
round-trip through save/load.

---

## 5. Turn Processing — The Clock Guard Pattern

The `GameClock` prevents duplicate processing of subsystems within a single
turn. Every step in `TurnProcessor.process_turn()` is guarded:

```python
if clock.mark_processed("subsystem_name"):
    self._process_subsystem(game_state, report)
```

Per-entity processing uses a second argument:

```python
if not game_state.game_clock.mark_processed("movements", ship.id):
    continue
```

### When adding a new turn processing step:

1. Add a `clock.mark_processed("your_step_name")` guard
2. Wire any tech effects from `game_state.tech.get_effects()`
3. Test with the 10-turn harness: `python -m gate_horizons.tests.test_harness`

**This exact bug happened in PR #10:** GameClock was added but `fuel_efficiency`
tech effect was not wired into movement processing.

---

## 6. Schema Versioning

`GameState.to_dict()` includes `"schema_version": CURRENT_SCHEMA_VERSION`.

When changing `GameState` structure:
1. Increment `CURRENT_SCHEMA_VERSION` in `state.py`
2. Add migration logic in `from_dict()` for the new version
3. Ensure old saves still load (test with `test_save_load_roundtrip.py`)

---

## 7. Testing Rules

### Tests must not require Kivy

The `game/` tests run in headless CI without Kivy. If a test needs to import
a module that depends on Kivy (like `__main__.py`), wrap it:

```python
try:
    module = importlib.import_module("gate_horizons.__main__")
except ImportError:
    self.skipTest("Kivy not installed")
```

### Run the full test suite before every PR

```bash
# Unit tests
python -m pytest gate_horizons/tests/ -v

# Integration test (10-turn headless simulation)
python -m gate_horizons.tests.test_harness
```

---

## 8. Common Mistakes That Have Crashed the Game

| Mistake | PR | Result |
|---------|-----|--------|
| Triple-dot relative import (`from ...game.X`) | #6 | `ImportError` on startup |
| Fixing only one symptom, not the root cause | #7 | Crash persisted |
| Adding new system without wiring tech effects | #10 | Research had no effect |
| Using `open()` on `Traversable` without check | #11 | Platform-dependent crash |
| `from_dict(**data)` without filtering keys | Multiple | `TypeError` on load |
| Test importing Kivy in headless environment | #11 | Test suite always fails |

---

## 9. Checklist for Code Changes

- [ ] All imports are absolute (`gate_horizons.X`) or single-dot relative within the same sub-package
- [ ] Data loaders handle both `str` and `Traversable` paths
- [ ] `from_dict()` filters dict keys to `_INIT_FIELDS`
- [ ] New turn processing steps are guarded by `clock.mark_processed()`
- [ ] New turn processing steps wire in relevant tech effects
- [ ] `python -m pytest gate_horizons/tests/ -v` passes (all tests green or skipped)
- [ ] `python -m gate_horizons.tests.test_harness` completes successfully
- [ ] No `kivy` imports in `game/` modules
- [ ] No tests that require Kivy without a skip guard
