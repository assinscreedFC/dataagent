"""Queries business sur le dataset Olist (sortie Polars).

Ces 5 queries servent de socle de référence (J1) et de tools déterministes
pour l'agent (J3). Toutes retournent un `polars.DataFrame`.
"""

import duckdb
import polars as pl

from dataagent.config import DEFAULT_TOP_N


def revenue_by_month(conn: duckdb.DuckDBPyConnection) -> pl.DataFrame:
    """CA mensuel des commandes livrées (somme des prix d'items)."""
    sql = """
        SELECT strftime(CAST(o.order_purchase_timestamp AS TIMESTAMP), '%Y-%m') AS month,
               ROUND(SUM(i.price), 2) AS revenue
        FROM orders o
        JOIN order_items i ON o.order_id = i.order_id
        WHERE o.order_status = 'delivered'
        GROUP BY month
        ORDER BY month
    """
    return conn.execute(sql).pl()


def top_categories(
    conn: duckdb.DuckDBPyConnection, n: int = DEFAULT_TOP_N
) -> pl.DataFrame:
    """Top N catégories produit par CA."""
    sql = """
        SELECT p.product_category_name AS category,
               ROUND(SUM(i.price), 2) AS revenue
        FROM order_items i
        JOIN products p ON i.product_id = p.product_id
        GROUP BY category
        ORDER BY revenue DESC
        LIMIT ?
    """
    return conn.execute(sql, [n]).pl()


def delivery_delay_vs_review(conn: duckdb.DuckDBPyConnection) -> pl.DataFrame:
    """Délai de livraison moyen (jours) par score de review."""
    sql = """
        SELECT r.review_score AS review_score,
               ROUND(AVG(date_diff('day',
                   CAST(o.order_purchase_timestamp AS TIMESTAMP),
                   CAST(o.order_delivered_customer_date AS TIMESTAMP))), 1)
                   AS avg_delivery_days
        FROM orders o
        JOIN order_reviews r ON o.order_id = r.order_id
        WHERE o.order_delivered_customer_date IS NOT NULL
        GROUP BY review_score
        ORDER BY review_score
    """
    return conn.execute(sql).pl()


def orders_by_status(conn: duckdb.DuckDBPyConnection) -> pl.DataFrame:
    """Répartition des commandes par statut."""
    sql = """
        SELECT order_status AS status, COUNT(*) AS n
        FROM orders
        GROUP BY status
        ORDER BY n DESC
    """
    return conn.execute(sql).pl()


def avg_review_score_by_month(conn: duckdb.DuckDBPyConnection) -> pl.DataFrame:
    """Score de review moyen par mois."""
    sql = """
        SELECT strftime(CAST(r.review_creation_date AS TIMESTAMP), '%Y-%m') AS month,
               ROUND(AVG(r.review_score), 2) AS avg_score
        FROM order_reviews r
        GROUP BY month
        ORDER BY month
    """
    return conn.execute(sql).pl()
