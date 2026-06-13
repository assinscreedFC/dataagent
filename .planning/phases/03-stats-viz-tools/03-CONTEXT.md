# Phase 3: Stats & Viz Tools - Context

**Gathered:** 2026-06-13 (auto mode — recommended defaults from PLAN.md + Phase 1 code)
**Status:** Ready for planning

<domain>
## Phase Boundary

Ajoute deux nouveaux nodes-tools indépendants : `stats_tool_node` (analyse statistique Polars : corrélation + détection d'anomalie) et `viz_tool_node` (visualisation plotly → PNG sur disque, chemin dans findings). Couvre TOOL-02 et TOOL-03. Les deux sont des fonctions de node autonomes, testées en isolation — ils ne sont PAS encore câblés dans le graphe (le router qui les dispatche est Phase 4). Le graphe reste linéaire planner→sql_tool→synthesizer jusqu'à Phase 4. HORS scope : router, critic loop, checkpointer, modification du graphe.

</domain>

<decisions>
## Implementation Decisions

### stats_tool (TOOL-02)
- **D-01:** `stats_tool_node(state) -> dict` consomme les données présentes dans `findings` (résultats SQL des étapes précédentes, sous forme exploitable Polars). Module dédié `src/dataagent/agent/stats.py` avec fonctions pures testables (`correlation(df, col_a, col_b)`, `detect_anomalies(series)`), le node les orchestre.
- **D-02:** Corrélation : coefficient de Pearson entre deux séries numériques via Polars (`df.select(pl.corr(a, b))`). Poussée dans findings (clé corrélation + colonnes + valeur).
- **D-03:** Détection d'anomalie : méthode z-score (|z| > seuil, défaut 3.0, constante `ANOMALY_Z_THRESHOLD` dans config) — simple, déterministe, testable sur fixtures synthétiques. Alternative IQR écartée (z-score suffit, plus lisible pour un portfolio). Anomalies poussées dans findings.
- **D-04:** Sur données insuffisantes (moins de 2 points, colonnes non numériques) : finding explicite "stats non calculables" sans crash.

### viz_tool (TOOL-03)
- **D-05:** `viz_tool_node(state) -> dict` génère une figure plotly à partir de données de findings et l'exporte en PNG via kaleido vers `config.REPORTS` (`reports/`). Module dédié `src/dataagent/agent/viz.py`.
- **D-06:** Type de graphe choisi selon la nature des données (série temporelle → line, catégoriel → bar) — heuristique simple, Claude's Discretion sur le détail. Nom de fichier déterministe basé sur la sous-question/un index (évite collision), pas de timestamp aléatoire (reproductibilité tests).
- **D-07:** Le chemin absolu du PNG généré est enregistré dans findings (clé `png_path`). `reports/` créé si absent (`config.REPORTS.mkdir(parents=True, exist_ok=True)`).

### Claude's Discretion
- Choix précis du type de graphe par heuristique, layout/style plotly, clés exactes des findings stats/viz, signature interne des helpers.

</decisions>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### Code existant à étendre/réutiliser
- `src/dataagent/agent/nodes.py` — patterns des nodes existants (planner/sql_tool/synthesizer) : signature `(state) -> dict`, retour `{"findings": [...]}` via reducer `add`, incrément iterations. Les nouveaux nodes suivent ce contrat.
- `src/dataagent/agent/state.py` — `AgentState` (findings accumulés).
- `src/dataagent/config.py` — ajouter `ANOMALY_Z_THRESHOLD` ; `REPORTS` path déjà défini.
- `src/dataagent/data/queries.py` — usage Polars existant (référence de style).
- `tests/conftest.py` — fixture `conn` DuckDB + fixtures synthétiques pour tester stats/viz sur données connues.

### Architecture
- `PLAN.md` §Graphe : "stats_tool : Polars (corrélation, agrégats, détection anomalie)", "viz_tool : plotly -> PNG sauvé, chemin dans findings". Stack : polars, plotly + kaleido (déjà installés, vérifié).

</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets
- Pattern node `(state) -> {"findings": [...]}` de nodes.py.
- Polars déjà dépendance (queries.py l'utilise).
- plotly + kaleido installés et importables.
- `config.REPORTS` pour le dossier de sortie PNG (déjà gitignored : `reports/*.png`).

### Established Patterns
- Tests : données synthétiques déterministes (pas de mock), vraie I/O. Pour viz : générer le PNG et asserter que le fichier existe + chemin dans finding. Pour stats : corrélation/anomalie sur séries connues (résultat attendu exact).
- Pas d'appel LLM dans stats_tool/viz_tool (calcul pur + rendu) → tests sans mock LLM, sans quota.

### Integration Points
- Nouveaux modules `stats.py`, `viz.py` + nodes correspondants dans `nodes.py` (ou nodes séparés). Pas de modification du graphe (graph.py inchangé cette phase).
- Findings consommés en aval par le synthesizer (déjà capable de lister les sources).

</code_context>

<specifics>
## Specific Ideas

- Noms de fichiers PNG déterministes pour des tests reproductibles (pas de timestamp aléatoire — `Date`/random interdits côté code de toute façon).
- Anomalie z-score : portfolio-friendly, déterministe, facile à expliquer.

</specifics>

<deferred>
## Deferred Ideas

- Câblage router vers stats/viz + critic loop — Phase 4
- Checkpointer — Phase 5

</deferred>

---

*Phase: 03-stats-viz-tools*
*Context gathered: 2026-06-13*
