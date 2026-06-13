**Requirements**: GRAPH-01, GRAPH-02, GRAPH-03, GRAPH-04, GRAPH-05, GRAPH-06
**Success Criteria** (what must be TRUE):
  1. `python -m dataagent "CA total 2017 ?"` retourne une réponse correcte
  2. Le rapport produit est en markdown et cite ses sources (tables/queries utilisées)
  3. Le state porte `max_iterations` comme hard stop, observable dans le run
  4. La connexion DuckDB vit dans le state en `UntrackedValue` (jamais checkpointée)
  5. Le planner décompose la question en sous-questions `plan[]` visibles dans le state
**Plans**: 3 plans
  - [x] 01-01-PLAN.md — Fondations : config Gemini + AgentState (8 champs, db UntrackedValue) + factory LLM
  - [x] 01-02-PLAN.md — Nodes : planner (Flash) + sql_tool minimal + synthesizer (Pro) + introspection schema
  - [ ] 01-03-PLAN.md — Graph compilé linéaire + CLI `python -m dataagent` + test end-to-end