# Phase 1: State Foundation & Minimal Graph - Context

**Gathered:** 2026-06-13 (auto mode — recommended defaults from PLAN.md)
**Status:** Ready for planning

<domain>
## Phase Boundary

Livre la boucle agent LangGraph minimale end-to-end : `planner → sql_tool → synthesizer`, compilée, invocable via `python -m dataagent "question"`. Le state schema complet est posé dès maintenant (y compris `max_iterations` et la connexion DuckDB en `UntrackedValue`), mais router, critic loop, stats_tool, viz_tool et checkpointer sont HORS scope (phases 3-5). Le sql_tool de cette phase est minimal (génère + exécute) — le durcissement validation/retry est la phase 2.

</domain>

<decisions>
## Implementation Decisions

### State schema (GRAPH-01)
- **D-01:** `AgentState` est un `TypedDict` portant exactement : `question: str`, `plan: list[str]`, `findings: Annotated[list[dict], add]`, `messages: Annotated[list, add_messages]`, `iterations: int`, `max_iterations: int`, `db: UntrackedValue[DuckDBPyConnection]`, `report: str` (conforme PLAN.md).
- **D-02:** La connexion DuckDB vit dans le state en `UntrackedValue` — transiente, jamais checkpointée (success criterion #4).
- **D-03:** `findings` accumule via reducer `Annotated[list, add]` ; `messages` via `add_messages`.

### Graphe minimal (GRAPH-02)
- **D-04:** `StateGraph(AgentState)` puis `.compile()` obligatoire avant exécution. Edges linéaires : `START → planner → sql_tool → synthesizer → END`. Pas de router ni de conditional edge cette phase.
- **D-05:** La connexion DuckDB est créée à l'entrée (chargement Olist depuis `data/raw/` via le loader J1 existant) et injectée dans le state initial, pas dans un node.

### LLM (GRAPH-03, GRAPH-04)
- **D-06:** Provider Gemini via `langchain-google-genai` (`ChatGoogleGenerativeAI`). Clé `GEMINI_API_KEY` chargée depuis `.env` via `python-dotenv`.
- **D-07:** Modèles — planner = `gemini-2.0-flash` (cheap/rapide), synthesizer = `gemini-2.5-pro` (qualité rapport). Noms de modèles centralisés en constantes dans `config.py` (override possible via env), pas hardcodés inline. La génération SQL du sql_tool minimal utilise aussi Flash.
- **D-08:** planner (Flash) décompose la question en sous-questions `plan[]` visibles dans le state (success criterion #5).
- **D-09:** synthesizer (Pro) produit un rapport markdown qui cite ses sources — tables/queries utilisées listées (success criterion #2).

### Garde-fou coût (GRAPH-05)
- **D-10:** `max_iterations` est dans le state dès cette phase (défaut constante `MAX_ITERATIONS = 5` dans `config.py`), `iterations` initialisé à 0. Observable dans le run. Pas encore consommé par une boucle (pas de critic ici) mais câblé et incrémenté côté sql_tool/structure prête pour la phase 4.

### CLI (GRAPH-06)
- **D-11:** Entrypoint `python -m dataagent "question"` via `src/dataagent/__main__.py` : parse la question (argument positionnel), build le graph, invoke, print le `report`. `python -m dataagent "CA total 2017 ?"` doit retourner une réponse correcte (success criterion #1).

### sql_tool minimal (scope phase 1)
- **D-12:** Génère du SQL depuis la sous-question + le schema DuckDB (noms de tables/colonnes injectés dans le prompt), exécute via DuckDB, pousse le résultat dans `findings` (dict avec query SQL + tables touchées + données). Validation stricte + retry = phase 2 (out of scope ici). En cas d'erreur SQL phase 1 : remonter l'erreur proprement, pas de retry.

### Claude's Discretion
- Format exact des dicts `findings` (clés précises), structure interne du prompt planner/sql/synthesizer, organisation des modules (`graph.py`, `state.py`, `nodes/`, `config.py`), gestion fine des erreurs LLM/réseau aux boundaries.

</decisions>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### Architecture & décisions figées
- `PLAN.md` — state schema (§State schema), graphe (§Graphe), findings LangGraph v1.0 vérifiés (§Findings), stack, décisions figées (provider Gemini révisé). Source de vérité de cette phase.

### Data layer existante (J1, à réutiliser)
- `src/dataagent/data/loader.py` — `connect()` + `load_csvs_to_duckdb(conn, "data/raw")` : charge Olist dans DuckDB, retourne les noms de tables. Réutilisé tel quel pour créer la connexion du state.
- `src/dataagent/data/queries.py` — 5 queries business Polars existantes ; référence pour le style SQL/schéma et potentiellement appelables par le sql_tool.
- `src/dataagent/config.py` — constantes existantes ; y ajouter les noms de modèles Gemini + `MAX_ITERATIONS`.

### LLM
- `langchain-google-genai` (`ChatGoogleGenerativeAI`) — vérifier l'API courante via Context7/docs au moment du plan (nom de classe, param `model`, `google_api_key`).

</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets
- `loader.connect()` / `load_csvs_to_duckdb()` : création connexion DuckDB + chargement Olist — réutilisé pour peupler `state["db"]`.
- `queries.py` : 5 queries business comme référence de schéma et style ; le sql_tool peut s'en inspirer ou les appeler.
- `config.py` : emplacement des constantes (modèles, MAX_ITERATIONS).

### Established Patterns
- Tests : vraie I/O DuckDB sur fixtures synthétiques (`tests/conftest.py`), jamais de mock I/O. Étendre ce pattern aux tests de la boucle agent (les appels LLM, eux, seront mockés ou testés sur question déterministe).
- Package layout `src/dataagent/` avec sous-modules ; `pyproject.toml` extra `agent` (déjà swappé vers `langchain-google-genai`).

### Integration Points
- Nouveau module agent (`src/dataagent/agent/` ou similaire) consommant `data/`.
- `src/dataagent/__main__.py` = nouveau point d'entrée CLI.
- `.env` (gitignored) fournit `GEMINI_API_KEY` ; `data/raw/` contient les 9 CSV Olist (déjà en place).

</code_context>

<specifics>
## Specific Ideas

- Le rapport doit citer ses sources (tables/queries) — pas juste un chiffre nu (success criterion #2).
- `max_iterations` câblé "dès le départ" est une exigence explicite du PLAN (garde-fou coût), même si la boucle critic n'arrive qu'en phase 4.

</specifics>

<deferred>
## Deferred Ideas

- Validation SQL contre schema + retry sur erreur — Phase 2 (TOOL-01)
- stats_tool, viz_tool — Phase 3
- Router conditional + critic loop + rapport multi-source — Phase 4
- Checkpointer SqliteSaver / resumabilité — Phase 5
- Eval, FastAPI, demo HTML — Phase 6

</deferred>

---

*Phase: 01-state-foundation-minimal-graph*
*Context gathered: 2026-06-13*
