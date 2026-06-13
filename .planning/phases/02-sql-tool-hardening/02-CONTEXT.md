# Phase 2: SQL Tool Hardening - Context

**Gathered:** 2026-06-13 (auto mode — recommended defaults from PLAN.md + Phase 1 code)
**Status:** Ready for planning

<domain>
## Phase Boundary

Durcit le `sql_tool_node` existant (livré minimal en Phase 1) pour qu'il ne casse plus sur du SQL halluciné : validation de la query contre le schema réel DuckDB AVANT exécution, et retry sur erreur avec une query corrigée par le LLM. Couvre TOOL-01. HORS scope : router, critic loop, stats/viz tools, checkpointer.

</domain>

<decisions>
## Implementation Decisions

### Validation pré-exécution (success criterion #1)
- **D-01:** Valider la query générée AVANT de l'exécuter sur les données via `EXPLAIN <sql>` sur la connexion DuckDB. `EXPLAIN` parse + résout tables/colonnes contre le catalogue sans scanner les données — une référence à une table/colonne inexistante lève une exception DuckDB (`CatalogException`/`BinderException`) capturée comme échec de validation.
- **D-02:** Rationale vs alternative : `EXPLAIN` est plus robuste qu'un check manuel des noms contre `information_schema` (gère alias, sous-requêtes, jointures, fonctions) — réutilise le moteur DuckDB plutôt que réimplémenter un validateur SQL.

### Retry sur erreur (success criteria #2, #4)
- **D-03:** Boucle de retry locale au sql_tool, bornée par une constante `SQL_MAX_RETRIES` (défaut 2) dans `config.py`. Distincte de `max_iterations` (garde-fou de la critic loop, Phase 4) — c'est un retry intra-tool.
- **D-04:** Sur échec (validation `EXPLAIN` OU erreur d'exécution), re-prompter `flash_llm` avec : la query fautive + le message d'erreur DuckDB exact + le schema → régénérer une query corrigée → re-valider → ré-exécuter. Répéter jusqu'à succès ou épuisement des retries.
- **D-05:** Si tous les retries échouent : pousser un finding d'erreur explicite (query finale + dernière erreur + nb tentatives) dans `findings`, sans lever d'exception (le graphe continue vers synthesizer). Pas de crash.

### Findings (success criterion #3)
- **D-06:** Une query valide pousse son résultat dans `findings` avec sa source (SQL exécutée + tables touchées + nb tentatives) — étend le format finding de Phase 1, ne le casse pas.

### Claude's Discretion
- Structure exacte du prompt de correction, parsing du message d'erreur DuckDB, classification fine des exceptions (validation vs exécution), clés précises du finding d'erreur.

</decisions>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### Code Phase 1 à durcir (NE PAS réécrire from scratch)
- `src/dataagent/agent/nodes.py` — `sql_tool_node` minimal existant : génère SQL via flash_llm, exécute, push finding. C'est CE node qu'on durcit (ajout validation + retry).
- `src/dataagent/agent/schema_introspect.py` — `schema_description(conn)` : description du schema injectée dans les prompts SQL ; réutilisée pour le prompt de correction.
- `src/dataagent/agent/llm.py` — `flash_llm()` factory réutilisée pour la régénération.
- `src/dataagent/config.py` — y ajouter `SQL_MAX_RETRIES`.
- `tests/test_nodes.py` — tests existants du sql_tool à étendre (LLM mocké, DuckDB réel).

### Architecture
- `PLAN.md` §Risques cadrés : "SQL halluciné → tool valide la query sur le schema DuckDB avant exec, retry sur erreur" — exigence directe de cette phase.

</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets
- `sql_tool_node` (nodes.py) : point d'extension principal.
- `schema_description()` : déjà utilisé pour générer le SQL, réutilisé pour le prompt de correction.
- `flash_llm()` : régénération de query.
- Fixture `conn` (tests/conftest.py) : DuckDB réel pour tester validation/retry.

### Established Patterns
- Tests : DuckDB réel + LLM mocké. Pour tester le retry : mocker flash_llm pour renvoyer une 1ère query fautive (table inexistante) puis une query correcte → vérifier que le finding final est correct.
- Findings retournés via `{"findings": [...]}` (reducer `add`).

### Integration Points
- Modifie uniquement `sql_tool_node` dans nodes.py + constante config + tests. Pas de changement au graphe ni aux autres nodes.

</code_context>

<specifics>
## Specific Ideas

- Le retry doit être borné (pas de boucle infinie) — cohérent avec la philosophie garde-fou coût du projet.
- Le finding d'erreur final doit rester exploitable par le synthesizer (rapport honnête "n'a pas pu calculer X").

</specifics>

<deferred>
## Deferred Ideas

- Router conditional + critic loop (itération multi-tools) — Phase 4
- stats_tool, viz_tool — Phase 3
- Checkpointer — Phase 5

</deferred>

---

*Phase: 02-sql-tool-hardening*
*Context gathered: 2026-06-13*
