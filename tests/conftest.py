"""Fixtures de test : mini-dataset Olist synthétique chargé dans un vrai DuckDB.

On n'utilise pas de mock : la vraie I/O DuckDB est testée sur des CSV minimaux
écrits dans un dossier temporaire.
"""

import polars as pl
import pytest

from dataagent.data.loader import connect, load_csvs_to_duckdb


@pytest.fixture
def olist_csv_dir(tmp_path):
    """Écrit un mini Olist (4 commandes) au format CSV et retourne le dossier."""
    pl.DataFrame(
        {
            "order_id": ["o1", "o2", "o3", "o4"],
            "customer_id": ["c1", "c2", "c3", "c4"],
            "order_status": ["delivered", "delivered", "delivered", "canceled"],
            "order_purchase_timestamp": [
                "2017-01-05 10:00:00",
                "2017-01-20 12:00:00",
                "2017-02-10 09:00:00",
                "2017-02-15 11:00:00",
            ],
            "order_delivered_customer_date": [
                "2017-01-10 10:00:00",
                "2017-01-23 12:00:00",
                "2017-02-20 09:00:00",
                None,
            ],
        }
    ).write_csv(tmp_path / "olist_orders_dataset.csv")

    pl.DataFrame(
        {
            "order_id": ["o1", "o2", "o3", "o4"],
            "order_item_id": [1, 1, 1, 1],
            "product_id": ["p1", "p2", "p1", "p2"],
            "price": [100.0, 200.0, 50.0, 30.0],
            "freight_value": [10.0, 15.0, 5.0, 3.0],
        }
    ).write_csv(tmp_path / "olist_order_items_dataset.csv")

    pl.DataFrame(
        {
            "product_id": ["p1", "p2"],
            "product_category_name": ["informatica", "moveis"],
        }
    ).write_csv(tmp_path / "olist_products_dataset.csv")

    pl.DataFrame(
        {
            "review_id": ["r1", "r2", "r3"],
            "order_id": ["o1", "o2", "o3"],
            "review_score": [5, 4, 2],
            "review_creation_date": [
                "2017-01-11 00:00:00",
                "2017-01-24 00:00:00",
                "2017-02-21 00:00:00",
            ],
        }
    ).write_csv(tmp_path / "olist_order_reviews_dataset.csv")

    return tmp_path


@pytest.fixture
def conn(olist_csv_dir):
    """Connexion DuckDB en mémoire avec le mini Olist chargé."""
    c = connect()
    load_csvs_to_duckdb(c, olist_csv_dir)
    yield c
    c.close()
