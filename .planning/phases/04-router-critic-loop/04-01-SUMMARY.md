---
phase: 04-router-critic-loop
plan: "01"
subsystem: agent-nodes
tags: [routing, critic, multi-source, state, tdd]
dependency_graph:
  requires: [03-02-SUMMARY.md]
  provides: [route_subquestion, critic_node, synthesizer-multi-source, current_step]
  affects: [graph.py (Plan 04-02 wiring)]
tech_stack:
  added: [typing.Literal]
  patterns: [keyword-routing, critic-loop-node, tdd-red-green, multi-source-serialization]
key_files:
  created: [tests/test_router_critic_nodes.py]
  modified:
    - src/dataagent/agent/state.py
    - src/dataagent/agent/nodes.py
    - tests/test_state.py
decisions:
  - "route_subquestion uses keyword heuristic (deterministic, testable) with index guard — no LLM call needed for routing"
  - "critic_node always increments iterations+current_step regardless of verdict — hard cap enforcement delegated to Plan 02 conditional edge"
  - "Sufficiency convention: last finding source=critic exposes sufficient:bool — consumed by Plan 02 path_map"
  - "insuffisant checked before suffisant in raw.lower() to avoid substring false-positive"
  - "_serialize_findings extended (not rewritten) — stats_tool/viz_tool added, critic summarized"
metrics:
  duration_seconds: 966
  completed_date: "2026-06-13"
  tasks_completed: 3
  files_modified: 4
---

# Phase 4 Plan 01: Router & Critic Nodes Summary

**One-liner:** Keyword-based `route_subquestion` (Literal-typed), `critic_node` (flash, always increments iterations+current_step, exposes `sufficient` bool via finding), and multi-source `synthesizer` with png markdown image support.

## Tasks Completed

| Task | Name | Commit | Files |
|------|------|--------|-------|
| 1 | Ajouter current_step au state | bdf805c | state.py, test_state.py |
| 2 | route_subquestion + critic_node (TDD) | fc4e8a5 | nodes.py, test_router_critic_nodes.py |
| 3 | synthesizer multi-source | 5b2b602 | nodes.py |

## What Was Built

### `current_step: int` in AgentState
- Added after `max_iterations`, before `db`
- Initialized to `0` in `initial_state()`
- Docstring: "index de la sous-question courante dans plan[], avancé par le critic à chaque tour de boucle"

### `route_subquestion(state) -> Literal["sql_tool", "stats_tool", "viz_tool"]`
- Keyword-based routing on `state["plan"][state["current_step"]]`
- Stats keywords: `corr[eé]l|anomalie|aberrant|[eé]cart[- ]type|tendance`
- Viz keywords: `graphe|visualis|courbe|histogramme|chart|plot|diagramme`
- Index guard: empty plan or `current_step >= len(plan)` → `"sql_tool"` (no IndexError)
- Case-insensitive via `re.IGNORECASE`

### `critic_node(state) -> dict`
- Calls `flash_llm()` with short prompt asking for "SUFFISANT" or "INSUFFISANT"
- ALWAYS returns `iterations = state["iterations"] + 1` (D-04, D-06)
- ALWAYS returns `current_step = state["current_step"] + 1`
- Pushes `{"source": "critic", "sufficient": bool, "iteration": N}` into findings (reducer add)
- Parse: checks `"insuffisant"` before `"suffisant"` to avoid substring false-positive
- Unknown LLM response → `sufficient=False` (safe default)

### `_serialize_findings` extended (multi-source)
- `sql_tool`: unchanged behavior
- `stats_tool`: serializes `analysis` type + `value`/`anomalies` details
- `viz_tool`: serializes `png_path` + `[INCLURE dans le rapport: ![graphe](png_path)]` directive
- `critic` findings: summarized as `[Critic itération N: SUFFISANT/INSUFFISANT]`, not as data
- Unknown sources: raw dump

### `synthesizer_node` system prompt extended
- Instructions to cross sql+stats+viz sources
- Explicit directive: if viz_tool finding has `png_path`, INCLUDE `![graphe](png_path)` in report

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] Fixed substring false-positive in critic sufficiency parsing**
- **Found during:** Task 2 GREEN — `test_returns_finding_source_critic_insufficient` failed
- **Issue:** `"suffisant" in "insuffisant".lower()` evaluates to `True` → INSUFFISANT was parsed as sufficient=True
- **Fix:** Check `"insuffisant"` before `"suffisant"` in the conditional chain
- **Files modified:** `src/dataagent/agent/nodes.py`
- **Commit:** fc4e8a5

**2. [Rule 1 - Bug] Updated test_state.py field count (8→9)**
- **Found during:** Task 1 verification — `test_agent_state_has_exactly_8_fields` failed
- **Issue:** Test hardcoded 8 fields; adding `current_step` makes it 9
- **Fix:** Updated `_EXPECTED_FIELDS` set and test name; added `current_step==0` assertion
- **Files modified:** `tests/test_state.py`
- **Commit:** bdf805c

## Verification Results

```
pytest tests/ : 109 passed, 0 failed, 0 regressions
pytest tests/test_router_critic_nodes.py: 31 passed
nodes.py coverage (full suite): 90% (threshold: 80%)
route_subquestion return type: typing.Literal['sql_tool', 'stats_tool', 'viz_tool']
critic_node increments iterations: verified by test
```

## Known Stubs

None — all new functions are fully implemented.

## Self-Check: PASSED
