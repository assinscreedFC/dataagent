---
phase: 01-state-foundation-minimal-graph
plan: "01"
subsystem: agent-state
tags: [langgraph, state-schema, gemini, config, duckdb]
dependency_graph:
  requires: []
  provides: [AgentState, initial_state, flash_llm, pro_llm, GEMINI_MODEL_FLASH, GEMINI_MODEL_PRO]
  affects: [plan-02-nodes, plan-03-graph]
tech_stack:
  added: [langgraph>=1.0, langchain-google-genai]
  patterns: [TypedDict state schema, UntrackedValue channel annotation, Annotated reducers]
key_files:
  created:
    - src/dataagent/agent/__init__.py
    - src/dataagent/agent/state.py
    - src/dataagent/agent/llm.py
    - tests/test_state.py
  modified:
    - src/dataagent/config.py
decisions:
  - "UntrackedValue(DuckDBPyConnection) requis en LangGraph 1.2.4 — syntaxe UntrackedValue() sans arg rejetée"
  - "GEMINI_API_KEY avec fallback GOOGLE_API_KEY pour compatibilité langchain-google-genai"
  - "llm.py non testé directement (instanciation = appel réseau) — couvert par run e2e plan 03"
metrics:
  duration_minutes: 19
  completed_date: "2026-06-13"
  tasks_completed: 3
  tasks_total: 3
  files_created: 4
  files_modified: 1
requirements: [GRAPH-01, GRAPH-05]
---

# Phase 1 Plan 1: State Foundation Summary

AgentState TypedDict (8 champs D-01) + UntrackedValue DuckDB + factory Gemini Flash/Pro config-driven.

## Tasks Completed

| Task | Name | Commit | Files |
|------|------|--------|-------|
| 1 | Constantes Gemini à config.py | 7c2ab4c | src/dataagent/config.py |
| 2 | AgentState + initial_state() + tests RED→GREEN | 465f14b | src/dataagent/agent/__init__.py, state.py, tests/test_state.py |
| 3 | Factory LLM Gemini flash_llm()/pro_llm() | ae71681 | src/dataagent/agent/llm.py |

## What Was Built

**config.py** enrichi avec `GEMINI_MODEL_FLASH` (gemini-2.0-flash), `GEMINI_MODEL_PRO` (gemini-2.5-pro), `GEMINI_API_KEY` (env avec fallback GOOGLE_API_KEY). Override via variables d'environnement. `MAX_ITERATIONS=5` commenté "garde-fou coût boucle critic".

**state.py** — `AgentState` TypedDict : 8 champs exacts (D-01). `db` annoté `Annotated[DuckDBPyConnection, UntrackedValue(DuckDBPyConnection)]` — jamais checkpointé (D-02). `findings` avec reducer `add`, `messages` avec `add_messages` (D-03). Helper `initial_state(question, db)` avec `iterations=0`, `max_iterations=MAX_ITERATIONS` (D-10).

**llm.py** — `flash_llm()` et `pro_llm()` retournent `ChatGoogleGenerativeAI` pointant sur les constantes config, `temperature=0` pour déterminisme. Clé depuis env uniquement.

**tests/test_state.py** — 4 tests sur vraie I/O DuckDB (fixture `conn` de conftest.py) : champs exacts, UntrackedValue en metadata, operator.add en metadata, valeurs par défaut initial_state.

## Verification

```
python -m pytest tests/test_state.py -q  → 4 passed
python -m pytest -q                      → 15 passed (0 regressions)
coverage state.py                        → 100%
```

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] UntrackedValue requiert un argument `typ` en LangGraph 1.2.4**
- **Found during:** Task 2 (RED phase — import error à la création de la classe)
- **Issue:** Le plan prescrit `UntrackedValue()` sans argument. LangGraph 1.2.4 exige `UntrackedValue(typ: type)`.
- **Fix:** `Annotated[DuckDBPyConnection, UntrackedValue(DuckDBPyConnection)]` — l'instance est toujours reconnue comme `UntrackedValue` dans les metadata, le test `isinstance(m, UntrackedValue)` passe.
- **Files modified:** src/dataagent/agent/state.py
- **Commit:** 465f14b

**2. [Rule 2 - Missing] Fallback GOOGLE_API_KEY dans config.py**
- **Found during:** Task 1
- **Issue:** `langchain-google-genai` accepte `GOOGLE_API_KEY` en fallback — l'omettre casse les environnements qui n'ont que cette variable.
- **Fix:** `GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY") or os.environ.get("GOOGLE_API_KEY")`
- **Files modified:** src/dataagent/config.py
- **Commit:** 7c2ab4c

## Known Stubs

None — aucun stub ou placeholder introduit dans ce plan.

## Threat Flags

None — pas de nouveau endpoint réseau, pas d'auth path, pas d'accès fichier aux boundaries. La clé API est lue depuis l'env (jamais loggée).

## Self-Check: PASSED
