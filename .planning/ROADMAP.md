# Roadmap: DataAgent

## Milestones

- ✅ **v1.0 — Agent LangGraph complet (J2-J4)** — Phases 1-6 (shipped 2026-06-13) — voir [`milestones/v1.0-ROADMAP.md`](milestones/v1.0-ROADMAP.md)
- 🚧 **v1.1 — Hardening** — Phase 7 (corrections code review post-v1.0)

## Phases

<details>
<summary>✅ v1.0 — Agent LangGraph complet (Phases 1-6) — SHIPPED 2026-06-13</summary>

- [x] Phase 1: State Foundation & Minimal Graph (3/3 plans) — 2026-06-13
- [x] Phase 2: SQL Tool Hardening (1/1 plan) — 2026-06-13
- [x] Phase 3: Stats & Viz Tools (2/2 plans) — 2026-06-13
- [x] Phase 4: Router & Critic Loop (2/2 plans) — 2026-06-13
- [x] Phase 5: Resumability (1/1 plan) — 2026-06-13
- [x] Phase 6: Eval, API & Demo (3/3 plans) — 2026-06-13

Détails complets : [`milestones/v1.0-ROADMAP.md`](milestones/v1.0-ROADMAP.md)

</details>

### 🚧 v1.1 — Hardening

- [ ] **Phase 7: Hardening & Bug Fixes** - Corrige les findings critiques de la revue : boucle agent (current_step/critic), sécurité SQL, qualité/perf, tests

## Phase Details

### Phase 7: Hardening & Bug Fixes
**Goal**: Corriger les bugs critiques et durcir le code identifiés par la revue multi-agents post-v1.0, sans changer le comportement nominal de l'agent.
**Depends on**: v1.0 (Phases 1-6 shipped)
**Requirements**: HARD-01, HARD-02, HARD-03, HARD-04, HARD-05, HARD-06, HARD-07, HARD-08, HARD-09, HARD-10, HARD-11, HARD-12
**Success Criteria** (what must be TRUE):
  1. `current_step` ne dépasse jamais `len(plan)-1` ; une question multi-étapes ne re-run plus la même sous-question jusqu'à max_iterations (test dédié)
  2. Le critic reçoit le contenu des findings et peut décider de synthétiser avant max_iterations
  3. Un SQL contenant DROP/DELETE/COPY/etc. est rejeté avant exécution (test dédié)
  4. Un nom de table CSV non conforme est rejeté/sanitizé dans loader
  5. `/ask` borne la longueur de question et n'expose pas les findings bruts par défaut ; render échappe le HTML
  6. mypy ne signale plus d'erreur sur `response.content` ; les except bindent et loggent
  7. schema introspecté une fois/run, LLM singletons, API conn persistante (lifespan)
  8. Couverture ≥85% global, blind spots couverts (__main__, échec exec SQL, gardes except)
  9. La suite de tests passe (aucune régression sur les 163 tests existants)
**Plans**: 4 plans (3 waves)

Plans:
- [x] 07-01-PLAN.md — Boucle agent core + perf schema : current_step borné (D-01), critic early-exit (D-02), critic contenu (D-03), _as_text (D-08), except bindés (D-09), schema 1×/run (D-10) [nodes/graph/state]
- [x] 07-02-PLAN.md — Sécurité : write/DDL guard (D-04), validation nom de table loader (D-05), /ask durci + lifespan conn persistante (D-06/D-12), html.escape (D-07)
- [ ] 07-03-PLAN.md — Perf : singletons flash_llm/pro_llm (D-11) [llm.py]
- [ ] 07-04-PLAN.md — Tests : blind spots CLI/exec-failure/except/planner-empty/write-guard/current_step/critic-content + MAJ terminaison D-01/D-02, ≥85% couverture (D-13)

## Progress

**Execution Order:** Phases execute in numeric order.

| Phase | Milestone | Plans | Status | Completed |
|-------|-----------|-------|--------|-----------|
| 1. State Foundation & Minimal Graph | v1.0 | 3/3 | Complete | 2026-06-13 |
| 2. SQL Tool Hardening | v1.0 | 1/1 | Complete | 2026-06-13 |
| 3. Stats & Viz Tools | v1.0 | 2/2 | Complete | 2026-06-13 |
| 4. Router & Critic Loop | v1.0 | 2/2 | Complete | 2026-06-13 |
| 5. Resumability | v1.0 | 1/1 | Complete | 2026-06-13 |
| 6. Eval, API & Demo | v1.0 | 3/3 | Complete | 2026-06-13 |
| 7. Hardening & Bug Fixes | v1.1 | 2/4 | In Progress|  |

---
*Milestone v1.0 shipped 2026-06-13 — 6 phases, 12 plans, 163 tests.*
*v1.1 Hardening in progress — Phase 7 (12 requirements from code review, 4 plans / 3 waves).*
