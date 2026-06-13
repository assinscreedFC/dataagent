# DataAgent

## What This Is

Agent analyste data autonome. Tu poses une question business en langage naturel (« Quel est le CA par mois ? », « Les retards de livraison plombent-ils les avis ? »), l'agent planifie, query la data, croise les sources, et sort un rapport markdown sourcé avec visualisations. Projet portfolio (Labs SolidScale) à but d'apprentissage : agentic AI + data engineering moderne.

## Core Value

Une question business en langage naturel produit un rapport correct, sourcé et visualisé — sans intervention humaine dans la boucle d'analyse.

## Requirements

### Validated

<!-- Shipped et confirmé — J1 data layer livrée et testée 11/11, cov 100%. -->

- ✓ Chargement Olist CSV → DuckDB avec nommage ergonomique des tables — J1
- ✓ 5 queries business retournant des DataFrames Polars (revenue_by_month, top_categories, delivery_delay_vs_review, orders_by_status, avg_review_score_by_month) — J1
- ✓ Tests sur fixtures synthétiques (vraie I/O DuckDB, pas de mock) — J1

### Active

<!-- Scope en construction — jalons J2 à J4 du PLAN. Hypothèses jusqu'à livraison. -->

- [ ] Couche LLM via `langchain-google-genai` (Gemini) : Flash pour planner/router/critic, Pro pour synthesizer
- [ ] StateGraph LangGraph v1.0 : boucle planner → sql_tool → synthesizer end-to-end (J2)
- [ ] Garde-fou coût `max_iterations` câblé dans le state dès J2
- [ ] `python -m dataagent "CA total 2017 ?"` retourne une réponse correcte (J2)
- [ ] stats_tool (Polars : corrélation, agrégats, anomalies) (J3)
- [ ] viz_tool (plotly → PNG, chemin dans findings) (J3)
- [ ] Router conditional type-hinté + path_map (J3)
- [ ] Critic loop avec hard cap iterations (J3)
- [ ] Checkpointer SqliteSaver pour resumabilité (J3)
- [ ] Eval : 10 questions test, correctness mesurée (J4)
- [ ] FastAPI endpoint `/ask` (J4)
- [ ] Rapport HTML → screenshots Labs (rebrand SolidScale) (J4)

### Out of Scope

- `create_react_agent` — StateGraph manuel requis (parallel nodes, supervisor, critic loop, branching custom)
- Dataset autre qu'Olist — Olist suffit (réel, multi-tables, riche en questions business)
- Provider LLM hors Gemini — pas de clé Anthropic dispo ; Gemini retenu (free tier solide), Groq/GitHub Models en réserve
- `config_schema` LangGraph — déprécié, retiré en v2.0 ; utiliser `context_schema`

## Context

- Repo privé, séparé du portfolio.
- Stack : LangGraph v1.0 (stable oct 2025) + DuckDB + Polars + Gemini (via langchain-google-genai).
- Dataset Olist e-commerce (Kaggle `olistbr/brazilian-ecommerce`, 9 tables, ~100k commandes), CSV dans `data/raw/`.
- Findings LangGraph v1.0 vérifiés juin 2026 (voir PLAN.md) : `StateGraph.compile()` obligatoire, connexion DuckDB en `UntrackedValue` (transient, jamais checkpointée), findings accumulés via `ReducedValue`/`Annotated[list, add]`, config run-scoped via `context_schema`, router avec type hints + `path_map` obligatoire, resumabilité via `checkpointer` SqliteSaver.
- État actuel : couche data J1 livrée et testée (modules `src/dataagent/data/loader.py` + `queries.py`, tests `tests/test_loader.py` + `test_queries.py`).

## Constraints

- **Tech stack**: LangGraph v1.0, `StateGraph` manuel — la doc recommande le StateGraph manuel dès qu'on a parallel nodes/supervisor/retry custom/branching ; la critic loop coche tout.
- **Tech stack**: DuckDB + Polars pour query/transform, plotly + kaleido pour viz, FastAPI + uvicorn pour l'API.
- **LLM**: Gemini via `langchain-google-genai` — Flash (planner/router/critic, cheap+rapide), Pro (synthesizer, qualité rapport). Clés Groq + GitHub Models en réserve si quota Gemini insuffisant.
- **Coût**: `max_iterations` hard stop dans le state dès J2 — empêche boucle critic infinie.
- **Tests**: vraie I/O DuckDB sur fixtures synthétiques, jamais de mock I/O ; pytest + dataset 10 Q/R pour l'eval.

## Key Decisions

| Decision | Rationale | Outcome |
|----------|-----------|---------|
| LangGraph `StateGraph` manuel (pas `create_react_agent`) | Critic loop = parallel nodes + supervisor + retry custom + branching | — Pending |
| Connexion DuckDB en `UntrackedValue` | State transient, jamais checkpointé | — Pending |
| `max_iterations` câblé dès J2 | Garde-fou coût, hard stop boucle critic | — Pending |
| Router type-hinté + `path_map` | Évite le misroute silencieux | — Pending |
| Gemini Flash planner/critic, Gemini Pro synthesizer | Cheap sur la boucle, qualité sur le rapport final ; seul provider avec clé dispo | — Pending |
| Provider Gemini (vs Claude figé au PLAN initial) | Pas de clé Anthropic ; Gemini free tier solide, Groq/GitHub en réserve | — Pending |

## Evolution

This document evolves at phase transitions and milestone boundaries.

**After each phase transition** (via `/gsd-transition`):
1. Requirements invalidated? → Move to Out of Scope with reason
2. Requirements validated? → Move to Validated with phase reference
3. New requirements emerged? → Add to Active
4. Decisions to log? → Add to Key Decisions
5. "What This Is" still accurate? → Update if drifted

**After each milestone** (via `/gsd-complete-milestone`):
1. Full review of all sections
2. Core Value check — still the right priority?
3. Audit Out of Scope — reasons still valid?
4. Update Context with current state

---
*Last updated: 2026-06-13 after initialization*
