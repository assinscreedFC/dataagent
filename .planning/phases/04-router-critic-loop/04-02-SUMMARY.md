---
phase: 04-router-critic-loop
plan: "02"
subsystem: agent-graph
tags: [langgraph, branched-graph, router, critic-loop, hard-cap, multi-source, tdd]
dependency_graph:
  requires: [04-01-SUMMARY.md]
  provides: [build_graph-branched, _critic_decision, _router_node, test_critic_loop]
  affects: [run() (CLI entry point), Phase 5 checkpointer wiring]
tech_stack:
  added: [typing.Literal for _critic_decision, add_conditional_edges with path_map]
  patterns: [branched-StateGraph, path_map-anti-misroute, hard-cap-applicatif, tdd-green-first]
key_files:
  created: [tests/test_critic_loop.py]
  modified:
    - src/dataagent/agent/graph.py
    - src/dataagent/agent/nodes.py
    - tests/test_graph.py
    - tests/test_nodes.py
decisions:
  - "_router_node pass-through + add_conditional_edges(path_map) — router sans LLM (deterministic keyword routing via route_subquestion du Plan 01)"
  - "_critic_decision Literal-typed: hard cap applicatif iterations>=max_iterations avant GraphRecursionError (5<25)"
  - "sql_tool_node traite uniquement current_step (sous-question courante) — plus de boucle interne sur tout le plan"
  - "test_nodes.py mis à jour: iterations retiré du contrat de sql_tool_node (critic seul propriétaire D-06)"
metrics:
  duration_seconds: 1200
  completed_date: "2026-06-13"
  tasks_completed: 3
  files_modified: 5
---

# Phase 4 Plan 02: Graph Wiring + Critic Loop Summary

**One-liner:** `build_graph()` restructuré en graphe branché LangGraph (7 nodes, 2 `add_conditional_edges` avec `path_map` explicite) : router dispatche via `route_subquestion`, `_critic_decision` reboucle ou synthétise avec hard cap à `max_iterations`.

## Tasks Completed

| Task | Name | Commit | Files |
|------|------|--------|-------|
| 1 | sql_tool_node cède iterations au critic | 9b55e30 | nodes.py |
| 2 | build_graph() branché avec path_map (router + critic) | f21abd1 | graph.py |
| 3 | Tests intégration boucle critic (TDD) | 1e5437b | test_critic_loop.py, test_graph.py, test_nodes.py |

## What Was Built

### `build_graph()` — graphe branché (graph.py)

Topologie :
```
START -> planner -> router -+-> sql_tool ---+
                            +-> stats_tool -+-> critic -> (cond) -+-> router (reboucle)
                            +-> viz_tool ---+                     +-> synthesizer -> END
```

- `_router_node(state) -> {}` : node pass-through, point d'ancrage pour `add_conditional_edges`
- `add_conditional_edges("router", route_subquestion, path_map={"sql_tool":..., "stats_tool":..., "viz_tool":...})` — TOOL-04, D-01
- Edges tool→critic pour `sql_tool`, `stats_tool`, `viz_tool`
- `_critic_decision(state) -> Literal["router","synthesizer"]` : hard cap `iterations>=max_iterations` → synthesizer ; `sufficient=True` → synthesizer ; sinon → router (TOOL-05/06, D-05/06)
- `add_conditional_edges("critic", _critic_decision, path_map={"router":..., "synthesizer":...})` — D-05
- `run()` inchangé (CLI entry point)

### `sql_tool_node` mis à jour (nodes.py)

- Traite uniquement `plan[current_step]` (sous-question courante) — plus de boucle interne
- Ne retourne plus `iterations` (D-06 : critic seul propriétaire)
- Retourne `{"findings": [finding]}` (un seul finding par appel, conforme graphe branché)

### `tests/test_critic_loop.py` — 16 tests

- **(a) Routing** : `TestRouting` (7 tests unitaires `route_subquestion`) + `TestRoutingEndToEnd` (finding sql_tool en e2e)
- **(b) Reloop+Synth** : `TestReloopThenSynth.test_reloop_then_synthesize` — critic insuffisant tour 1, suffisant tour 2 → `iterations==2`
- **(c) HARD CAP** : `TestHardCap` (5 tests) — critic toujours INSUFFISANT → `iterations==max_iterations==5`, terminaison prouvée par compteur d'appels critic ; `_critic_decision` unité hard cap / reloop / sufficient / no-findings
- **(d) Multi-source** : `TestMultiSource` — viz_tool finding + image `![` dans report ; multi-source report avec sources analytiques

### `tests/test_graph.py` mis à jour

- `test_graph_linear_structure` → `test_graph_branched_structure` (7 nodes attendus)
- `_FakeFlash` étendu : appel 3+ retourne SUFFISANT (sortie propre au 1er tour)

### `tests/test_nodes.py` mis à jour

- 4 tests retiraient `assert result["iterations"] == N+1` sur `sql_tool_node` → remplacés par `assert "iterations" not in result` (contrat D-06)

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] Régression test_nodes.py suite au retrait de iterations**
- **Found during:** Task 3 GREEN (full suite) — 4 tests `test_sql_tool_*` échouaient sur `KeyError: 'iterations'`
- **Issue:** Tests de phase 2 assertaient `result["iterations"] == state["iterations"] + 1` sur `sql_tool_node`, mais Task 1 a intentionnellement retiré ce champ (D-06)
- **Fix:** Assertions `iterations` remplacées par `assert "iterations" not in result` (nouveau contrat)
- **Files modified:** `tests/test_nodes.py`
- **Commit:** 1e5437b

**2. [Rule 2 - Contract] sql_tool_node adapté au graphe branché**
- **Found during:** Task 1 implementation — l'ancienne version itérait sur tout `plan[]` (comportement linéaire)
- **Issue:** Dans le graphe branché, chaque appel de sql_tool_node doit traiter uniquement `plan[current_step]` (une sous-question par passage dans la boucle)
- **Fix:** sql_tool_node lit `current_step` et traite `plan[current_step]` uniquement
- **Files modified:** `src/dataagent/agent/nodes.py`
- **Commit:** 9b55e30

## Verification Results

```
pytest tests/ : 125 passed, 0 failed, 18 warnings (deprecation plotly/kaleido)
pytest tests/test_critic_loop.py --cov=dataagent.agent.graph --cov=dataagent.agent.nodes:
  graph.py  : 96% (45 stmts, 2 miss — lignes 169-170 : branche conn=None du run() CLI)
  nodes.py  : 91% (full suite)
  TOTAL     : 92%
grep path_map graph.py : 2 occurrences (router + critic edges) ✓
HARD CAP test : terminaison prouvée, iterations==5==max_iterations ✓
MAX_ITERATIONS(5) < LangGraph recursion_limit(25) : hard cap applicatif s'arrête en premier ✓
```

## Known Stubs

None — tous les nodes sont implémentés et câblés. `run()` fonctionnel CLI.

## Threat Flags

Aucun nouveau endpoint réseau, chemin d'authentification, ou surface sécurité introduit par ce plan.

## Self-Check: PASSED
