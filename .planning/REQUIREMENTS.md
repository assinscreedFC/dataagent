# Requirements: DataAgent

**Defined:** 2026-06-13
**Core Value:** Une question business en langage naturel produit un rapport correct, sourcé et visualisé — sans intervention humaine dans la boucle d'analyse.

## v1 Requirements

Requirements pour l'agent complet (jalons J2→J4). J1 data layer déjà validée (voir PROJECT.md).

### Graph (boucle agent end-to-end — J2)

- [ ] **GRAPH-01**: Le state `AgentState` (TypedDict) porte question, plan, findings (reducer `add`), messages, iterations, max_iterations, db (`UntrackedValue`), report
- [ ] **GRAPH-02**: Un `StateGraph` compilé câble planner → sql_tool → synthesizer end-to-end
- [ ] **GRAPH-03**: Le node planner (Haiku) décompose la question en sous-questions `plan[]`
- [ ] **GRAPH-04**: Le node synthesizer (Opus) produit un rapport markdown sourcé
- [ ] **GRAPH-05**: `max_iterations` est câblé dans le state dès J2 comme hard stop
- [ ] **GRAPH-06**: `python -m dataagent "CA total 2017 ?"` retourne une réponse correcte

### Tools (multi-tool + critic — J3)

- [ ] **TOOL-01**: sql_tool génère du SQL, le valide sur le schema DuckDB avant exec, retry sur erreur, push findings
- [ ] **TOOL-02**: stats_tool calcule corrélations, agrégats et détecte les anomalies via Polars
- [ ] **TOOL-03**: viz_tool produit un PNG plotly et enregistre son chemin dans findings
- [ ] **TOOL-04**: Le router (conditional edge) est type-hinté avec `path_map` et choisit le tool selon la sous-question courante
- [ ] **TOOL-05**: Le node critic (Haiku) juge si les findings suffisent, reboucle ou synthétise, et incrémente iterations
- [ ] **TOOL-06**: La critic loop s'arrête au hard cap `max_iterations`
- [ ] **TOOL-07**: Un `checkpointer` SqliteSaver rend le run resumable
- [ ] **TOOL-08**: Une question complexe produit un rapport multi-source avec graphe

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
| LLM hors Claude | Haiku + Opus figés |
| `config_schema` LangGraph | Déprécié, retiré en v2.0 — utiliser `context_schema` |

## Traceability

| Requirement | Phase | Status |
|-------------|-------|--------|
| GRAPH-01 | TBD | Pending |
| GRAPH-02 | TBD | Pending |
| GRAPH-03 | TBD | Pending |
| GRAPH-04 | TBD | Pending |
| GRAPH-05 | TBD | Pending |
| GRAPH-06 | TBD | Pending |
| TOOL-01 | TBD | Pending |
| TOOL-02 | TBD | Pending |
| TOOL-03 | TBD | Pending |
| TOOL-04 | TBD | Pending |
| TOOL-05 | TBD | Pending |
| TOOL-06 | TBD | Pending |
| TOOL-07 | TBD | Pending |
| TOOL-08 | TBD | Pending |
| EVAL-01 | TBD | Pending |
| API-01 | TBD | Pending |
| DEMO-01 | TBD | Pending |

**Coverage:**
- v1 requirements: 17 total
- Mapped to phases: 0 (rempli par le roadmap)
- Unmapped: 17 ⚠️

---
*Requirements defined: 2026-06-13*
*Last updated: 2026-06-13 after initial definition*
