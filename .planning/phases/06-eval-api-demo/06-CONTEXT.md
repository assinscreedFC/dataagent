# Phase 6: Eval, API & Demo - Context

**Gathered:** 2026-06-13 (auto mode — recommended defaults from PLAN.md, phase finale J4)
**Status:** Ready for planning

<domain>
## Phase Boundary

Ferme le projet (J4) : (1) une eval mesure la correctness de l'agent sur un jeu de 10 questions, (2) un endpoint FastAPI `POST /ask` expose l'agent, (3) le rapport est rendu en HTML (rebrand SolidScale) et capturable en screenshots pour Labs. Couvre EVAL-01, API-01, DEMO-01. Dernière phase du milestone.

</domain>

<decisions>
## Implementation Decisions

### Eval (EVAL-01)
- **D-01:** Jeu de 10 questions test dans un fichier versionné (`src/dataagent/eval/questions.py` ou `eval/dataset.json`) : chaque entrée = `{question, expected_keywords}` (ex. mots-clés/tables/ordre de grandeur attendus dans le rapport). Questions business réalistes sur Olist (CA, catégories, délais, avis…).
- **D-02:** Le harness d'eval (`src/dataagent/eval/runner.py`) exécute l'agent sur chaque question et **score la correctness** : présence des `expected_keywords` dans le rapport (score = ratio matché). Rapporte un score agrégé.
- **D-03:** Garde-fou quota : le harness est entièrement **testable avec LLM mocké** (les tests ne consomment pas de quota Gemini). Le run live réel sur les 10 questions consomme beaucoup de quota free tier → exécuté en échantillon / manuel (item human-verify), pas dans la CI. Le code du harness + son scoring sont prouvés par tests mockés.

### API (API-01)
- **D-04:** App FastAPI (`src/dataagent/api.py`) avec `POST /ask` : body `{"question": str}` → exécute l'agent (`run()`) → retourne `{"report": str, "findings": [...]}` (et le `png_path` si présent). Lance la connexion DuckDB par requête (ou app-scoped). Health check `GET /health`.
- **D-05:** Testé via `fastapi.testclient.TestClient` avec l'agent/LLM mocké (pas de quota). Valide : 200 + report non vide sur question valide, 422/400 sur body invalide.

### Demo HTML & screenshots (DEMO-01)
- **D-06:** Renderer `src/dataagent/render.py` : markdown du rapport → HTML standalone stylé (rebrand SolidScale : palette sobre, typographie propre, images de graphes embarquées via les `png_path` des findings viz). Sauvé dans `reports/*.html`.
- **D-07:** Screenshots : le rendu HTML est le livrable automatisable + testable (fichier HTML produit, contient le rapport + images). La capture screenshot réelle pour Labs nécessite un navigateur headless → item manuel/human-verify (ouvrir le HTML, capturer), documenté. Ne pas bloquer la CI dessus.

### Claude's Discretion
- Choix lib markdown→HTML (markdown / mistune déjà présents dans l'écosystème, ou rendu simple), CSS exact SolidScale, structure du dataset eval, scoping connexion DuckDB dans l'API (par requête vs lifespan), format du rapport d'eval.

</decisions>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### Architecture
- `PLAN.md` §Jalons J4 : "10 questions test, eval correctness", "FastAPI endpoint /ask", "Rapport HTML -> screenshots Labs (rebrand SolidScale)". §Stack : fastapi + uvicorn (déjà installés).

### Code à réutiliser
- `src/dataagent/agent/graph.py` — `run(question, conn=None, thread_id=None)` : point d'entrée appelé par l'eval ET l'API.
- `src/dataagent/data/loader.py` — `connect()` + `load_csvs_to_duckdb()` pour la connexion (eval + API).
- `src/dataagent/agent/nodes.py` — les findings (incl. `png_path` viz) consommés par le renderer HTML.
- `src/dataagent/config.py` — `REPORTS` (dossier HTML/PNG), modèles Gemini.
- `tests/conftest.py` — fixtures DuckDB + pattern mock LLM.

### Branding
- Skill `solidscale-voice` (référence ton/brand SolidScale) — pour le wording/titre de la demo si pertinent ; le CSS reste sobre et pro.

</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets
- `run()` (graph.py) : appelé par eval runner ET endpoint API.
- `loader` : connexion DuckDB.
- Findings viz `png_path` : images à embarquer dans le HTML.
- fastapi + uvicorn + TestClient installés et importables.

### Established Patterns
- Tests : LLM mocké (pas de quota), I/O réelle (HTML écrit sur disque, TestClient réel). Eval/API/render tous testables sans appel Gemini réel.
- Mock LLM déterministe pour scorer l'eval sur un rapport connu.

### Integration Points
- Nouveaux modules : `eval/` (dataset + runner), `api.py` (FastAPI), `render.py` (markdown→HTML). Consomment `run()` et les findings. Aucune modif du graphe ni des nodes.
- `reports/` (gitignored html/png) pour les sorties demo.

</code_context>

<specifics>
## Specific Ideas

- Quota Gemini free tier serré → l'eval live (10 runs × boucle) est un item manuel/échantillonné, le harness est prouvé par tests mockés. Idem screenshots (navigateur headless = manuel).
- Rebrand SolidScale : HTML sobre et pro, graphes embarqués — c'est la vitrine portfolio Labs.

</specifics>

<deferred>
## Deferred Ideas

- Aucune — dernière phase du milestone v1.0. Idées futures → backlog post-milestone.

</deferred>

---

*Phase: 06-eval-api-demo*
*Context gathered: 2026-06-13*
