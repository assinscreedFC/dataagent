# Requirements: DataAgent

**Defined:** 2026-06-13
**Core Value:** Une question business en langage naturel produit un rapport correct, sourcé et visualisé — sans intervention humaine dans la boucle d'analyse.

## v1 Requirements

Requirements pour l'agent complet (jalons J2→J4). J1 data layer déjà validée (voir PROJECT.md).

### Graph (boucle agent end-to-end — J2)

- [x] **GRAPH-01**: Le state `AgentState` (TypedDict) porte question, plan, findings (reducer `add`), messages, iterations, max_iterations, db (`UntrackedValue`), report
- [x] **GRAPH-02**: Un `StateGraph` compilé câble planner → sql_tool → synthesizer end-to-end
- [x] **GRAPH-03**: Le node planner (Gemini Flash) décompose la question en sous-questions `plan[]`
- [x] **GRAPH-04**: Le node synthesizer (Gemini Pro) produit un rapport markdown sourcé
- [x] **GRAPH-05**: `max_iterations` est câblé dans le state dès J2 comme hard stop
- [x] **GRAPH-06**: `python -m dataagent "CA total 2017 ?"` retourne une réponse correcte

### Tools (multi-tool + critic — J3)

- [x] **TOOL-01**: sql_tool génère du SQL, le valide sur le schema DuckDB avant exec, retry sur erreur, push findings
- [x] **TOOL-02**: stats_tool calcule corrélations, agrégats et détecte les anomalies via Polars
- [x] **TOOL-03**: viz_tool produit un PNG plotly et enregistre son chemin dans findings
- [x] **TOOL-04**: Le router (conditional edge) est type-hinté avec `path_map` et choisit le tool selon la sous-question courante
- [x] **TOOL-05**: Le node critic (Gemini Flash) juge si les findings suffisent, reboucle ou synthétise, et incrémente iterations
- [x] **TOOL-06**: La critic loop s'arrête au hard cap `max_iterations`
- [x] **TOOL-07**: Un `checkpointer` SqliteSaver rend le run resumable
- [x] **TOOL-08**: Une question complexe produit un rapport multi-source avec graphe

### Eval & API (J4)

- [ ] **EVAL-01**: Un jeu de 10 questions test mesure la correctness des réponses
- [ ] **API-01**: Un endpoint FastAPI `/ask` accepte une question et retourne le rapport
- [ ] **DEMO-01**: Le rapport est rendu en HTML et capturé en screenshots pour Labs (rebrand SolidScale)

## v2 Requirements

(Aucun pour l'instant — scope cadré sur l'agent complet J2→J4.)

## Out of Scope

| Feature | Reason |
|---------|--------|
| `create_react_agent` | StateGraph manuel requis (parallel nodes, supervisor, critic loop, branching) |
| Dataset hors Olist | Olist suffit (réel, multi-tables, riche en questions business) |
| Provider LLM hors Gemini | Pas de clé Anthropic ; Gemini retenu, Groq/GitHub Models en réserve |
| `config_schema` LangGraph | Déprécié, retiré en v2.0 — utiliser `context_schema` |

## Traceability

| Requirement | Phase | Status |
|-------------|-------|--------|
| GRAPH-01 | Phase 1 | Complete |
| GRAPH-02 | Phase 1 | Complete |
| GRAPH-03 | Phase 1 | Complete |
| GRAPH-04 | Phase 1 | Complete |
| GRAPH-05 | Phase 1 | Complete |
| GRAPH-06 | Phase 1 | Complete |
| TOOL-01 | Phase 2 | Complete |
| TOOL-02 | Phase 3 | Complete |
| TOOL-03 | Phase 3 | Complete |
| TOOL-04 | Phase 4 | Complete |
| TOOL-05 | Phase 4 | Complete |
| TOOL-06 | Phase 4 | Complete |
| TOOL-07 | Phase 5 | Complete |
| TOOL-08 | Phase 4 | Complete |
| EVAL-01 | Phase 6 | Pending |
| API-01 | Phase 6 | Pending |
| DEMO-01 | Phase 6 | Pending |

**Coverage:**
- v1 requirements: 17 total
- Mapped to phases: 17 ✓
- Unmapped: 0

---
*Requirements defined: 2026-06-13*
*Last updated: 2026-06-13 after roadmap creation*
