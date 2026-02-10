# Gate Horizons Audit Report — Refactored for Next Attempt

## Snapshot
- Build health: ✅ compile + tests pass.
- Current quality state: stable baseline with architectural drift at UI action boundaries.
- Refactor objective: convert this from a raw issue dump into an execution-ready backlog.

## Prioritized backlog (next attempt)

| Priority | Area | Problem | Why it matters | Next action | Done when |
|---|---|---|---|---|---|
| P1 | Ship action dispatch | Galaxy/Fleet/System paths do not consistently route through shared controller APIs. | Behavior divergence and regression risk across screens. | Introduce/standardize a single action dispatch service in `GameState` and call it from all screens. | Same action from any screen hits same method and test proves parity. |
| P1 | Dead-end context actions | Context menu still exposes actions that only show “not implemented yet”. | Player trust and UX quality issue in core gameplay loop. | Hide unfinished actions or implement real handlers before exposing. | No dead-end action remains in ship context menus. |
| P1 | Direct UI state mutation | Some handlers mutate ship state directly (e.g., mining/stop). | Bypasses validation, logging, and side effects. | Replace direct mutations with controller commands only. | Screen code no longer edits model internals for orders. |
| P1 | System View parity | System View uses alternate action paths for gate activation / ship build. | Inconsistent rules and cost handling versus Galaxy Map flows. | Route to canonical `GameState` methods used elsewhere. | Gate/build logic matches across entrypoints and tests. |
| P2 | Input validation UX | Route manifest parse errors are swallowed silently. | Users can submit broken input without feedback. | Surface inline validation errors and block submit until valid. | Invalid input yields visible error and no silent failures. |
| P2 | Coupling cleanup | Fleet screen depends on GalaxyMap private methods. | Fragile screen-to-screen coupling. | Move shared behavior into public controller/service API. | No cross-screen private method calls for gameplay actions. |
| P2 | Balance guardrails | Logistics demo can collapse colony stability despite passing tests. | Misleading “green” status and poor tuning signal. | Add reserve rules/thresholds for demo manifests. | 30-turn demo avoids deterministic stability collapse. |

## Claude scorecard

| Dimension | Score | Notes |
|---|---:|---|
| Delivery speed | 9/10 | Large feature surface implemented quickly. |
| Functional coverage | 8/10 | Most major loops exist and run. |
| Architecture consistency | 6/10 | UI/controller boundaries need cleanup. |
| UX robustness | 6/10 | Some dead ends and silent validation failures. |
| Test discipline | 8/10 | Strong green suite, but parity cases should expand. |

**Overall: 7.4 / 10 (strong build momentum, needs consolidation pass).**

## Execution plan for next pass
1. **Unify dispatch layer** (highest leverage).
2. **Remove dead-end actions** from menus.
3. **Refactor direct mutation handlers** into controller commands.
4. **Add parity tests** for Galaxy Map vs Fleet vs System View action paths.
5. **Polish validation UX** in Trade screen.
6. **Re-run full suite** and document deltas in this file.

## Validation commands
- `python -m compileall -q .`
- `pytest -q`
