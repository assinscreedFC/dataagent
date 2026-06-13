"""Fonctions pures d'analyse statistique : corrélation Pearson + détection d'anomalies z-score.

Aucun appel LLM, aucune I/O, aucun aléatoire — calcul pur Polars, déterministe et testable.
"""

import math

import polars as pl

from dataagent.config import ANOMALY_Z_THRESHOLD


def correlation(df: pl.DataFrame, col_a: str, col_b: str) -> float | None:
    """Calcule le coefficient de corrélation de Pearson entre deux colonnes numériques.

    Args:
        df: DataFrame Polars contenant les colonnes.
        col_a: Nom de la première colonne numérique.
        col_b: Nom de la deuxième colonne numérique.

    Returns:
        Coefficient de Pearson (float entre -1.0 et 1.0), ou None si :
        - df contient moins de 2 lignes,
        - l'une des colonnes est absente ou non numérique,
        - le résultat Polars est NaN (série constante).
    """
    # Vérifier présence des colonnes
    if col_a not in df.columns or col_b not in df.columns:
        return None

    # Vérifier que les colonnes sont numériques
    if not df[col_a].dtype.is_numeric() or not df[col_b].dtype.is_numeric():
        return None

    # Vérifier nombre de lignes suffisant
    if df.height < 2:
        return None

    # Calcul Pearson via Polars
    result = df.select(pl.corr(col_a, col_b)).item()

    # Convertir NaN (série constante) en None
    if result is None or (isinstance(result, float) and math.isnan(result)):
        return None

    return float(result)


def detect_anomalies(
    series: list[float] | pl.Series,
    threshold: float = ANOMALY_Z_THRESHOLD,
) -> list[dict]:
    """Détecte les anomalies dans une série numérique via z-score.

    Args:
        series: Série de valeurs numériques (list[float] ou pl.Series).
        threshold: Seuil z-score au-delà duquel une valeur est anomalie (défaut ANOMALY_Z_THRESHOLD).

    Returns:
        Liste de dicts {"index": int, "value": float, "z_score": float} pour chaque anomalie.
        Liste vide si :
        - len < 2,
        - variance nulle (std == 0),
        - aucune valeur ne dépasse le seuil.
    """
    # Coercion en pl.Series
    if not isinstance(series, pl.Series):
        s = pl.Series(series, dtype=pl.Float64)
    else:
        s = series.cast(pl.Float64)

    # Garde-fou longueur
    if len(s) < 2:
        return []

    mean = s.mean()
    std = s.std(ddof=0)

    # Garde-fou variance nulle (évite division par zéro)
    if std is None or std == 0.0:
        return []

    anomalies: list[dict] = []
    for i, v in enumerate(s.to_list()):
        if v is None:
            continue
        z = (v - mean) / std
        if abs(z) > threshold:
            anomalies.append({"index": i, "value": float(v), "z_score": float(z)})

    return anomalies
