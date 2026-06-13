---
phase: 07-hardening-bug-fixes
plan: "04"
subsystem: testing
tags: [pytest, coverage, blind-spots, cli, critic-loop, hardening]

dependency_graph:
  requires:
    - phase: 07-hardening-bug-fixes
      provides: [D-01-bound-current-step, D-02-early-exit-critic, D-03-summarize-findings, D-04-write-guard, D-07-html-escape, D-11-llm-singletons]
  provides:
    - test_cli.py covering __main__.main() CLI
    - exec-failure SQL test (EXPLAIN passes, conn.execute raise → retry → error finding)
    - stats/viz except-guard tests (arity mismatch → no crash)
    - planner empty/whitespace fallback test
    - write-guard test (DROP rejected, table intact)
    - D-01/D-02 updated stale tests (plan+current_step added to states)
    - D-03 critic content summary tests
    - D-02 early-exit tests
  affects: [future test additions, coverage baseline]

tech-stack:
  added: []
  patterns: [proxy-wrapper-for-readonly-ctype-attrs, capturing-LLM-for-prompt-inspection]

key-files:
  created:
    - tests/test_cli.py
  modified:
    - tests/test_critic_loop.py
    - tests/test_router_critic_nodes.py
    - tests/test_nodes.py

key-decisions:
  - "D-13: DuckDB execute is read-only (C extension) → wrap conn in proxy class instead of monkeypatching"
  - "D-13: Stale tests fixed by adding plan+current_step to test states, not weakening production code"
  - "D-13: CLI test patches dataagent.agent.graph.run (deferred import) not __main__.run"

patterns-established:
  - "Proxy wrapper pattern: wrap C-extension objects in Python class to simulate failures"
  - "Capturing LLM: _CapturingLLM records messages to verify prompt content in assertions"
  - "CLI test: monkeypatch sys.argv + monkeypatch graph.run + capsys for output capture"

requirements-completed: [HARD-12]

duration: 35min
completed: "2026-06-13"
---

# Phase 7 Plan 04: Blind Spots + Fix Expected Failures + Coverage Summary

**94% global coverage (up from 88%), 248 tests GREEN — 3 stale tests fixed for D-01/D-02, CLI tests added (0%→97%), exec-failure/stats-viz-guard/planner-empty/write-guard/critic-content blind spots covered**

## Performance

- **Duration:** ~35 min
- **Started:** 2026-06-13T18:30:00Z
- **Completed:** 2026-06-13T19:05:00Z
- **Tasks:** 3 committed tasks
- **Files modified:** 5

## Accomplishments

- Fixed 3 stale tests that were expected failures since plan 07-01 (D-01/D-02 behavior changes)
- Created `tests/test_cli.py` (6 tests): `__main__.main()` coverage went from 0% to 97%
- Added 20+ new blind-spot tests: exec-failure-after-EXPLAIN, stats/viz arity-mismatch guards, planner whitespace fallback, write-guard (DROP rejected), D-03 critic content summary, D-02 early-exit, D-01 current_step bound
- Global coverage: 88% → 94% (target was ≥85%)
- Suite: 248 passed, 0 failures, 0 regressions

## Task Commits

1. **Task 1: Fix 3 expected failures D-01/D-02** - `c6e0e22` (test)
2. **Task 2: Add test_cli.py CLI coverage** - `8e71524` (test)
3. **Task 3: Add blind-spot tests (nodes, router_critic, critic_loop)** - `8a37f6d` (test)

## Files Created/Modified

- `tests/test_cli.py` - New: 6 CLI tests for `__main__.main()` (valid, missing-arg, missing-key, run-raise, debug, google-key)
- `tests/test_nodes.py` - Added: planner-empty, exec-failure via proxy wrapper, stats/viz arity-mismatch guards, write-guard, critic-content summary
- `tests/test_router_critic_nodes.py` - Fixed: `test_current_step_increments_from_nonzero` (D-01 bound assertion); Added: D-01 bound tests, D-02 early-exit tests, D-03 critic content tests
- `tests/test_critic_loop.py` - Fixed: `test_critic_decision_reloop_when_insufficient`, `test_critic_decision_no_findings_reloops` (added plan+current_step); Added: hard-cap precedence test, D-02 early-exit test

## Coverage Report (final)

```
Name                                       Stmts   Miss  Cover
---------------------------------------------------------------
src\dataagent\__init__.py                      1      0   100%
src\dataagent\__main__.py                     32      1    97%
src\dataagent\agent\graph.py                  72      2    97%
src\dataagent\agent\llm.py                    16      0   100%
src\dataagent\agent\nodes.py                 299     27    91%
src\dataagent\agent\schema_introspect.py      11      0   100%
src\dataagent\agent\state.py                  19      0   100%
src\dataagent\agent\stats.py                  32      2    94%
src\dataagent\agent\viz.py                    24      0   100%
src\dataagent\api.py                          28      5    82%
src\dataagent\config.py                       14      0   100%
src\dataagent\data\loader.py                  27      0   100%
src\dataagent\data\queries.py                 18      0   100%
src\dataagent\eval\runner.py                  21      0   100%
src\dataagent\render.py                       24      0   100%
---------------------------------------------------------------
TOTAL                                        639     37    94%
```

## Decisions Made

- **D-13a:** DuckDB `execute` is a read-only C-extension attribute — cannot be monkeypatched. Used a Python proxy wrapper class (`_FailingConn`) that delegates EXPLAIN to real conn but raises on data execution. This is the correct pattern for testing failures in C-extension objects.
- **D-13b:** Stale tests fixed by adding `plan` and `current_step` fields to test states, not by weakening production code. The production logic (D-01/D-02) is correct.
- **D-13c:** CLI import is deferred in `main()` (`from dataagent.agent.graph import run`). Tests must patch `dataagent.agent.graph.run`, not `dataagent.__main__.run`.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] DuckDB execute read-only — monkeypatch approach replaced by proxy wrapper**
- **Found during:** Task 3 (exec-failure test)
- **Issue:** `monkeypatch.setattr(conn, "execute", ...)` raises `AttributeError: '_duckdb.DuckDBPyConnection' object attribute 'execute' is read-only`
- **Fix:** Implemented `_FailingConn` proxy class that wraps the real conn, passes EXPLAIN through, raises on data execution
- **Files modified:** tests/test_nodes.py
- **Verification:** Test passes, DuckDB conn untouched
- **Committed in:** 8a37f6d

---

**Total deviations:** 1 auto-fixed (Rule 1 — bug in test approach)
**Impact on plan:** Minor implementation change, goal achieved identically.

## Issues Encountered

None beyond the monkeypatch/read-only DuckDB attribute (handled via proxy wrapper above).

## Known Stubs

None — all tests wire real production code. No placeholders.

## Threat Surface Scan

No new network endpoints, auth paths, file access patterns, or schema changes. Tests only.

## Next Phase Readiness

- Phase 07 hardening complete (4/4 plans done)
- All 248 tests GREEN, 94% coverage
- Production code unchanged in this plan (tests only)
- Project ready for v1.1 milestone close

## Self-Check: PASSED

- `tests/test_cli.py` exists: FOUND
- `tests/test_nodes.py` has blind-spot tests: FOUND
- Commits c6e0e22, 8e71524, 8a37f6d: VERIFIED via git log
- 248 passed, 0 failures: VERIFIED
- Coverage 94% ≥ 85%: VERIFIED
