---
phase: 02-sql-tool-hardening
plan: "01"
subsystem: sql_tool_node
tags: [hardening, validation, retry, duckdb, tdd]
dependency_graph:
  requires: [01-03]
  provides: [TOOL-01]
  affects: [sql_tool_node, findings]
tech_stack:
  added: []
  patterns:
    - EXPLAIN-based SQL validation before execution
    - Bounded retry loop with LLM re-prompting on error
    - TDD (RED -> GREEN) for retry and exhaustion scenarios
key_files:
  created: []
  modified:
    - src/dataagent/config.py
    - src/dataagent/agent/nodes.py
    - tests/test_nodes.py
decisions:
  - "SQL_MAX_RETRIES=2 in config.py distinct from MAX_ITERATIONS (D-03)"
  - "EXPLAIN used for pre-execution validation (D-01/D-02) — no manual schema check"
  - "_SequenceLLM test helper for retry scenario simulation"
metrics:
  duration_minutes: 10
  completed_date: "2026-06-13"
  tasks_completed: 3
  files_modified: 3
---

# Phase 02 Plan 01: SQL Tool Hardening Summary

**One-liner:** EXPLAIN-based SQL validation + bounded retry loop (SQL_MAX_RETRIES=2) with LLM re-prompting on DuckDB error, enriching findings with `attempts` key.

## Tasks Completed

| Task | Name | Commit | Files |
|------|------|--------|-------|
| 1 | SQL_MAX_RETRIES + _validate_sql helper | bdf4934 | config.py, nodes.py |
| 2 (RED) | Failing tests for validation + retry | 3669a23 | tests/test_nodes.py |
| 2 (GREEN) | _execute_subquestion with EXPLAIN + retry | feb914f | nodes.py |
| 3 | E2E node recovery test + column rejection | 4aecb6a | tests/test_nodes.py |

## What Was Built

### `src/dataagent/config.py`
- Added `SQL_MAX_RETRIES = 2` — intra-tool retry guard, distinct from `MAX_ITERATIONS` (critic loop).

### `src/dataagent/agent/nodes.py`
- `_validate_sql(conn, sql) -> str | None`: runs `EXPLAIN <sql>` against DuckDB catalogue. Returns `None` if valid, the DuckDB error message string if invalid. Never raises.
- `_generate_sql(schema, subquestion) -> str`: extracted from old `_execute_subquestion` (initial SQL generation via Flash LLM).
- `_regenerate_sql(schema, subquestion, bad_sql, error) -> str`: re-prompts Flash LLM with the faulty query + exact DuckDB error + schema to get a corrected query.
- `_execute_subquestion` refactored: bounded loop `range(1, SQL_MAX_RETRIES + 2)`, EXPLAIN validation before each execution, retry with re-prompting on failure, exhaustion produces error finding without crash.
- Finding format extended: success findings now include `attempts` key (D-06). Error findings include `attempts` key.

### `tests/test_nodes.py`
- `_SequenceLLM`: test helper that returns contents from a list in sequence (enables simulation of bad-then-good LLM responses).
- `test_sql_tool_retries_and_corrects`: bad SQL then correct SQL → `attempts == 2`, success finding.
- `test_sql_tool_valid_first_try_attempts_one`: valid SQL first try → `attempts == 1`, Phase 1 format preserved.
- `test_sql_tool_exhausts_retries_pushes_error`: always-bad SQL → error finding, `attempts == SQL_MAX_RETRIES + 1`, no exception.
- `test_sql_tool_node_recovers_from_failed_initial_sql`: E2E node-level proof that failed initial SQL still produces correct finding (success criterion #4).
- `test_validate_sql_rejects_unknown_column`: EXPLAIN rejects unknown column before execution (success criterion #1, column-level).

## Verification Results

- Critère #1 (rejet avant exec): `_validate_sql` returns error str for unknown table AND unknown column.
- Critère #2 (retry ≥1 avec query corrigée): `test_sql_tool_retries_and_corrects` → `attempts == 2`, finding succès.
- Critère #3 (résultat valide avec source): finding succès porte `source`/`sql`/`tables`/`rows`/`columns`/`attempts`.
- Critère #4 (SQL initial fail → finding correct): `test_sql_tool_node_recovers_from_failed_initial_sql`.
- D-05 (épuisement sans crash): `test_sql_tool_exhausts_retries_pushes_error`.
- Coverage `nodes.py`: **95%** (target: 80%).
- Full suite: **36/36 passed**, zero regressions.

## Deviations from Plan

None — plan executed exactly as written.

## Known Stubs

None — all data flows from real DuckDB queries through the hardened node.

## Threat Flags

No new network endpoints, auth paths, or file access patterns introduced. All changes are internal to `sql_tool_node`. Threat model T-02-01 and T-02-02 fully mitigated as planned.

## Self-Check: PASSED

Files exist:
- src/dataagent/config.py — contains `SQL_MAX_RETRIES = 2`
- src/dataagent/agent/nodes.py — contains `EXPLAIN`, `_validate_sql`, `_generate_sql`, `_regenerate_sql`, `attempts`
- tests/test_nodes.py — contains `_SequenceLLM`, `test_sql_tool_retries_and_corrects`, `test_sql_tool_exhausts_retries_pushes_error`

Commits verified: bdf4934, 3669a23, feb914f, 4aecb6a all present in git log.
