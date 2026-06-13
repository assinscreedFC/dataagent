# Roadmap: DataAgent

## Overview

La couche data J1 (DuckDB + 5 queries Polars) est déjà livrée et testée. Ce roadmap couvre l'agent complet (jalons J2→J4) : on pose d'abord le state schema LangGraph et la boucle minimale planner→sql_tool→synthesizer end-to-end (J2), on durcit le sql_tool (validation schema + retry), on ajoute les tools stats et viz en parallèle, on câble le router conditionnel et la critic loop avec hard cap (J3), on rend le run resumable via checkpointer, puis on ferme avec l'eval correctness, l'API FastAPI `/ask` et la demo Labs (J4). L'ordre suit strictement les dépendances LangGraph : rien ne se branche avant que le state et le graphe minimal existent.

## Phases

**Phase Numbering:**
- Integer phases (1, 2, 3): Planned milestone work
- Decimal phases (2.1, 2.2): Urgent insertions (marked with INSERTED)

Decimal phases appear between their surrounding integers in numeric order.

- [ ] **Phase 1: State Foundation & Minimal Graph** - State schema + boucle planner→sql_tool→synthesizer end-to-end (J2)
- [ ] **Phase 2: SQL Tool Hardening** - sql_tool valide la query sur le schema DuckDB et retry sur erreur
- [ ] **Phase 3: Stats & Viz Tools** - stats_tool (corrélation/anomalies) + viz_tool (PNG plotly), parallélisables
- [ ] **Phase 4: Router & Critic Loop** - Router type-hinté + critic loop avec hard cap, rapport multi-source (J3)
- [ ] **Phase 5: Resumability** - Checkpointer SqliteSaver pour runs resumables
- [ ] **Phase 6: Eval, API & Demo** - Eval 10 Q/R, endpoint FastAPI `/ask`, rapport HTML + screenshots Labs (J4)

## Phase Details

### Phase 1: State Foundation & Minimal Graph
**Goal**: L'agent répond correctement à une question simple via une boucle LangGraph minimale end-to-end, avec le garde-fou coût câblé dès le départ.
**Depends on**: Nothing (data layer J1 already shipped)
**Requirements**: GRAPH-01, GRAPH-02, GRAPH-03, GRAPH-04, GRAPH-05, GRAPH-06
**Success Criteria** (what must be TRUE):
  1. `python -m dataagent "CA total 2017 ?"` retourne une réponse correcte
  2. Le rapport produit est en markdown et cite ses sources (tables/queries utilisées)
  3. Le state porte `max_iterations` comme hard stop, observable dans le run
  4. La connexion DuckDB vit dans le state en `UntrackedValue` (jamais checkpointée)
  5. Le planner décompose la question en sous-questions `plan[]` visibles dans le state
**Plans**: TBD

### Phase 2: SQL Tool Hardening
**Goal**: Le sql_tool ne casse plus sur du SQL halluciné — il valide contre le schema réel avant exec et retry sur erreur.
**Depends on**: Phase 1
**Requirements**: TOOL-01
**Success Criteria** (what must be TRUE):
  1. Une query SQL référençant une colonne/table inexistante est rejetée avant exécution
  2. Sur erreur d'exécution, le tool retry au moins une fois avec une query corrigée
  3. Le résultat d'une query valide est poussé dans `findings` avec sa source
  4. Une question dont le SQL initial échoue finit quand même par produire un finding correct
**Plans**: TBD

### Phase 3: Stats & Viz Tools
**Goal**: L'agent dispose de deux nouveaux tools — analyse statistique (Polars) et visualisation (plotly) — qui enrichissent les findings.
**Depends on**: Phase 1
**Requirements**: TOOL-02, TOOL-03
**Success Criteria** (what must be TRUE):
  1. stats_tool calcule une corrélation entre deux séries et la pousse dans findings
  2. stats_tool détecte au moins une anomalie sur une série connue de fixtures
  3. viz_tool produit un fichier PNG plotly sur disque
  4. Le chemin du PNG généré est enregistré dans findings
**Plans**: TBD
**UI hint**: yes

### Phase 4: Router & Critic Loop
**Goal**: L'agent oriente dynamiquement vers le bon tool et reboucle jusqu'à ce que les findings suffisent, dans la limite du hard cap — produisant un rapport multi-source.
**Depends on**: Phase 2, Phase 3
**Requirements**: TOOL-04, TOOL-05, TOOL-06, TOOL-08
**Success Criteria** (what must be TRUE):
  1. Le router (conditional edge type-hinté + `path_map`) dirige chaque sous-question vers sql/stats/viz
  2. Le critic juge les findings, reboucle si insuffisants et incrémente `iterations`
  3. La boucle s'arrête à `max_iterations` même si le critic n'est pas satisfait (pas de boucle infinie)
  4. Une question complexe produit un rapport markdown multi-source incluant un graphe
**Plans**: TBD

### Phase 5: Resumability
**Goal**: Un run interrompu peut reprendre là où il s'est arrêté grâce au checkpointer.
**Depends on**: Phase 4
**Requirements**: TOOL-07
**Success Criteria** (what must be TRUE):
  1. Le graphe est compilé avec un `checkpointer` SqliteSaver
  2. Un run identifié par thread_id écrit son état dans le store SQLite
  3. Relancer le même thread_id reprend l'état au lieu de repartir de zéro
**Plans**: TBD

### Phase 6: Eval, API & Demo
**Goal**: La correctness de l'agent est mesurée, exposée via une API, et la demo Labs est capturée.
**Depends on**: Phase 5
**Requirements**: EVAL-01, API-01, DEMO-01
**Success Criteria** (what must be TRUE):
  1. Un jeu de 10 questions test tourne et rapporte un score de correctness
  2. `POST /ask` avec une question retourne le rapport généré
  3. Le rapport est rendu en HTML
  4. Des screenshots du rapport (rebrand SolidScale) sont produits pour Labs
**Plans**: TBD
**UI hint**: yes

## Progress

**Execution Order:**
Phases execute in numeric order: 1 → 2 → 3 → 4 → 5 → 6

| Phase | Plans Complete | Status | Completed |
|-------|----------------|--------|-----------|
| 1. State Foundation & Minimal Graph | 0/TBD | Not started | - |
| 2. SQL Tool Hardening | 0/TBD | Not started | - |
| 3. Stats & Viz Tools | 0/TBD | Not started | - |
| 4. Router & Critic Loop | 0/TBD | Not started | - |
| 5. Resumability | 0/TBD | Not started | - |
| 6. Eval, API & Demo | 0/TBD | Not started | - |

---
*Roadmap created: 2026-06-13*
*Coverage: 17/17 v1 requirements mapped*
