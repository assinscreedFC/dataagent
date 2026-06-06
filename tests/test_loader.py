"""Tests du loader DuckDB."""

from pathlib import Path

import pytest

from dataagent.data.loader import connect, load_csvs_to_duckdb, table_name


def test_table_name_strips_olist_prefix_and_dataset_suffix():
    assert table_name(Path("olist_order_items_dataset.csv")) == "order_items"
    assert table_name(Path("olist_orders_dataset.csv")) == "orders"
    assert table_name(Path("product_category_name_translation.csv")) == (
        "product_category_name_translation"
    )


def test_load_creates_expected_tables(olist_csv_dir):
    c = connect()
    loaded = load_csvs_to_duckdb(c, olist_csv_dir)
    assert set(loaded) == {"orders", "order_items", "products", "order_reviews"}
    c.close()


def test_loaded_table_has_rows(conn):
    n = conn.execute("SELECT COUNT(*) FROM orders").fetchone()[0]
    assert n == 4


def test_empty_dir_raises(tmp_path):
    c = connect()
    with pytest.raises(FileNotFoundError):
        load_csvs_to_duckdb(c, tmp_path)
    c.close()


def test_missing_dir_raises():
    c = connect()
    with pytest.raises(FileNotFoundError):
        load_csvs_to_duckdb(c, "n_existe_pas_xyz")
    c.close()
