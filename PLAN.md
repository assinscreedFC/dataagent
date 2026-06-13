# DataAgent — Plan

Agent analyste data autonome. Tu poses une question business en langage naturel, l'agent planifie, query la data, croise les sources, sort un rapport sourcé avec graphes.

Projet portfolio (Labs SolidScale) à but d'apprentissage : **agentic AI + data engineering moderne**.

## Décisions figées

- Repo privé, séparé du portfolio.
- **LangGraph v1.0** (stable oct 2025), `StateGraph` manuel — pas `create_react_agent`. Justification : la doc recommande le StateGraph manuel dès qu'on a parallel nodes, supervisor, retry custom ou branching complexe ; notre critic loop coche tout.
- **Dataset** : Olist e-commerce (Kaggle, 9 tables, ~100k commandes). Réel, multi-tables, riche en questions business.
- **LLM** : Gemini (via `langchain-google-genai`). Flash → planner/router/critic (cheap, rapide). Pro → synthesizer (qualité rapport). _(Décision révisée 2026-06-13 : pas de clé Anthropic dispo ; Gemini free tier retenu, Groq + GitHub Models en réserve. Claude était figé au plan initial.)_
- **Garde-fou coût** : `max_iterations` dans le state dès J2. Hard stop boucle critic.

## Findings LangGraph v1.0 (vérifiés juin 2026)

| Sujet | Décision |
|-------|----------|
| Builder | `StateGraph` puis `.compile()` (obligatoire avant exec) |
| Connexion DuckDB dans le state | `UntrackedValue` — state transient jamais checkpointé |
| Accumuler findings sur la boucle | `ReducedValue` / `Annotated[list, add]` reducer |
| Config run-scoped | `context_schema` (le `config_schema` est déprécié, retiré en v2.0) |
| Router | type hints sur le return + `path_map` obligatoire (sinon misroute silencieux) |
| Resumabilité | `checkpointer` SqliteSaver |

Sources : github.com/langchain-ai/langgraph/releases, reference.langchain.com StateGraph, doc best-practices 2026.

## State schema (cœur)

```python
class AgentState(TypedDict):
    question: str                          # question business user
    plan: list[str]                        # sous-questions du planner
    findings: Annotated[list[dict], add]   # accumule sur la boucle
    messages: Annotated[list, add_messages]
    iterations: int                        # garde-fou boucle critic
    max_iterations: int                    # hard cap (ex: 5)
    db: UntrackedValue[DuckDBConn]         # connexion, jamais checkpointée
    report: str                            # output final
```

## Graphe

```
START -> planner -> router -+-> sql_tool ---+
                            +-> stats_tool -+-> critic -> (cond) -+-> router (reboucle si manque + iters<max)
                            +-> viz_tool ---+                     +-> synthesizer -> END
```

- **planner** (Gemini Flash) : décompose la question -> `plan[]`
- **router** (conditional edge, type-hinté + path_map) : choisit le tool selon la sous-question courante
- **sql_tool** : génère SQL, valide sur le schema DuckDB, exécute, push findings
- **stats_tool** : Polars (corrélation, agrégats, détection anomalie)
- **viz_tool** : plotly -> PNG sauvé, chemin dans findings
- **critic** (Gemini Flash) : findings suffisants ? reboucle ou synth. Incrémente `iterations`.
- **synthesizer** (Gemini Pro) : rapport markdown sourcé + graphes

## Stack

| Couche | Lib | Version cible |
|--------|-----|---------------|
| Agent | langgraph | ^1.0 |
| LLM | langchain-google-genai | latest |
| Query | duckdb | latest |
| Transform | polars | latest |
| Viz | plotly + kaleido | latest |
| API | fastapi + uvicorn | latest |
| Checkpoint | langgraph SqliteSaver | inclus |
| Eval | pytest + dataset 10 Q/R | — |

## Jalons

### J1 — Data layer nu (zéro IA) [EN COURS]
- Charge Olist dans DuckDB
- 5 queries business (Polars output)
- Tests sur fixtures synthétiques (vraie I/O DuckDB, pas de mock)
- Sortie : module `data/` testé, pas d'agent

### J2 — Agent single-tool, boucle bout-en-bout
- StateGraph : planner -> sql_tool -> synthesizer (pas de critic)
- 1 question simple end-to-end
- `max_iterations` câblé dès maintenant
- Sortie : `python -m dataagent "CA total 2017 ?"` -> réponse correcte

### J3 — Multi-tool + critic loop
- Ajoute stats_tool, viz_tool
- Router conditional (type-hinté + path_map)
- Critic loop avec hard cap
- Sortie : question complexe -> rapport multi-source + graphe

### J4 — Eval + polish + demo Labs
- 10 questions test, eval correctness
- FastAPI endpoint `/ask`
- Rapport HTML -> screenshots Labs (rebrand SolidScale)

## Risques cadrés

| Risque | Mitigation (dès J2) |
|--------|---------------------|
| Boucle critic infinie / coût explose | `max_iterations` hard stop dans le state |
| SQL halluciné | tool valide la query sur le schema DuckDB avant exec, retry sur erreur |
| Misroute silencieux router | type hints + `path_map` |
| State non reproductible | `checkpointer` SqliteSaver |

## Dataset — setup

Télécharger Olist depuis Kaggle (`olistbr/brazilian-ecommerce`) et déposer les CSV dans `data/raw/`. Le loader détecte tous les `*.csv` du dossier.
