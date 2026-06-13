---
gsd_state_version: 1.0
milestone: v1.1
milestone_name: — Hardening
status: verifying
stopped_at: Completed 07-hardening-bug-fixes/07-04-PLAN.md
last_updated: "2026-06-13T18:54:04.199Z"
last_activity: 2026-06-13
progress:
  total_phases: 1
  completed_phases: 1
  total_plans: 4
  completed_plans: 4
  percent: 100
---

# Project State

## Project Reference

See: .planning/PROJECT.md (updated 2026-06-13)

**Core value:** Une question business en langage naturel produit un rapport correct, sourcé et visualisé — sans intervention humaine dans la boucle d'analyse.
**Current focus:** Phase 7 — Hardening & Bug Fixes

## Current Position

Phase: 7 (Hardening & Bug Fixes) — EXECUTING
Plan: 4 of 4
Status: Phase complete — ready for verification
Last activity: 2026-06-13

Progress: [░░░░░░░░░░] 0%

## Performance Metrics

**Velocity:**

- Total plans completed: 12
- Average duration: - min
- Total execution time: 0.0 hours

**By Phase:**

| Phase | Plans | Total | Avg/Plan |
|-------|-------|-------|----------|
| 01 | 3 | - | - |
| 02 | 1 | - | - |
| 03 | 2 | - | - |
| 04 | 2 | - | - |
| 05 | 1 | - | - |
| 06 | 3 | - | - |

**Recent Trend:**

- Last 5 plans: -
- Trend: -

*Updated after each plan completion*
| Phase 01-state-foundation-minimal-graph P01-01 | 19 | 3 tasks | 5 files |
| Phase 01-state-foundation-minimal-graph P01-02 | 7 | 3 tasks | 3 files |
| Phase 01-state-foundation-minimal-graph P01-03 | 6 | 3 tasks | 3 files |
| Phase 02-sql-tool-hardening P02-01 | 10 | 3 tasks | 3 files |
| Phase 03-stats-viz-tools P03-01 | 10 | 3 tasks | 4 files |
| Phase 03-stats-viz-tools P03-02 | 17 | 3 tasks | 3 files |
| Phase 04-router-critic-loop P01 | 966 | 3 tasks | 4 files |
| Phase 04-router-critic-loop P02 | 1200 | 3 tasks | 5 files |
| Phase 05-resumability P01 | 40 | 3 tasks | 3 files |
| Phase 06 P01 | 751 | 2 tasks | 4 files |
| Phase 06 P06-02 | 12 | 2 tasks | 2 files |
| Phase 06-eval-api-demo P06-03 | 13 | 1 tasks | 2 files |
| Phase 07-hardening-bug-fixes P07-01 | 12 | 3 tasks | 5 files |
| Phase 07 P02 | 20 | 3 tasks | 9 files |
| Phase 07-hardening-bug-fixes P03 | 5 | 1 tasks | 2 files |
| Phase 07-hardening-bug-fixes P07-04 | 35 | 3 tasks | 5 files |

## Accumulated Context

### Decisions

Decisions are logged in PROJECT.md Key Decisions table.
Recent decisions affecting current work:

- [Setup]: LangGraph `StateGraph` manuel (pas `create_react_agent`) — critic loop = parallel nodes + supervisor + retry custom + branching
- [Setup]: Connexion DuckDB en `UntrackedValue` — state transient jamais checkpointé
- [Setup]: `max_iterations` câblé dès Phase 1 (J2) — garde-fou coût, hard stop boucle critic
- [Setup]: Router type-hinté + `path_map` — évite le misroute silencieux
- [Setup]: Haiku planner/router/critic, Opus synthesizer — cheap sur la boucle, qualité sur le rapport
- [Phase 01-state-foundation-minimal-graph]: UntrackedValue(typ) requis LangGraph 1.2.4 — syntaxe Annotated[T, UntrackedValue(T)] retenue
- [Phase 01-state-foundation-minimal-graph]: sql_tool_node iterates over all plan sub-questions (one finding per sub-question) — richer synthesizer context
- [Phase 01-state-foundation-minimal-graph]: _extract_tables uses regex cross-check against schema string (no SQL AST parser, YAGNI)
- [Phase 01-state-foundation-minimal-graph]: run(conn=None) injectable pour tests, crée connexion réelle pour CLI (pattern à conserver)
- [Phase 01-state-foundation-minimal-graph]: load_dotenv() avant imports dataagent dans __main__.py — import différé de run() dans main()
- [Phase 02-sql-tool-hardening]: EXPLAIN used for pre-execution SQL validation (D-01/D-02) — more robust than manual information_schema check
- [Phase 02-sql-tool-hardening]: SQL_MAX_RETRIES=2 in config.py, distinct from MAX_ITERATIONS (D-03) — intra-tool retry guard
- [Phase 03-stats-viz-tools]: Test fixture uses [10]*20+[100] (z~4.47) instead of [10]*6+[100] (z~2.24 < threshold 3.0) — math constraint
- [Phase 03-stats-viz-tools]: stats_tool_node does not increment iterations — router/critic owns that in Phase 4
- [Phase 03-stats-viz-tools]: render_chart uses slugify (re.sub [^a-z0-9]+) for path-safe deterministic PNG filenames
- [Phase 03-stats-viz-tools]: viz_tool_node renders only first chartable sql_tool finding per call; does not increment iterations
- [Phase 04-router-critic-loop]: route_subquestion uses keyword heuristic (deterministic) with index guard; critic_node exposes sufficient:bool via last finding source=critic for Plan 02 path_map
- [Phase 04-router-critic-loop]: _router_node pass-through + add_conditional_edges path_map; _critic_decision hard cap applicatif (iterations>=max avant GraphRecursionError); sql_tool_node traite uniquement current_step
- [Phase 05-resumability]: _FilteredSqliteSaver strips db from __start__ channel before msgpack serialization (UntrackedValue not enough)
- [Phase 05-resumability]: LangGraph re-runs full graph on same thread_id for completed checkpoints — findings accumulate via add reducer as proof of checkpoint activity
- [Phase 05-resumability]: run(thread_id) passes initial_state() to invoke() with FilteredSqliteSaver filtering db — conn fresh per run (D-05)
- [Phase 06]: score_report retourne 0.0 sur liste vide — sémantique zéro critères => zéro score
- [Phase 06]: run_fn injectable en paramètre de run_eval (default=graph.run) — tests sans quota Gemini (D-03)
- [Phase 06]: AskRequest min_length=1 rejects empty question at Pydantic layer (T-06-01); run() imported at module top for monkeypatch (D-05); sync handlers in FastAPI threadpool for blocking run() (D-04)
- [Phase 06-eval-api-demo]: render_html injects extra img only when png_path absent from markdown (synthesizer may already embed it)
- [Phase 06-eval-api-demo]: CSS inlined in head — standalone HTML, no external assets required
- [Phase 07-01]: D-01/D-02: critic_node bounds next_step + _critic_decision early-exit when plan exhausted; hard cap preserved
- [Phase 07-01]: D-08: _as_text(response)->str helper after every .invoke() — type-safe, handles multi-part LLM responses
- [Phase 07-01]: D-10: schema:str in AgentState computed once in run(), propagated via state; sql_tool_node uses fallback
- [Phase 07-02]: D-04: SQL_FORBIDDEN_KEYWORDS + _is_write_sql word-boundary guard before validate/exec, no retry on write (HARD-03)
- [Phase 07-02]: D-05: _TABLE_NAME_RE in loader.py skips non-conforming CSV table names with warning (HARD-04)
- [Phase 07-02]: D-06: max_length=2000 on AskRequest; _filter_findings strips sql/rows/columns by default; ?debug=true opt-in (HARD-05)
- [Phase 07-02]: D-07: html.escape(png_path, quote=True) in render.py before <img src> injection (HARD-06)
- [Phase 07-02]: D-12: FastAPI lifespan creates one persistent DuckDB conn; ask() uses getattr fallback None for test compat (HARD-11)
- [Phase 07-hardening-bug-fixes]: D-11: _flash/_pro lazy singletons in llm.py — one ChatGoogleGenerativeAI instance per process, monkeypatching preserved
- [Phase 07-hardening-bug-fixes]: D-13a: DuckDB execute read-only (C-ext) — proxy wrapper _FailingConn used in tests instead of monkeypatch
- [Phase 07-hardening-bug-fixes]: D-13b: Stale tests fixed by adding plan+current_step to test states (D-01/D-02 behavior), production code unchanged
- [Phase 07-hardening-bug-fixes]: D-13c: CLI deferred import — tests must patch dataagent.agent.graph.run not __main__.run

### Pending Todos

None yet.

### Blockers/Concerns

None yet.

## Session Continuity

Last session: 2026-06-13T18:54:04.187Z
Stopped at: Completed 07-hardening-bug-fixes/07-04-PLAN.md
Resume file: None
