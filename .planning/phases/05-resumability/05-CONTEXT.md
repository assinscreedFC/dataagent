# Phase 5: Resumability - Context

**Gathered:** 2026-06-13 (auto mode — recommended defaults from PLAN.md + phases 1-4 code)
**Status:** Ready for planning

<domain>
## Phase Boundary

Rend les runs de l'agent resumables : le graphe est compilé avec un `checkpointer` SqliteSaver, un run identifié par `thread_id` persiste son état dans un store SQLite, et relancer le même `thread_id` reprend l'état au lieu de repartir de zéro. Couvre TOOL-07. HORS scope : eval/API/demo (Phase 6). Modifications limitées à `build_graph()`/`run()` (graph.py), config (chemin du store), et tests.

</domain>

<decisions>
## Implementation Decisions

### Checkpointer (success criterion #1)
- **D-01:** `build_graph()` compile le graphe avec un `checkpointer` SqliteSaver (`from langgraph.checkpoint.sqlite import SqliteSaver`, package `langgraph-checkpoint-sqlite` déjà installé + ajouté à pyproject extra `agent`). Conforme PLAN.md (resumabilité via checkpointer SqliteSaver).
- **D-02:** Chemin du store SQLite dans une constante config `CHECKPOINT_DB` (défaut `PROJECT_ROOT / ".checkpoints.sqlite"`, gitignored `*.sqlite`). Override possible via env.

### thread_id & persistance (success criteria #2, #3)
- **D-03:** `run()` accepte un paramètre optionnel `thread_id: str | None`. Si fourni → invoke avec `config={"configurable": {"thread_id": thread_id}}` ; le checkpointer écrit l'état (plan, findings, iterations, current_step…) dans SQLite. Sans `thread_id` → comportement actuel (run éphémère, checkpointer optionnel ou thread_id généré).
- **D-04:** Relancer `run()` avec le même `thread_id` reprend l'état checkpointé (LangGraph charge le dernier checkpoint du thread) au lieu de repartir de zéro.

### Connexion DuckDB transiente (point d'attention)
- **D-05:** La connexion DuckDB est en `UntrackedValue` → JAMAIS checkpointée (Phase 1, D-02). À la reprise, `run()` doit **ré-injecter** une connexion DuckDB fraîche dans l'état initial (recharger Olist via le loader) ; le checkpointer restaure le reste (plan/findings/iterations). C'est précisément le rôle d'`UntrackedValue` : l'état logique est resumable, la ressource I/O est recréée.

### Claude's Discretion
- Gestion du cycle de vie du `SqliteSaver` (context manager `from_conn_string` vs connexion sqlite3 explicite), génération du thread_id par défaut, exposition éventuelle de `--thread-id` côté CLI (optionnel, pas requis par les critères).

</decisions>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### Architecture
- `PLAN.md` §Findings LangGraph v1.0 : "Resumabilité → `checkpointer` SqliteSaver". §Risques : "State non reproductible → checkpointer SqliteSaver". §State schema : `db: UntrackedValue` (jamais checkpointé — clé pour la reprise).

### Code à modifier (réutiliser, ne pas casser)
- `src/dataagent/agent/graph.py` — `build_graph()` (ajouter `checkpointer=`) + `run()` (param `thread_id`, ré-injection conn à la reprise — D-05). Le graphe branché de Phase 4 reste inchangé structurellement.
- `src/dataagent/config.py` — ajouter `CHECKPOINT_DB`.
- `pyproject.toml` — `langgraph-checkpoint-sqlite` ajouté à l'extra `agent`.
- `tests/conftest.py` — fixtures.

### API
- `langgraph.checkpoint.sqlite.SqliteSaver` (v3.1.0 installé) — vérifier l'API courante (`SqliteSaver.from_conn_string(path)` est un context manager ; alternative : `SqliteSaver(sqlite3.connect(path, check_same_thread=False))`).

</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets
- `build_graph()` + `run()` de graph.py (Phase 4, graphe branché) — points d'extension.
- `loader.connect()` + `load_csvs_to_duckdb()` — recréation de la connexion DuckDB à la reprise (D-05).
- `config.PROJECT_ROOT` pour le chemin du store.

### Established Patterns
- Tests : I/O réelle (SQLite réel, DuckDB réel), LLM mocké. Pour tester la reprise : run avec thread_id (mock LLM déterministe), vérifier que le store SQLite contient l'état du thread, relancer le même thread_id et vérifier que l'état est repris (pas de re-planification depuis zéro). Pas d'appel LLM réel → pas de quota.
- `UntrackedValue` (db) déjà en place — la reprise ré-injecte la conn.

### Integration Points
- graph.py (compile + run), config.py (chemin store), pyproject (dep), .gitignore (`*.sqlite` ajouté).
- Le store SQLite est créé au premier run avec thread_id.

</code_context>

<specifics>
## Specific Ideas

- Le point subtil est `UntrackedValue` : la connexion DuckDB ne doit pas être checkpointée (non sérialisable + ressource), donc la reprise recrée la conn et restaure le reste. C'est le design voulu par le PLAN.
- Tester explicitement la reprise (même thread_id → état repris), pas seulement la compilation avec checkpointer.

</specifics>

<deferred>
## Deferred Ideas

- Eval 10 Q/R, FastAPI /ask, demo HTML/screenshots Labs — Phase 6 (dernière phase)

</deferred>

---

*Phase: 05-resumability*
*Context gathered: 2026-06-13*
