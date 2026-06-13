# Phase 7: Hardening & Bug Fixes - Context

**Gathered:** 2026-06-13 (auto mode — décisions issues de la revue code multi-agents post-v1.0)
**Status:** Ready for planning

<domain>
## Phase Boundary

Corrige les findings de la revue code (4 agents) sur le code v1.0 livré, sans changer le comportement nominal de l'agent. Couvre HARD-01..12. Regroupe : 2 bugs CRITICAL de la boucle agent, le durcissement sécurité du chemin SQL/API/render, la robustesse typage/exceptions, 3 optimisations perf, et le comblement des blind spots de tests. Aucune nouvelle feature. HORS scope : rotation clé API (manuel), rate-limiting, router LLM-based, eval live.

</domain>

<decisions>
## Implementation Decisions

### Boucle agent — correctness (HARD-01, HARD-02)
- **D-01:** `critic_node` borne l'avancement : `next_step = min(current_step + 1, len(plan) - 1)` si `plan` non vide, sinon 0. Plus de dépassement de `plan[]`.
- **D-02:** `_critic_decision` (graph.py) route vers `synthesizer` dès que toutes les sous-questions sont traitées : ajouter `if current_step >= len(plan): return "synthesizer"` **avant** le check `iterations >= max_iterations` (en plus du hard cap existant, qui reste). Évite de re-run la dernière sous-question en boucle.
- **D-03:** Le critic reçoit le **contenu** des findings, pas juste un count. Helper `_summarize_findings_for_critic(findings) -> str` : pour chaque finding, ligne courte (sql → subquestion + `rows[:2]` ; stats → analyse + colonnes/valeur ; viz → png généré). Cappé ~1500 chars. Injecté dans le prompt critic à la place du `"N finding(s) — sources: ..."`.

### Sécurité (HARD-03, HARD-04, HARD-05, HARD-06)
- **D-04:** Garde write/DDL sur le SQL LLM. Constante `SQL_FORBIDDEN_KEYWORDS` (config) : `DROP, DELETE, INSERT, UPDATE, CREATE, ALTER, COPY, ATTACH, DETACH, PRAGMA, CALL, REPLACE, TRUNCATE`. Helper `_is_write_sql(sql) -> bool` (regex word-boundary, case-insensitive). Dans `_execute_subquestion`, **avant** validation/exécution : si write détecté → ne pas exécuter, pousser finding d'erreur "SQL non autorisé (write/DDL bloqué)", pas de retry sur ce motif. Seuls SELECT/WITH/EXPLAIN passent.
- **D-05:** `loader.py` valide le nom de table dérivé du CSV contre `^[a-zA-Z_][a-zA-Z0-9_]*$` avant interpolation DDL. Nom non conforme → skip du fichier + warning loggé (ne crash pas tout le chargement). Helper réutilise/durcit `table_name()`.
- **D-06:** `/ask` : `AskRequest.question` gagne `max_length=2000` (en plus de `min_length=1`). La réponse par défaut ne renvoie **pas** les findings bruts : champ `report` toujours présent + `findings` filtré (retirer `sql`, `rows`, `columns` ; garder `source`, `subquestion`, `tables`, `png_path`, `analysis`). Optionnel : query param `?debug=true` pour findings complets (Claude's Discretion).
- **D-07:** `render.py` : `html.escape()` sur `png_path` injecté dans `<img src>` et sur toute valeur non fiable interpolée dans le HTML. Le corps markdown reste rendu (confiance synthesizer) mais les attributs sont échappés.

### Robustesse typage & exceptions (HARD-07, HARD-08)
- **D-08:** Helper `_as_text(response) -> str` dans nodes.py (ou llm.py) : retourne `response.content` si str, sinon concatène les parts texte / `str(content)`. Utilisé après **chaque** `.invoke().content` (planner, sql gen/regen, critic, synthesizer). Corrige les 5 erreurs mypy, évite crash sur réponse multi-part.
- **D-09:** Les `except Exception` aveugles (nodes.py stats DataFrame ~341, viz DataFrame ~422, render_chart ~445) bindent l'exception (`as exc`) et loggent `logger.warning(..., exc_info=True)`. Plus de swallow silencieux. Garder le comportement (skip/finding), juste tracer.

### Performance (HARD-09, HARD-10, HARD-11)
- **D-10:** Schema introspecté **une fois par run**. Ajouter `schema: str` à `AgentState` ; `initial_state(question, conn, schema="")` ; `run()` calcule `schema_description(conn)` une fois et l'injecte. `sql_tool_node` lit `state.get("schema")` ; fallback `schema_description(conn)` si vide (préserve les tests node-level isolés). Élimine ~150 queries/run.
- **D-11:** `flash_llm()`/`pro_llm()` retournent des **singletons** module-level (cache `_flash`/`_pro`, créés au 1er appel). Plus de ré-instanciation ~30×/run. Les tests qui monkeypatchent `flash_llm`/`pro_llm` restent valides (ils patchent la fonction).
- **D-12:** API FastAPI : `lifespan` crée **une** connexion DuckDB persistante (load Olist une fois au startup), fermée au shutdown. `ask()` réutilise cette conn (`run(question, conn=app_conn)`). Plus de rechargement des 9 CSV par requête.

### Tests (HARD-12)
- **D-13:** Combler les blind spots : tests `__main__.py` (CLI : question valide via run mocké, arg manquant → exit non-zéro), chemin échec exécution SQL (EXPLAIN passe / `conn.execute` raise → retry puis finding erreur), gardes `except` stats/viz (rows arity mismatch), fallback planner vide (LLM whitespace → `[question]`), garde write SQL (D-04), borne current_step (D-01/D-02), critic content (D-03). Viser ≥85% global. Vrais I/O, LLM mocké uniquement.

### Claude's Discretion
- Emplacement exact des helpers, format du résumé critic, query param debug `/ask`, signature `_as_text`, organisation des nouveaux tests.

</decisions>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### Findings de la revue (source des décisions)
- Revue multi-agents post-v1.0 (résumée dans cette CONTEXT) : 2 bugs CRITICAL boucle agent (current_step overflow + critic aveugle), sécurité SQL/API/render, type safety, perf, blind spots tests.

### Code à corriger (NE PAS réécrire — patchs ciblés)
- `src/dataagent/agent/nodes.py` — `critic_node` (~531-561), `route_subquestion`, `sql_tool_node`/`_execute_subquestion` (~131-199), `stats_tool_node` (~341), `viz_tool_node` (~422-447), planner_node fallback (~50), accès `.content` (43,115,128,549,600).
- `src/dataagent/agent/graph.py` — `_critic_decision` (~113), `run()` (injection schema), `build_graph`/`run` types.
- `src/dataagent/agent/state.py` — ajouter `schema: str` + `initial_state(schema="")`.
- `src/dataagent/agent/llm.py` — singletons.
- `src/dataagent/agent/schema_introspect.py` — réutilisé (appelé une fois).
- `src/dataagent/config.py` — `SQL_FORBIDDEN_KEYWORDS`.
- `src/dataagent/data/loader.py` — validation nom de table (~36).
- `src/dataagent/api.py` — lifespan + max_length + filtrage findings.
- `src/dataagent/render.py` — html.escape (~197).
- `src/dataagent/__main__.py` — cible des tests CLI.
- `PLAN.md` — décisions figées (hard cap, UntrackedValue, path_map) à préserver.

</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets
- Tous les nodes/graph existants (v1.0) — patchs ciblés, pas de réécriture.
- `schema_description(conn)` réutilisé (appelé une fois au lieu de N).
- Pattern test : DuckDB réel + LLM mocké (`_FakeLLM`/`_SequenceLLM`).

### Established Patterns
- `findings` reducer `add` ; `iterations`/`current_step`/`max_iterations` dans le state.
- `_FilteredSqliteSaver` (resumabilité) — ne pas casser ; si on ajoute `schema` au state, vérifier qu'il se sérialise (str → msgpack OK).
- Tests : aucun mock I/O DuckDB/FS, seul le LLM mocké. 163 tests existants à ne PAS régresser.

### Integration Points
- Ajout champ state `schema` → impacte initial_state + run + sql_tool (fallback préserve compat).
- Singletons llm → transparents pour le monkeypatch des tests.
- API lifespan → nouvelle conn app-scoped.
- Attention : changer `current_step`/critic peut impacter `test_critic_loop.py`/`test_hard_cap` — mettre à jour les tests si le comportement de terminaison change (la terminaison plus tôt via D-02 est le comportement voulu).

</code_context>

<specifics>
## Specific Ideas

- Priorité d'implémentation : HARD-01/02 (boucle) d'abord (bugs bloquants), puis sécurité, puis perf/qualité, puis tests.
- Le hard cap `max_iterations` existant RESTE en place (D-02 ajoute une terminaison plus précoce, ne le remplace pas).
- Garder le comportement nominal : un run normal doit produire le même type de rapport, juste sans gaspiller d'itérations ni exposer de surface d'attaque.

</specifics>

<deferred>
## Deferred Ideas

- Rotation clé API (manuel utilisateur), rate-limiting `/ask`, router LLM-based, request timeout LLM, ThreadPool eval, retention checkpointer — backlog post-v1.1.

</deferred>

---

*Phase: 07-hardening-bug-fixes*
*Context gathered: 2026-06-13*
