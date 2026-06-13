# Phase 4: Router & Critic Loop - Context

**Gathered:** 2026-06-13 (auto mode — recommended defaults from PLAN.md + phases 1-3 code)
**Status:** Ready for planning

<domain>
## Phase Boundary

Transforme le graphe linéaire (planner→sql_tool→synthesizer) en boucle agentique branchée conforme au schéma PLAN.md : un router conditionnel dispatche chaque sous-question vers le bon tool (sql/stats/viz), un node critic juge si les findings suffisent et reboucle ou synthétise, le tout borné par `max_iterations` (hard cap, pas de boucle infinie). Couvre TOOL-04 (router), TOOL-05 (critic), TOOL-06 (hard cap), TOOL-08 (rapport multi-source avec graphe). HORS scope : checkpointer (Phase 5), eval/API/demo (Phase 6).

Graphe cible (PLAN.md) :
```
START -> planner -> router -+-> sql_tool ---+
                            +-> stats_tool -+-> critic -> (cond) -+-> router (reboucle si manque + iters<max)
                            +-> viz_tool ---+                     +-> synthesizer -> END
```

</domain>

<decisions>
## Implementation Decisions

### Router (TOOL-04)
- **D-01:** Le router est une fonction de routage conditionnelle (`add_conditional_edges`) avec return **type-hinté** (`Literal["sql_tool","stats_tool","viz_tool"]`) et **`path_map` obligatoire** — exigence PLAN.md (sinon misroute silencieux). Il choisit le tool selon la sous-question courante du plan.
- **D-02:** Sélection du tool : un node `router_node` (ou la fonction de routing) examine la sous-question courante (index dans `plan[]`) et décide. Heuristique LLM-light : un appel flash_llm classant la sous-question en {sql, stats, viz}, OU heuristique par mots-clés (corrélation/anomalie→stats, graphe/visualise→viz, sinon sql). Défaut recommandé : classification flash_llm (cohérent avec l'esprit agentique), fallback mots-clés si réponse hors enum. La sous-question courante est suivie par un index `current_step` dans le state.
- **D-03:** Après exécution d'un tool, retour vers `critic` (pas directement re-router) — conforme au schéma.

### Critic loop (TOOL-05, TOOL-06)
- **D-04:** `critic_node` (flash_llm, D-07) juge si les `findings` accumulés suffisent à répondre à la `question` initiale. Incrémente `iterations`. Retourne une décision.
- **D-05:** Conditional edge après critic : si findings insuffisants ET `iterations < max_iterations` → reboucle vers `router` (traite la sous-question suivante / approfondit). Sinon → `synthesizer`. Type-hinté + path_map.
- **D-06:** Hard cap : la boucle s'arrête à `max_iterations` (défaut 5, constante existante) MÊME si le critic n'est pas satisfait — garantit l'absence de boucle infinie (TOOL-06). Le critic incrémente toujours `iterations` à chaque passage.

### State
- **D-07:** Ajouter au besoin un champ `current_step: int` (index de la sous-question courante dans `plan[]`) au state pour que le router sache quelle sous-question traiter. Initialisé à 0, incrémenté à chaque tour de boucle. `iterations`/`max_iterations` déjà présents (Phase 1).

### Rapport multi-source (TOOL-08)
- **D-08:** Le synthesizer (déjà existant) produit le rapport markdown à partir de TOUS les findings accumulés (sql + stats + viz) — multi-source. Si un finding viz a un `png_path`, le rapport l'inclut/le référence (lien markdown image). Étend le prompt synthesizer existant, ne le réécrit pas.

### Claude's Discretion
- Heuristique exacte de routing, prompt du critic (critères de suffisance), gestion de l'avancement `current_step` vs reboucle, format d'inclusion du PNG dans le markdown.

</decisions>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### Architecture (CRITIQUE — décisions LangGraph figées)
- `PLAN.md` §Graphe (schéma exact), §Findings LangGraph v1.0 : router avec type hints + `path_map` obligatoire (sinon misroute silencieux) ; `ReducedValue`/`Annotated[list, add]` pour accumuler findings ; critic incrémente iterations ; hard cap max_iterations.

### Code à câbler (réutiliser, ne pas réécrire)
- `src/dataagent/agent/graph.py` — `build_graph()` linéaire actuel → à restructurer en graphe branché. `run()` conservé.
- `src/dataagent/agent/nodes.py` — `planner_node`, `sql_tool_node`, `stats_tool_node`, `viz_tool_node`, `synthesizer_node` existants. Ajouter `router_node`/routing fn + `critic_node`. NE PAS casser les nodes existants ni leurs tests.
- `src/dataagent/agent/state.py` — `AgentState` ; ajouter `current_step` si besoin (avec valeur initiale dans `initial_state()`).
- `src/dataagent/agent/llm.py` — `flash_llm` pour router/critic.
- `src/dataagent/config.py` — `MAX_ITERATIONS` (déjà là).

</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets
- 5 nodes existants + 2 tools (stats/viz) prêts mais non câblés — cette phase les branche.
- `findings` reducer `add` déjà en place (accumule sur la boucle).
- `iterations`/`max_iterations` déjà dans le state (Phase 1, garde-fou prêt).
- `run()` dans graph.py (point d'entrée conservé).

### Established Patterns
- Tests : DuckDB réel + LLM mocké. Pour la critic loop : mocker flash_llm (router renvoie un tool, critic renvoie "insuffisant" N fois puis "suffisant", OU jamais suffisant pour tester le hard cap). Asserter : routing correct, iterations s'arrête à max_iterations, pas de boucle infinie, rapport multi-source.
- Router type-hinté + path_map = exigence dure (test que le routing ne misroute pas silencieusement).

### Integration Points
- `graph.py` (restructuration majeure : nodes router+critic, conditional_edges, path_map).
- `state.py` (champ current_step éventuel).
- nodes.py (router_node, critic_node).
- Le run live (`python -m dataagent "question complexe"`) consomme du quota Gemini — validation live optionnelle/échantillonnée (free tier limité), le gros de la vérif passe par tests mockés.

</code_context>

<specifics>
## Specific Ideas

- Hard cap = exigence anti-boucle-infinie explicite du PLAN (garde-fou coût). Tester le cas "critic jamais satisfait → arrêt à max_iterations".
- Router sans path_map = misroute silencieux : risque cadré au PLAN, à éviter absolument (type hints + path_map).

</specifics>

<deferred>
## Deferred Ideas

- Checkpointer SqliteSaver (resumabilité) — Phase 5
- Eval 10 Q/R, FastAPI /ask, demo HTML — Phase 6

</deferred>

---

*Phase: 04-router-critic-loop*
*Context gathered: 2026-06-13*
