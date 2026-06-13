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


# ---------------------------------------------------------------------------
# Tests validation nom de table — HARD-04 (D-05, plan 07-02 Task 1)
# ---------------------------------------------------------------------------


def test_invalid_table_name_skipped_with_warning(tmp_path, caplog):
    """Un CSV dont le nom de table dérivé commence par un chiffre est ignoré avec warning."""
    import logging

    import polars as pl

    # Fichier avec nom de table non conforme (commence par chiffre après strip préfixe/suffixe)
    # table_name("123bad.csv") → "123bad" (pas de préfixe olist_, pas de suffixe _dataset)
    pl.DataFrame({"id": [1, 2]}).write_csv(tmp_path / "123bad.csv")
    # Fichier valide pour que loaded ne soit pas vide
    pl.DataFrame({"order_id": ["o1"], "price": [10.0]}).write_csv(tmp_path / "olist_orders_dataset.csv")

    c = connect()
    with caplog.at_level(logging.WARNING, logger="dataagent.data.loader"):
        loaded = load_csvs_to_duckdb(c, tmp_path)
    c.close()

    # Le fichier non conforme est ignoré
    assert "123bad" not in loaded
    # La table valide est chargée
    assert "orders" in loaded
    # Un warning a été émis
    assert any("non conforme" in record.message or "ignoré" in record.message for record in caplog.records)


def test_invalid_table_name_does_not_crash_other_files(tmp_path):
    """Un CSV non conforme n'empêche pas le chargement des autres CSV valides."""
    import polars as pl

    pl.DataFrame({"id": [1]}).write_csv(tmp_path / "123bad.csv")
    pl.DataFrame({"order_id": ["o1"]}).write_csv(tmp_path / "olist_orders_dataset.csv")
    pl.DataFrame({"order_id": ["o1"], "product_id": ["p1"], "price": [10.0], "order_item_id": [1], "freight_value": [1.0]}).write_csv(
        tmp_path / "olist_order_items_dataset.csv"
    )

    c = connect()
    loaded = load_csvs_to_duckdb(c, tmp_path)
    c.close()

    assert "orders" in loaded
    assert "order_items" in loaded
    assert "123bad" not in loaded


def test_all_invalid_table_names_raises(tmp_path):
    """Si tous les CSV ont des noms non conformes, FileNotFoundError est levé (loaded vide)."""
    import polars as pl

    pl.DataFrame({"id": [1]}).write_csv(tmp_path / "123bad.csv")
    pl.DataFrame({"id": [2]}).write_csv(tmp_path / "456also_bad.csv")

    c = connect()
    with pytest.raises(FileNotFoundError):
        load_csvs_to_duckdb(c, tmp_path)
    c.close()


def test_conformant_table_name_loads_normally(tmp_path):
    """Un CSV avec nom de table conforme se charge normalement."""
    import polars as pl

    pl.DataFrame({"order_id": ["o1"], "price": [100.0]}).write_csv(tmp_path / "olist_orders_dataset.csv")

    c = connect()
    loaded = load_csvs_to_duckdb(c, tmp_path)
    c.close()

    assert "orders" in loaded
