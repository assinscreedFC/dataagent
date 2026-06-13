---
phase: 01-state-foundation-minimal-graph
plan: "02"
subsystem: agent-nodes
tags: [langgraph, nodes, planner, sql-tool, synthesizer, duckdb, gemini]
dependency_graph:
  requires: [AgentState, initial_state, flash_llm, pro_llm, GEMINI_MODEL_FLASH, GEMINI_MODEL_PRO]
  provides: [schema_description, planner_node, sql_tool_node, synthesizer_node]
  affects: [plan-03-graph, plan-03-cli]
tech_stack:
  added: []
  patterns: [LangGraph node (state -> dict), parameterized DuckDB introspection, monkeypatch LLM mock]
key_files:
  created:
    - src/dataagent/agent/schema_introspect.py
    - src/dataagent/agent/nodes.py
    - tests/test_nodes.py
  modified: []
decisions:
  - "sql_tool_node iterates over all plan sub-questions (one finding per sub-question) — documented as Phase 1 choice"
  - "BLE001 broad except kept intentionally for sql_tool error boundary (duckdb.Error + fallback Exception)"
  - "_extract_tables uses regex cross-check against schema string to avoid parsing SQL AST (YAGNI)"
metrics:
  duration_minutes: 7
  completed_date: "2026-06-13"
  tasks_completed: 3
  tasks_total: 3
  files_created: 3
  files_modified: 0
requirements: [GRAPH-03, GRAPH-04]
---

# Phase 1 Plan 2: LangGraph Nodes Summary

Three LangGraph nodes (planner/Flash, sql_tool/Flash, synthesizer/Pro) with DuckDB schema introspection and parameterized SQL anti-hallucination.

## Tasks Completed

| Task | Name | Commit | Files |
|------|------|--------|-------|
| 1 | schema_introspect.py — DuckDB schema description | 4f89f50 | src/dataagent/agent/schema_introspect.py, tests/test_nodes.py |
| 2 | planner_node + sql_tool_node | 0b0d5ea | src/dataagent/agent/nodes.py |
| 3 | synthesizer_node + full test suite | 0b0d5ea | src/dataagent/agent/nodes.py (synthesizer included), tests/test_nodes.py |

## What Was Built

**schema_introspect.py** — `schema_description(conn)` introspects `information_schema.tables` and `information_schema.columns` with parameterized queries. Returns `TABLE name(col TYPE, ...)` format, one line per table, ordered deterministically. Fed into sql_tool prompts to give the LLM real table/column names (anti-hallucination, D-12).

**nodes.py** — Three LangGraph nodes (each returns a dict of state keys to update):

- `planner_node(state)` (Flash, D-08): Prompts Flash to decompose the question into 1-4 analytical sub-questions. Parses non-empty lines, guarantees non-empty plan. Returns `{"plan": list[str]}`.

- `sql_tool_node(state)` (Flash, D-12): Iterates over `plan[]`, for each sub-question prompts Flash with the DuckDB schema + question, cleans markdown fences from output, executes SQL on real DuckDB. Success: `{"source", "subquestion", "sql", "tables", "rows", "columns"}`. Error: `{"source", "subquestion", "sql", "error"}` — no retry, no re-raise (D-12). Returns `{"findings": [...], "iterations": N+1}`.

- `synthesizer_node(state)` (Pro, D-09): Serializes findings to structured text, prompts Pro to write a markdown report explicitly citing sources (tables + SQL queries). Handles empty/all-error findings with an explanatory markdown report. Returns `{"report": str}`.

**tests/test_nodes.py** — 13 tests, LLM mocked via monkeypatch `_FakeLLM`, DuckDB I/O real (fixture `conn`):
- 4 schema tests (non-empty, table listing, column listing, determinism)
- 3 planner tests (multi-line, single-line, empty-lines)
- 3 sql_tool tests (success+finding, error+no-crash, fence stripping)
- 3 synthesizer tests (markdown report, empty findings, error findings)

## Verification

```
python -m pytest tests/test_nodes.py -q          → 13 passed
python -m pytest -q                              → 28 passed (0 regressions)
coverage nodes.py                                → 99%
coverage schema_introspect.py                    → 100%
python -c "from dataagent.agent.nodes import planner_node, sql_tool_node, synthesizer_node" → ok
```

## Deviations from Plan

### Auto-fixed Issues

None — plan executed exactly as written.

### Implementation Notes

1. **synthesizer_node included in nodes.py commit** — Task 2 committed all three nodes together (`0b0d5ea`) because nodes.py was written in one pass. Task 3 added test coverage for synthesizer; no separate commit needed (file unchanged).

2. **sql_tool iterates over all plan sub-questions** — The plan offered a choice ("first sub-question OR iterate"). Chose full iteration to produce one finding per sub-question, which gives synthesizer richer context. Documented in decisions.

## Known Stubs

None — all nodes produce real output from real DuckDB queries (with LLM mocked in tests).

## Threat Flags

None — no new network endpoints, no file I/O at trust boundaries, no new auth paths. LLM API key read from env only (never logged).

## Self-Check: PASSED
