# DataAgent

Agent analyste data autonome : question business en langage naturel -> rapport sourcé avec graphes.

Stack : LangGraph v1.0 (StateGraph manuel) + DuckDB + Polars + Claude.

Voir [`PLAN.md`](./PLAN.md) pour l'architecture et les jalons.

## Setup

```bash
python -m venv .venv
.venv\Scripts\activate          # Windows
pip install -e ".[dev]"          # J1 : data layer + tests
pip install -e ".[dev,agent]"    # J2+ : ajoute LangGraph / LLM
```

## Données

Télécharger le dataset Olist (Kaggle `olistbr/brazilian-ecommerce`), déposer les CSV dans `data/raw/`.

## Tests

```bash
pytest                 # tout
pytest --cov=dataagent # couverture
```

## État

- [x] J1 — data layer (DuckDB + 5 queries business, testé)
- [ ] J2 — agent single-tool
- [ ] J3 — multi-tool + critic loop
- [ ] J4 — eval + API + demo Labs
