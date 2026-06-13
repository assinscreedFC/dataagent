# Roadmap: DataAgent

## Milestones

- ✅ **v1.0 — Agent LangGraph complet (J2-J4)** — Phases 1-6 (shipped 2026-06-13) — voir [`milestones/v1.0-ROADMAP.md`](milestones/v1.0-ROADMAP.md)
- ✅ **v1.1 — Hardening** — Phase 7 (shipped 2026-06-13) — voir [`milestones/v1.1-ROADMAP.md`](milestones/v1.1-ROADMAP.md)

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

<details>
<summary>✅ v1.1 — Hardening (Phase 7) — SHIPPED 2026-06-13</summary>

- [x] Phase 7: Hardening & Bug Fixes (4/4 plans) — 2026-06-13
  - Corrections code review multi-agents : current_step borné + critic content (boucle agent), garde SQL write/DDL + validation table + /ask durci + html.escape (sécurité), _as_text + except bindés (robustesse), schema 1×/run + LLM singletons + API lifespan (perf), blind spots tests (cov 94%, 248 tests).

Détails complets : [`milestones/v1.1-ROADMAP.md`](milestones/v1.1-ROADMAP.md)

</details>

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
| 7. Hardening & Bug Fixes | v1.1 | 4/4 | Complete   | 2026-06-13 |

---
*Milestone v1.0 shipped 2026-06-13 — 6 phases, 12 plans, 163 tests.*
*Milestone v1.1 Hardening shipped 2026-06-13 — Phase 7, 4 plans, 12 reqs, 248 tests, cov 94%.*
*Next milestone: `/gsd-new-milestone`*
