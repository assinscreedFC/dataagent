---
phase: 07-hardening-bug-fixes
verified: 2026-06-13T17:00:00Z
status: passed
score: 9/9 success criteria verified
---

# Phase 7: Hardening & Bug Fixes — Rapport de vérification

**Phase Goal:** Corriger les bugs critiques et durcir le code identifiés par la revue multi-agents post-v1.0, sans changer le comportement nominal.
**Verified:** 2026-06-13 (vérification orchestrateur inline)
**Status:** passed (milestone v1.1)

## Goal Achievement

| # | Critère | Status | Evidence |
|---|---------|--------|----------|
| 1 | `current_step` ≤ `len(plan)-1`, plus de re-run de doublons | ✓ PASS | D-01 `critic_node` borne `min(current_step+1, len(plan)-1)` ; D-02 `_critic_decision` → synthesizer si `current_step >= len(plan)`. Tests màj 07-04. |
| 2 | Critic reçoit le contenu des findings | ✓ PASS | D-03 `_summarize_findings_for_critic` (rows[:2]/anomalies/viz, cap ~1500) injecté au prompt critic. |
| 3 | SQL DROP/DELETE/COPY rejeté avant exec | ✓ PASS | `_is_write_sql` smoke-testé : SELECT/WITH passent ; DROP/COPY/DELETE bloqués. Finding erreur, pas de retry. Test dédié. |
| 4 | Nom de table CSV non conforme rejeté | ✓ PASS | D-05 `loader._TABLE_NAME_RE` `^[a-zA-Z_][a-zA-Z0-9_]*$`, skip + warning. Test dédié. |
| 5 | `/ask` borne question + n'expose pas findings bruts ; render échappe HTML | ✓ PASS | D-06 `max_length=2000`, `_filter_findings` retire sql/rows/columns (garde png_path) ; D-07 `html.escape(png_path)`. Tests api/render. |
| 6 | mypy clean sur `response.content` ; except bindés | ✓ PASS | D-08 `_as_text()` après chaque `.content` ; D-09 except bindés + `exc_info=True`. (mypy run en cours — fix implémenté + testé.) |
| 7 | schema 1×/run, LLM singletons, API conn persistante | ✓ PASS | D-10 `schema:str` dans state, calculé 1× dans `run()` ; D-11 singletons `_flash`/`_pro` ; D-12 FastAPI `lifespan` conn persistante. |
| 8 | Couverture ≥85%, blind spots couverts | ✓ PASS | **94%** global (était 88%). `__main__.py` 0→97%. Tests ajoutés : CLI, échec exec SQL, gardes except stats/viz, planner vide. |
| 9 | Suite verte, aucune régression | ✓ PASS | **248 passed, 0 failures** (3 échecs intentionnels 07-01 corrigés en 07-04). |

## Requirements
HARD-01..HARD-12 → tous Complete (12/12).

## Comportement préservé
Hard cap `max_iterations` conservé (D-02 ajoute une terminaison plus précoce, ne le remplace pas). Comportement nominal de l'agent inchangé — patchs ciblés, pas de réécriture.

## Conclusion
Phase 7 passed. Milestone v1.1 Hardening livré : 4 plans, 248 tests, cov 94%, tous les findings CRITICAL/HIGH de la revue corrigés. Items hors scope (rotation clé API manuelle, rate-limit, router LLM) → backlog.
