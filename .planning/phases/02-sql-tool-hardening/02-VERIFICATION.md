---
phase: 02-sql-tool-hardening
verified: 2026-06-13T00:00:00Z
status: passed
score: 5/5 must-haves verified
re_verification: false
---

# Phase 02: SQL Tool Hardening — Verification Report

**Phase Goal:** Le sql_tool ne casse plus sur du SQL halluciné — il valide contre le schema réel avant exec et retry sur erreur.
**Verified:** 2026-06-13
**Status:** passed
**Re-verification:** No — initial verification

---

## Goal Achievement

### Observable Truths

| # | Truth | Status | Evidence |
|---|-------|--------|----------|
| 1 | Une query SQL référençant une colonne/table inexistante est rejetée AVANT exécution sur les données (via EXPLAIN) | VERIFIED | `_validate_sql` runs `conn.execute("EXPLAIN " + sql)` (nodes.py:77). `test_validate_sql_rejects_unknown_column` asserts non-None return for `SELECT colonne_bidon FROM orders`. `test_sql_tool_handles_sql_error` confirms no data scan on bad table. |
| 2 | Sur erreur de validation ou d'exécution, le tool re-prompte le LLM et retry au moins une fois avec une query corrigée | VERIFIED | `_regenerate_sql` re-prompts with bad_sql + DuckDB error (nodes.py:114-124). `test_sql_tool_retries_and_corrects` uses `_SequenceLLM` and asserts `attempts == 2` on success finding. |
| 3 | Le résultat d'une query valide est poussé dans findings avec sa source (SQL + tables + nb tentatives) | VERIFIED | Success finding returns `source`, `subquestion`, `sql`, `tables`, `rows`, `columns`, `attempts` (nodes.py:163-171). `test_sql_tool_valid_first_try_attempts_one` asserts all Phase 1 keys plus `attempts == 1`. |
| 4 | Une question dont le SQL initial échoue finit quand même par produire un finding correct via le retry | VERIFIED | `test_sql_tool_node_recovers_from_failed_initial_sql` calls `sql_tool_node` with `_SequenceLLM(["SELECT * FROM commandes_inexistantes", "SELECT COUNT(*) AS n FROM orders"])`, asserts `error` not in finding and `rows` non-empty. |
| 5 | Si tous les retries échouent, un finding d'erreur explicite est poussé sans crash (le graphe continue) | VERIFIED | Loop exits after `SQL_MAX_RETRIES + 1` attempts, returns error finding (nodes.py:191-197). `test_sql_tool_exhausts_retries_pushes_error` asserts `attempts == SQL_MAX_RETRIES + 1`, `error` present, no exception. |

**Score:** 5/5 truths verified

---

## Required Artifacts

| Artifact | Expected | Status | Details |
|----------|----------|--------|---------|
| `src/dataagent/config.py` | Constante `SQL_MAX_RETRIES` (défaut 2) | VERIFIED | Line 12: `SQL_MAX_RETRIES = 2` with doc comment distinguishing it from `MAX_ITERATIONS` |
| `src/dataagent/agent/nodes.py` | `sql_tool_node` durci: EXPLAIN + boucle retry + finding enrichi | VERIFIED | Contains `_validate_sql`, `_generate_sql`, `_regenerate_sql`, `_execute_subquestion` with bounded loop, `attempts` in both success and error findings |
| `tests/test_nodes.py` | Tests validation rejette + retry produit finding correct + épuisement retries | VERIFIED | Contains `_SequenceLLM`, `test_sql_tool_retries_and_corrects`, `test_sql_tool_exhausts_retries_pushes_error`, `test_sql_tool_node_recovers_from_failed_initial_sql`, `test_validate_sql_rejects_unknown_column` |

---

## Key Link Verification

| From | To | Via | Status | Details |
|------|----|-----|--------|---------|
| `nodes.py` | `conn.execute("EXPLAIN " + sql)` | `_validate_sql` — pre-execution catalogue check | VERIFIED | nodes.py:77 — literal string `"EXPLAIN " + sql`, no data scan |
| `nodes.py` | `flash_llm()` re-prompt with DuckDB error | `_regenerate_sql` — corrected query generation in retry loop | VERIFIED | nodes.py:114-124 — `bad_sql` and `error` injected into system_msg; called at nodes.py:149 for `attempt > 1` |
| `nodes.py` | `findings[]` (reducer add) | `_execute_subquestion` returning enriched finding with `attempts` | VERIFIED | nodes.py:163-171 (success) and 191-197 (error exhaustion); `sql_tool_node` appends to `findings` list at line 215 |

---

## Data-Flow Trace (Level 4)

| Artifact | Data Variable | Source | Produces Real Data | Status |
|----------|--------------|--------|--------------------|--------|
| `sql_tool_node` findings | `rows`, `columns` | `conn.execute(sql)` + `cursor.fetchall()` (nodes.py:159-161) | Yes — real DuckDB cursor against Olist CSV-loaded tables | FLOWING |
| `_validate_sql` error path | `validation_error` str | `duckdb.Error` raised by `EXPLAIN` (nodes.py:79-85) | Yes — real catalogue exception from DuckDB | FLOWING |
| `_regenerate_sql` prompt | `bad_sql`, `error` | `last_sql`, `last_error` set from previous failed attempt (nodes.py:154, 173) | Yes — carries actual DuckDB error text into re-prompt | FLOWING |

---

## Behavioral Spot-Checks

| Behavior | Command | Result | Status |
|----------|---------|--------|--------|
| `SQL_MAX_RETRIES` importable from config | `python -c "from dataagent.config import SQL_MAX_RETRIES; print(SQL_MAX_RETRIES)"` | `2` | PASS |
| `_validate_sql` importable from nodes | `python -c "from dataagent.agent.nodes import _validate_sql; print('ok')"` | `ok` | PASS |
| Full test suite (36 tests, LLM mocked) | `python -m pytest tests/ -q` | `36 passed` | PASS |
| `nodes.py` coverage | `pytest --cov=dataagent.agent.nodes tests/test_nodes.py` | `95%` (target: 80%) | PASS |

---

## Requirements Coverage

| Requirement | Source Plan | Description | Status | Evidence |
|-------------|------------|-------------|--------|----------|
| TOOL-01 | 02-01-PLAN.md | sql_tool génère du SQL, le valide sur le schema DuckDB avant exec, retry sur erreur, push findings | SATISFIED | `_validate_sql` (EXPLAIN), `_execute_subquestion` bounded retry loop, findings with `source`/`sql`/`tables`/`rows`/`attempts`. All 36 tests green. |

---

## Anti-Patterns Found

| File | Line | Pattern | Severity | Impact |
|------|------|---------|----------|--------|
| `nodes.py` | 204 | Docstring says "Minimal (D-12) : pas de validation ni retry (phase 2)" — outdated after phase 2 hardening | INFO | None — stale comment, no behavioral impact |

No stubs, no hardcoded empty returns, no TODO without context, no swallowed exceptions.

---

## Human Verification Required

None. All four success criteria are fully testable with mocked LLM and a real DuckDB connection. The test suite exercises all branches programmatically.

---

## Gaps Summary

No gaps. All 5 must-have truths are verified against actual code and confirmed by a passing 36-test suite (0 failures, 0 regressions from Phase 1). Coverage on `nodes.py` is 95%, well above the 80% target. The only finding is a stale docstring comment on `sql_tool_node` (line 204) that still says "pas de validation ni retry" — informational only, no behavioral impact.

---

_Verified: 2026-06-13_
_Verifier: Claude (gsd-verifier)_
