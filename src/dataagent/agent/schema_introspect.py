"""Introspection du schéma DuckDB pour injection dans les prompts SQL.

Fournit une description textuelle des tables et colonnes disponibles,
permettant au LLM de générer du SQL avec les vrais noms (anti-hallucination, D-12).
"""

import duckdb


def schema_description(conn: duckdb.DuckDBPyConnection) -> str:
    """Retourne une description textuelle du schéma DuckDB (tables + colonnes).

    Format de sortie (une ligne par table) :
        TABLE orders(order_id VARCHAR, customer_id VARCHAR, ...)
        TABLE order_items(order_id VARCHAR, order_item_id INTEGER, ...)

    Requêtes paramétrées uniquement — jamais de f-string sur input utilisateur.

    Args:
        conn: Connexion DuckDB active avec les tables chargées.

    Returns:
        Texte décrivant tables + colonnes, prêt pour injection dans un prompt.
    """
    tables_query = (
        "SELECT table_name "
        "FROM information_schema.tables "
        "WHERE table_schema = 'main' "
        "ORDER BY table_name"
    )
    tables = [row[0] for row in conn.execute(tables_query).fetchall()]

    lines: list[str] = []
    for table in tables:
        columns_query = (
            "SELECT column_name, data_type "
            "FROM information_schema.columns "
            "WHERE table_name = ? "
            "ORDER BY ordinal_position"
        )
        cols = conn.execute(columns_query, [table]).fetchall()
        col_defs = ", ".join(f"{col_name} {data_type}" for col_name, data_type in cols)
        lines.append(f"TABLE {table}({col_defs})")

    return "\n".join(lines)
