"""Tests pour les fonctions pures stats.py et stats_tool_node.

Données synthétiques déterministes — pas de mock LLM, pas de DuckDB requis.
Structure AAA (Arrange-Act-Assert).
"""

import polars as pl
import pytest

from dataagent.agent.stats import correlation, detect_anomalies


# ---------------------------------------------------------------------------
# Tests : correlation()
# ---------------------------------------------------------------------------


def test_correlation_perfect_positive():
    """Deux séries parfaitement corrélées → 1.0."""
    # Arrange
    df = pl.DataFrame({"x": [1.0, 2.0, 3.0, 4.0], "y": [2.0, 4.0, 6.0, 8.0]})

    # Act
    result = correlation(df, "x", "y")

    # Assert
    assert result is not None
    assert result == pytest.approx(1.0, abs=1e-9)


def test_correlation_perfect_negative():
    """Deux séries parfaitement anti-corrélées → -1.0."""
    # Arrange
    df = pl.DataFrame({"x": [1.0, 2.0, 3.0, 4.0], "y": [8.0, 6.0, 4.0, 2.0]})

    # Act
    result = correlation(df, "x", "y")

    # Assert
    assert result is not None
    assert result == pytest.approx(-1.0, abs=1e-9)


def test_correlation_insufficient_rows():
    """Moins de 2 lignes → None."""
    # Arrange
    df = pl.DataFrame({"x": [1.0], "y": [2.0]})

    # Act
    result = correlation(df, "x", "y")

    # Assert
    assert result is None


def test_correlation_empty_dataframe():
    """DataFrame vide → None."""
    # Arrange
    df = pl.DataFrame({"x": [], "y": []})

    # Act
    result = correlation(df, "x", "y")

    # Assert
    assert result is None


def test_correlation_non_numeric_column():
    """Colonne non numérique → None."""
    # Arrange
    df = pl.DataFrame({"x": ["a", "b", "c"], "y": [1.0, 2.0, 3.0]})

    # Act
    result = correlation(df, "x", "y")

    # Assert
    assert result is None


def test_correlation_both_non_numeric():
    """Les deux colonnes non numériques → None."""
    # Arrange
    df = pl.DataFrame({"x": ["a", "b", "c"], "y": ["d", "e", "f"]})

    # Act
    result = correlation(df, "x", "y")

    # Assert
    assert result is None


def test_correlation_constant_series():
    """Série constante (variance nulle) → None (pas de NaN propagé)."""
    # Arrange
    df = pl.DataFrame({"x": [1.0, 1.0, 1.0, 1.0], "y": [1.0, 2.0, 3.0, 4.0]})

    # Act
    result = correlation(df, "x", "y")

    # Assert — NaN retourné par Polars doit être converti en None
    assert result is None


# ---------------------------------------------------------------------------
# Tests : detect_anomalies()
# ---------------------------------------------------------------------------


def test_detect_anomalies_flags_outlier():
    """Série [10]*20 + [100] → dernier index (valeur 100) détecté comme anomalie (z~4.47 > 3.0)."""
    # Arrange — 20 valeurs normales + 1 outlier clair (z~4.47 avec ddof=0)
    series = [10.0] * 20 + [100.0]

    # Act
    anomalies = detect_anomalies(series)

    # Assert
    assert len(anomalies) >= 1
    # L'outlier est au dernier index (20)
    indices = [a["index"] for a in anomalies]
    assert 20 in indices
    # Vérifier la structure du dict
    outlier = next(a for a in anomalies if a["index"] == 20)
    assert outlier["value"] == pytest.approx(100.0)
    assert abs(outlier["z_score"]) > 3.0


def test_detect_anomalies_no_outlier():
    """Série sans outlier → liste vide."""
    # Arrange
    series = [10.0, 11.0, 10.5, 9.8, 10.2, 10.7]

    # Act
    anomalies = detect_anomalies(series)

    # Assert
    assert anomalies == []


def test_detect_anomalies_length_less_than_2():
    """Série de longueur < 2 → liste vide (pas de crash)."""
    # Arrange
    series = [42.0]

    # Act
    anomalies = detect_anomalies(series)

    # Assert
    assert anomalies == []


def test_detect_anomalies_empty_series():
    """Série vide → liste vide."""
    # Arrange
    series: list[float] = []

    # Act
    anomalies = detect_anomalies(series)

    # Assert
    assert anomalies == []


def test_detect_anomalies_zero_variance():
    """Série constante (std == 0) → liste vide (pas de division par zéro)."""
    # Arrange
    series = [5.0, 5.0, 5.0, 5.0, 5.0]

    # Act
    anomalies = detect_anomalies(series)

    # Assert
    assert anomalies == []


def test_detect_anomalies_polars_series_input():
    """Accepte un pl.Series en entrée (coercion interne). Série avec z>3.0."""
    # Arrange — [10]*20 + [100] donne z~4.47 pour l'outlier
    series = pl.Series([10.0] * 20 + [100.0])

    # Act
    anomalies = detect_anomalies(series)

    # Assert
    assert len(anomalies) >= 1
    indices = [a["index"] for a in anomalies]
    assert 20 in indices


def test_detect_anomalies_dict_structure():
    """Chaque anomalie a les clés 'index', 'value', 'z_score'."""
    # Arrange — [10]*20 + [100] : outlier z~4.47 > 3.0
    series = [10.0] * 20 + [100.0]

    # Act
    anomalies = detect_anomalies(series)

    # Assert
    assert len(anomalies) >= 1
    for a in anomalies:
        assert "index" in a
        assert "value" in a
        assert "z_score" in a
        assert isinstance(a["index"], int)
        assert isinstance(a["value"], float)
        assert isinstance(a["z_score"], float)


# ---------------------------------------------------------------------------
# Tests : stats_tool_node
# ---------------------------------------------------------------------------


def test_stats_tool_node_correlation_and_anomaly():
    """Node avec findings contenant données numériques → findings correlation + anomaly."""
    from dataagent.agent.nodes import stats_tool_node

    # Arrange — findings avec rows et columns numériques
    state = {
        "findings": [
            {
                "source": "sql_tool",
                "subquestion": "test",
                "sql": "SELECT x, y FROM t",
                "tables": ["t"],
                "rows": [(1.0, 2.0), (2.0, 4.0), (3.0, 6.0), (4.0, 8.0)],
                "columns": ["x", "y"],
                "attempts": 1,
            }
        ]
    }

    # Act
    result = stats_tool_node(state)

    # Assert
    assert "findings" in result
    sources = [f["source"] for f in result["findings"]]
    assert all(s == "stats_tool" for s in sources)
    analyses = [f["analysis"] for f in result["findings"]]
    assert "correlation" in analyses


def test_stats_tool_node_insufficient_data():
    """Node avec findings sans données numériques → finding insufficient_data, pas de crash."""
    from dataagent.agent.nodes import stats_tool_node

    # Arrange — findings avec < 2 rows
    state = {
        "findings": [
            {
                "source": "sql_tool",
                "subquestion": "test",
                "sql": "SELECT x FROM t",
                "tables": ["t"],
                "rows": [(1.0,)],
                "columns": ["x"],
                "attempts": 1,
            }
        ]
    }

    # Act
    result = stats_tool_node(state)

    # Assert
    assert "findings" in result
    analyses = [f["analysis"] for f in result["findings"]]
    assert "insufficient_data" in analyses


def test_stats_tool_node_empty_findings():
    """Node avec findings vide → insufficient_data."""
    from dataagent.agent.nodes import stats_tool_node

    # Arrange
    state = {"findings": []}

    # Act
    result = stats_tool_node(state)

    # Assert
    assert "findings" in result
    analyses = [f["analysis"] for f in result["findings"]]
    assert "insufficient_data" in analyses


def test_stats_tool_node_error_finding_skipped():
    """Finding avec 'error' (pas de rows/columns) → ignoré proprement, insufficient_data."""
    from dataagent.agent.nodes import stats_tool_node

    # Arrange
    state = {
        "findings": [
            {
                "source": "sql_tool",
                "subquestion": "test",
                "sql": "SELECT x FROM t",
                "error": "Table not found",
                "attempts": 3,
            }
        ]
    }

    # Act
    result = stats_tool_node(state)

    # Assert — pas de crash, insufficient_data poussé
    assert "findings" in result
    analyses = [f["analysis"] for f in result["findings"]]
    assert "insufficient_data" in analyses


def test_stats_tool_node_non_numeric_columns():
    """Findings avec colonnes non numériques → insufficient_data."""
    from dataagent.agent.nodes import stats_tool_node

    # Arrange
    state = {
        "findings": [
            {
                "source": "sql_tool",
                "subquestion": "test",
                "sql": "SELECT cat FROM t",
                "tables": ["t"],
                "rows": [("a",), ("b",), ("c",)],
                "columns": ["cat"],
                "attempts": 1,
            }
        ]
    }

    # Act
    result = stats_tool_node(state)

    # Assert
    assert "findings" in result
    analyses = [f["analysis"] for f in result["findings"]]
    assert "insufficient_data" in analyses


def test_stats_tool_node_returns_source_stats_tool():
    """Tous les findings retournés ont source == 'stats_tool'."""
    from dataagent.agent.nodes import stats_tool_node

    # Arrange
    state = {
        "findings": [
            {
                "source": "sql_tool",
                "subquestion": "test",
                "sql": "SELECT x, y FROM t",
                "tables": ["t"],
                "rows": [(1.0, 10.0), (2.0, 20.0), (3.0, 30.0)],
                "columns": ["x", "y"],
                "attempts": 1,
            }
        ]
    }

    # Act
    result = stats_tool_node(state)

    # Assert
    for f in result["findings"]:
        assert f["source"] == "stats_tool"


def test_stats_tool_node_anomaly_detected():
    """Node détecte anomalie sur colonne avec outlier connu (z>3.0, série 21 points)."""
    from dataagent.agent.nodes import stats_tool_node

    # Arrange — 20 lignes normales + 1 outlier évident (z~4.47 > 3.0)
    normal_rows = [(float(i), 10.0) for i in range(1, 21)]
    outlier_row = (21.0, 100.0)
    rows = normal_rows + [outlier_row]
    state = {
        "findings": [
            {
                "source": "sql_tool",
                "subquestion": "test",
                "sql": "SELECT x, y FROM t",
                "tables": ["t"],
                "rows": rows,
                "columns": ["x", "y"],
                "attempts": 1,
            }
        ]
    }

    # Act
    result = stats_tool_node(state)

    # Assert
    analyses = [f["analysis"] for f in result["findings"]]
    assert "anomaly" in analyses
    anomaly_findings = [f for f in result["findings"] if f["analysis"] == "anomaly"]
    assert len(anomaly_findings) >= 1
    # Vérifier la structure
    for af in anomaly_findings:
        assert "column" in af
        assert "anomalies" in af
        assert len(af["anomalies"]) >= 1
