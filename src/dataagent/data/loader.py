"""Chargement des CSV Olist dans DuckDB.

Chaque fichier `*.csv` du dossier devient une table. Le nom de table est dérivé
du nom de fichier en retirant le préfixe `olist_` et le suffixe `_dataset`
(ex: `olist_order_items_dataset.csv` -> table `order_items`).
"""

from pathlib import Path

import duckdb


def connect(db_path: str = ":memory:") -> duckdb.DuckDBPyConnection:
    """Ouvre une connexion DuckDB (en mémoire par défaut)."""
    return duckdb.connect(db_path)


def table_name(csv_path: Path) -> str:
    """Dérive un nom de table ergonomique depuis le nom de fichier Olist."""
    name = csv_path.stem
    name = name.removeprefix("olist_").removesuffix("_dataset")
    return name


def load_csvs_to_duckdb(
    conn: duckdb.DuckDBPyConnection, csv_dir: str | Path
) -> list[str]:
    """Charge tous les CSV du dossier dans DuckDB. Retourne les tables créées."""
    csv_dir = Path(csv_dir)
    if not csv_dir.is_dir():
        raise FileNotFoundError(f"Dossier introuvable : {csv_dir}")

    loaded: list[str] = []
    for csv_path in sorted(csv_dir.glob("*.csv")):
        table = table_name(csv_path)
        conn.execute(
            f'CREATE OR REPLACE TABLE "{table}" AS '
            "SELECT * FROM read_csv_auto(?)",
            [str(csv_path)],
        )
        loaded.append(table)

    if not loaded:
        raise FileNotFoundError(f"Aucun CSV trouvé dans : {csv_dir}")
    return loaded
