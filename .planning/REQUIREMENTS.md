# Requirements: DataAgent — v1.1 Hardening

**Defined:** 2026-06-13
**Core Value:** Une question business en langage naturel produit un rapport correct, sourcé et visualisé — sans intervention humaine dans la boucle d'analyse.
**Source:** Code review multi-agents post-v1.0 (4 agents : Python, sécurité, archi/perf, tests).

## v1.1 Requirements

Corrections issues de la revue. Priorité : correctness boucle agent > sécurité > qualité/perf > tests.

### Correctness boucle agent (CRITICAL)

- [x] **HARD-01**: `current_step` borné — au reboucle critic, ne dépasse jamais `len(plan)-1` ; `_critic_decision` route vers synthesizer quand toutes les sous-questions sont traitées (plus de re-run de doublons jusqu'à max_iterations)
- [x] **HARD-02**: Le critic reçoit un résumé du **contenu** des findings (rows échantillonnées, anomalies, viz) — pas seulement un count — pour juger la suffisance réellement

### Sécurité (CRITICAL/HIGH)

- [x] **HARD-03**: Garde DDL/write sur le SQL généré par le LLM — rejet de `DROP/DELETE/INSERT/UPDATE/CREATE/ALTER/COPY/ATTACH/DETACH/PRAGMA/CALL` avant exécution (défense contre prompt injection via `question`)
- [x] **HARD-04**: Validation du nom de table dérivé du fichier CSV (`^[a-zA-Z_][a-zA-Z0-9_]*$`) avant interpolation DDL dans `loader.py`
- [x] **HARD-05**: Endpoint `/ask` durci — `max_length` sur `question` ; `findings` (SQL/rows) non exposés par défaut dans la réponse publique
- [x] **HARD-06**: `render.py` échappe le HTML (`html.escape`) sur `png_path` et le contenu non fiable injecté dans le HTML

### Qualité & robustesse (HIGH)

- [x] **HARD-07**: Type safety sur `response.content` — cast/guard `str` après chaque accès LLM `.content` (corrige les 5 erreurs mypy, évite crash sur réponse multi-part)
- [x] **HARD-08**: Les `except Exception` aveugles bindent l'exception et loggent avec `exc_info=True` (nodes.py stats/viz/render guards) — plus de swallow silencieux

### Performance (HIGH)

- [x] **HARD-09**: Schema DuckDB introspecté **une seule fois** par run (stocké dans le state) au lieu d'un appel par invocation de node
- [x] **HARD-10**: Factories `flash_llm()`/`pro_llm()` retournent des singletons module-level (plus de ré-instanciation ~30×/run)
- [x] **HARD-11**: API FastAPI ouvre **une** connexion DuckDB persistante au démarrage (`lifespan`) au lieu de recharger les 9 CSV à chaque requête `/ask`

### Tests (MEDIUM)

- [x] **HARD-12**: Couverture des blind spots — `__main__.py` (CLI), chemin échec exécution SQL (EXPLAIN passe / execute raise), gardes `except` stats/viz, fallback planner vide ; viser ≥85% global

## Out of Scope

| Feature | Reason |
|---------|--------|
| Rotation clé `GEMINI_API_KEY` | Action manuelle utilisateur (console Gemini), pas du code |
| Rate-limiting `/ask` (slowapi) | Reporté — déploiement public non prévu pour le portfolio v1.1 |
| Router LLM-based (vs keyword) | Amélioration, pas un bug bloquant — backlog post-v1.1 |
| Eval live 10 Q / screenshots | Items manuels v1.0 (quota/browser) |

## Traceability

| Requirement | Phase | Status |
|-------------|-------|--------|
| HARD-01 | Phase 7 | Complete |
| HARD-02 | Phase 7 | Complete |
| HARD-03 | Phase 7 | Complete |
| HARD-04 | Phase 7 | Complete |
| HARD-05 | Phase 7 | Complete |
| HARD-06 | Phase 7 | Complete |
| HARD-07 | Phase 7 | Complete |
| HARD-08 | Phase 7 | Complete |
| HARD-09 | Phase 7 | Complete |
| HARD-10 | Phase 7 | Complete |
| HARD-11 | Phase 7 | Complete |
| HARD-12 | Phase 7 | Complete |

**Coverage:**
- v1.1 requirements: 12 total
- Mapped to phases: 12 ✓
- Unmapped: 0

---
*Requirements defined: 2026-06-13 (post-v1.0 review)*
