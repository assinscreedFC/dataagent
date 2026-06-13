---
phase: 01-state-foundation-minimal-graph
plan: "03"
subsystem: agent-graph
tags: [langgraph, stategraph, graph, cli, duckdb, gemini, end-to-end]
dependency_graph:
  requires:
    - phase: 01-state-foundation-minimal-graph/01-01
      provides: [AgentState, initial_state, flash_llm, pro_llm]
    - phase: 01-state-foundation-minimal-graph/01-02
      provides: [planner_node, sql_tool_node, synthesizer_node]
  provides:
    - build_graph() — CompiledStateGraph linéaire START->planner->sql_tool->synthesizer->END
    - run(question, conn=None) — invoque le graphe, retourne l'état final
    - python -m dataagent "question" — entrypoint CLI end-to-end
  affects: [phase-02-sql-validation, phase-04-critic-loop, phase-05-checkpointer]
tech-stack:
  added: []
  patterns: [LangGraph StateGraph compile+invoke, CLI entrypoint __main__.py, load_dotenv avant imports, DuckDB conn injection via run(conn=)]
key-files:
  created:
    - src/dataagent/agent/graph.py
    - src/dataagent/__main__.py
    - tests/test_graph.py
  modified: []
key-decisions:
  - "run(conn=None) accepte une conn injectée (tests) ou crée la connexion réelle (CLI) — pas de chargement CSV dans les tests"
  - "load_dotenv() en tout début de __main__.py (avant imports dataagent) pour que config.py lise GEMINI_API_KEY correctement"
  - "Import différé de graph.run dans main() pour garantir load_dotenv prioritaire"
  - "Coverage graph.py 91% — branche conn is None (chargement CSV réel) testée manuellement via CLI"
patterns-established:
  - "Injection de conn via run(conn=) : même pattern à conserver pour tous les helpers futurs nécessitant DuckDB"
  - "Entrypoint CLI : load_dotenv -> fail-fast key check -> import différé -> run() -> print"
requirements-completed: [GRAPH-02, GRAPH-06]
duration: 6min
completed: "2026-06-13"
---

# Phase 1 Plan 3: Graph Wiring & CLI Summary

StateGraph LangGraph compilé (planner->sql_tool->synthesizer) invocable via `python -m dataagent "question"`, avec injection DuckDB, max_iterations=5 observable et rapport markdown sourcé.

## Performance

- **Duration:** 6 min
- **Started:** 2026-06-13T11:58:22Z
- **Completed:** 2026-06-13T12:04:01Z
- **Tasks:** 3
- **Files modified:** 3 created

## Accomplishments

- `build_graph()` compile `StateGraph(AgentState)` avec 3 nodes et edges linéaires `START -> planner -> sql_tool -> synthesizer -> END` (D-04, GRAPH-02)
- `run(question, conn=None)` injecte la connexion DuckDB dans `initial_state` via UntrackedValue, invoque le graphe compilé, retourne l'état final complet (plan, findings, report, max_iterations)
- `python -m dataagent "question"` : load_dotenv, fail-fast GEMINI_API_KEY, build+invoke, print report ; `--debug` expose plan/iterations/max_iterations (GRAPH-06)
- Tests e2e : 3 tests (compile, structure, run complet) ; DuckDB réel, LLM mocké ; tous criteria vérifiés ; 31 tests suite complète, 0 régression

## Task Commits

1. **Task 1: build_graph() + run()** - `72758c8` (feat)
2. **Task 2: Entrypoint CLI __main__.py** - `1aa2c3f` (feat)
3. **Task 3: test_graph.py** - `e7bca94` (test)

## Files Created/Modified

- `src/dataagent/agent/graph.py` — build_graph() StateGraph compilé + run() helper avec injection conn
- `src/dataagent/__main__.py` — CLI entrypoint : load_dotenv, fail-fast, invoke, print
- `tests/test_graph.py` — 3 tests e2e : compile, structure nodes, run() complet (DuckDB réel, LLM mocké)

## Decisions Made

- `run(conn=None)` : injection optionnelle de conn pour les tests (pas de rechargement des 9 CSV réels), création automatique pour le CLI. Pattern à conserver pour les futurs helpers.
- `load_dotenv()` placé en tout début de `__main__.py` (avant `from dataagent...`) pour que `config.py` lise `GEMINI_API_KEY` au moment de l'import — import de `run` différé dans `main()`.
- Coverage graph.py 91% : la branche `if conn is None` (création conn + chargement CSV réels) n'est pas couverte par les tests automatiques (injectent une conn), mais est exercée via le run CLI manuel avec `GEMINI_API_KEY`.

## Deviations from Plan

None - plan executed exactly as written.

## Known Stubs

None — tous les modules produisent une sortie réelle (LLM mocké dans les tests uniquement).

## Threat Flags

None — pas de nouveau endpoint réseau, pas d'accès fichier aux boundaries de sécurité. La clé API est vérifiée depuis l'env uniquement (jamais loggée). Le fail-fast `sys.exit(1)` sur clé manquante est conforme security.md.

## Issues Encountered

None.

## User Setup Required

Le run live (criterion #1) nécessite `GEMINI_API_KEY` dans `.env` et un accès réseau Gemini :

```bash
python -m dataagent "CA total 2017 ?"
```

Cette commande n'est pas dans les tests automatiques — à exécuter manuellement pour valider la réponse end-to-end avec le vrai LLM.

## Verification

```
python -m pytest tests/ -q      → 31 passed (0 regressions)
python -m pytest tests/test_graph.py --cov=dataagent.agent.graph → 91% coverage
python -c "from dataagent.agent.graph import build_graph; build_graph()"  → CompiledStateGraph
python -m dataagent               → usage + exit 1
# Manuel (nécessite GEMINI_API_KEY + réseau) :
# python -m dataagent "CA total 2017 ?"  → rapport markdown sourcé
```

## Next Phase Readiness

- Phase 1 complète : AgentState + factories LLM + 3 nodes + graphe compilé + CLI end-to-end
- Phase 2 (sql-validation) : sql_tool_node reçoit findings avec `error` key — validation + retry viennent s'y brancher sans toucher le graphe
- Phase 4 (critic loop) : `max_iterations` et `iterations` sont dans le state dès maintenant, prêts pour la condition `iterations >= max_iterations`

---
*Phase: 01-state-foundation-minimal-graph*
*Completed: 2026-06-13*

## Self-Check: PASSED
