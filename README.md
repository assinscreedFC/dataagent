# DataAgent

**Agent analyste data autonome : une question business en langage naturel → un rapport sourcé avec graphes.**

Tu poses une question (« Quel est le CA par mois ? », « Les retards de livraison plombent-ils les avis ? »), l'agent planifie, query la data, croise les sources, et sort un rapport sourcé avec visualisations. Projet portfolio (Labs SolidScale) — apprentissage **agentic AI + data engineering moderne**.

Stack : **LangGraph v1.0** (`StateGraph` manuel) + **DuckDB** + **Polars** + **Claude** (Haiku planner/critic, Opus synthétiseur).

> ⚠️ **Statut : en construction.** La couche data (J1) est livrée et testée. L'agent LangGraph (J2+) est en cours — voir [État](#état). Voir [`PLAN.md`](./PLAN.md) pour l'architecture complète et les jalons.

---

## Setup

```bash
python -m venv .venv
.venv\Scripts\activate          # Windows  (source .venv/bin/activate sur Unix)
pip install -e ".[dev]"          # J1 : data layer + tests
pip install -e ".[dev,agent]"    # J2+ : ajoute LangGraph / LLM / plotly / fastapi
```

## Données

Dataset **Olist e-commerce** (Kaggle `olistbr/brazilian-ecommerce`, 9 tables, ~100k commandes). Télécharge-le et dépose les CSV dans `data/raw/`.

Le loader dérive un nom de table ergonomique de chaque fichier (`olist_order_items_dataset.csv` → table `order_items`).

---

## Couche data (J1 — livrée)

Chargement DuckDB + 5 queries business prêtes, retournant des DataFrames Polars.

```python
from dataagent.data.loader import connect, load_csvs_to_duckdb
from dataagent.data.queries import (
    revenue_by_month,
    top_categories,
    delivery_delay_vs_review,
    orders_by_status,
    avg_review_score_by_month,
)

conn = connect()                                 # DuckDB en mémoire
tables = load_csvs_to_duckdb(conn, "data/raw")   # -> ['customers', 'orders', 'order_items', ...]

print(revenue_by_month(conn))             # CA par mois (Polars DataFrame)
print(top_categories(conn, n=10))         # Top 10 catégories par CA
print(delivery_delay_vs_review(conn))     # Délai livraison moyen par score d'avis
```

| Query | Retour |
|-------|--------|
| `revenue_by_month(conn)` | CA agrégé par mois |
| `top_categories(conn, n=10)` | Top N catégories produit par CA |
| `delivery_delay_vs_review(conn)` | Délai de livraison moyen (jours) par score de review |
| `orders_by_status(conn)` | Répartition des commandes par statut |
| `avg_review_score_by_month(conn)` | Score d'avis moyen par mois |

---

## Architecture cible (agent)

- **LangGraph `StateGraph` manuel** (pas `create_react_agent`) : la critic loop impose parallel nodes + router + retry custom.
- **Connexion DuckDB** dans le state via `UntrackedValue` (transient, jamais checkpointé).
- **Findings** accumulés via reducer `Annotated[list, add]`.
- **Garde-fou coût** : `MAX_ITERATIONS` (hard stop de la boucle critic), Haiku pour planner/router/critic, Opus pour la synthèse finale.
- **Resumabilité** : checkpointer SQLite.

Flux : question → planner → query (data layer) → critic loop → synthétiseur → rapport sourcé + graphes.

---

## Structure

```
src/dataagent/
├── config.py          # PROJECT_ROOT, DATA_RAW, REPORTS, DEFAULT_TOP_N, MAX_ITERATIONS
└── data/
    ├── loader.py      # connect(), load_csvs_to_duckdb(), table_name()
    └── queries.py     # 5 queries business → Polars DataFrame
tests/                 # test_loader.py, test_queries.py (DuckDB réel, pas de mock)
PLAN.md                # architecture + jalons + findings LangGraph v1.0
```

## Tests

```bash
pytest                 # tout
pytest --cov=dataagent # couverture
```

DuckDB réel en mémoire, pas de mock I/O.

## État

- [x] **J1 — data layer** (DuckDB + 5 queries business, testé, couverture 100 %)
- [ ] J2 — agent single-tool
- [ ] J3 — multi-tool + critic loop
- [ ] J4 — eval + API (FastAPI) + démo Labs

## Licence

Projet portfolio privé (Labs SolidScale).
