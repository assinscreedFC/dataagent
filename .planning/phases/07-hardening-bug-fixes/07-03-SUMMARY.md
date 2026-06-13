---
phase: 07-hardening-bug-fixes
plan: "03"
subsystem: llm
tags: [gemini, langchain, singleton, performance, python]

requires:
  - phase: 07-01
    provides: nodes.py with _as_text helper and schema injection

provides:
  - flash_llm() and pro_llm() as module-level singletons (lazy creation, _flash/_pro cache)
  - _reset_singletons() utility for test isolation
  - 5 identity/construction-count tests in test_llm_singletons.py

affects: [nodes, graph, tests that call flash_llm/pro_llm indirectly]

tech-stack:
  added: []
  patterns: [lazy singleton with global cache, _reset_singletons for test isolation]

key-files:
  created:
    - tests/test_llm_singletons.py
  modified:
    - src/dataagent/agent/llm.py

key-decisions:
  - "D-11: _flash/_pro module globals initialized to None; created on first call; returned on subsequent calls — avoids ~30 re-instantiations per run"
  - "Tests patch nodes.flash_llm (the function), not the cache — monkeypatching remains valid without any changes to tests"
  - "_reset_singletons() resets both globals to None — used in autouse fixture for test isolation without touching test monkeypatching approach"

patterns-established:
  - "Lazy singleton: global var = None; if var is None: var = construct(); return var"
  - "Test isolation for module singletons: autouse fixture calls _reset_singletons() before and after each test"

requirements-completed: [HARD-10]

duration: 5min
completed: 2026-06-13
---

# Phase 7 Plan 03: LLM Singletons Summary

**Module-level singleton cache for ChatGoogleGenerativeAI (_flash/_pro), eliminating ~30 re-instantiations per agent run**

## Performance

- **Duration:** ~5 min
- **Started:** 2026-06-13T18:22:00Z
- **Completed:** 2026-06-13T18:26:41Z
- **Tasks:** 1
- **Files modified:** 2

## Accomplishments

- Added `_flash: ChatGoogleGenerativeAI | None = None` and `_pro: ChatGoogleGenerativeAI | None = None` module-level cache variables in `llm.py`
- `flash_llm()` and `pro_llm()` now use `global _flash`/`global _pro` with lazy creation on first call
- `_reset_singletons()` helper resets both globals to None for test isolation
- 5 new tests asserting: same-object identity on two calls, single construction, and flash is not pro

## Task Commits

1. **Task 1: Singletons module-level flash_llm/pro_llm (HARD-10)** - `313afc5` (feat)

## Files Created/Modified

- `src/dataagent/agent/llm.py` - Added `_flash`/`_pro` module globals, lazy creation in `flash_llm()`/`pro_llm()`, `_reset_singletons()` helper
- `tests/test_llm_singletons.py` - 5 singleton identity tests with ChatGoogleGenerativeAI patched via unittest.mock

## Decisions Made

- Lazy creation on first call (not at import time) preserves the existing fail-fast behavior for missing API keys and keeps config readable once
- `_reset_singletons()` rather than exposing the globals directly — cleaner test API
- Tests use `unittest.mock.patch` on `dataagent.agent.llm.ChatGoogleGenerativeAI` and an `autouse` fixture calling `_reset_singletons()` before/after each test

## Deviations from Plan

None - plan executed exactly as written.

## Issues Encountered

None. The 3 pre-existing test failures (test_critic_decision_reloop_when_insufficient, test_critic_decision_no_findings_reloops, test_current_step_increments_from_nonzero) remain from 07-01 work and are expected to be fixed in 07-04.

## User Setup Required

None - no external service configuration required.

## Next Phase Readiness

- `llm.py` singleton ready; 07-04 (blind-spot tests) can proceed
- All 3 known pre-existing failures still isolated to critic_loop / router_critic_nodes tests from 07-01 work

---
*Phase: 07-hardening-bug-fixes*
*Completed: 2026-06-13*
