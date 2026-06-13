"""Tests des nodes LangGraph : schema_introspect, planner_node, sql_tool_node, synthesizer_node.

Stratégie : vraie I/O DuckDB (fixture conn de conftest.py), mock UNIQUEMENT les LLMs.
"""

import pytest

from dataagent.agent.schema_introspect import schema_description
from dataagent.agent.state import initial_state
from dataagent.config import SQL_MAX_RETRIES


# ---------------------------------------------------------------------------
# Fake LLM helper (le seul mock autorisé : appel réseau LLM)
# ---------------------------------------------------------------------------

class _FakeResponse:
    """Simule la réponse d'un ChatGoogleGenerativeAI.invoke()."""

    def __init__(self, content: str) -> None:
        self.content = content


class _FakeLLM:
    """LLM factice dont .invoke() retourne un contenu prédéfini."""

    def __init__(self, content: str) -> None:
        self._content = content

    def invoke(self, messages):  # noqa: ANN001
        return _FakeResponse(self._content)


class _SequenceLLM:
    """LLM factice dont .invoke() retourne les contenus en séquence (round-robin sur le dernier)."""

    def __init__(self, contents: list) -> None:
        self._contents = contents
        self._index = 0

    def invoke(self, messages):  # noqa: ANN001
        content = self._contents[min(self._index, len(self._contents) - 1)]
        self._index += 1
        return _FakeResponse(content)


# ---------------------------------------------------------------------------
# Tests schema_description (Task 1)
# ---------------------------------------------------------------------------


def test_schema_description_returns_nonempty_string(conn):
    """schema_description doit retourner une str non vide."""
    result = schema_description(conn)
    assert isinstance(result, str)
    assert len(result) > 0


def test_schema_description_lists_olist_tables(conn):
    """schema_description doit mentionner les tables du mini Olist."""
    result = schema_description(conn)
    for table in ("orders", "order_items", "products", "order_reviews"):
        assert table in result, f"Table '{table}' absente de la description"


def test_schema_description_lists_orders_columns(conn):
    """Pour la table orders, la description doit contenir au moins order_id."""
    result = schema_description(conn)
    assert "order_id" in result


def test_schema_description_is_deterministic(conn):
    """Deux appels successifs sur la même connexion retournent le même résultat."""
    assert schema_description(conn) == schema_description(conn)


# ---------------------------------------------------------------------------
# Tests planner_node (Task 2)
# ---------------------------------------------------------------------------


def test_planner_node_returns_nonempty_plan(conn, monkeypatch):
    """planner_node doit retourner un plan[] non vide avec les sous-questions parsées."""
    from dataagent.agent import nodes

    fake_llm = _FakeLLM("CA 2017 ?\nNombre de commandes ?")
    monkeypatch.setattr(nodes, "flash_llm", lambda: fake_llm)

    state = initial_state("CA total 2017 ?", conn)
    result = nodes.planner_node(state)

    assert "plan" in result
    assert isinstance(result["plan"], list)
    assert len(result["plan"]) >= 1
    assert result["plan"] == ["CA 2017 ?", "Nombre de commandes ?"]


def test_planner_node_single_line_plan(conn, monkeypatch):
    """Si le LLM retourne une seule ligne, plan doit contenir cette ligne."""
    from dataagent.agent import nodes

    fake_llm = _FakeLLM("CA total 2017 ?")
    monkeypatch.setattr(nodes, "flash_llm", lambda: fake_llm)

    state = initial_state("CA total 2017 ?", conn)
    result = nodes.planner_node(state)

    assert result["plan"] == ["CA total 2017 ?"]


def test_planner_node_ignores_empty_lines(conn, monkeypatch):
    """planner_node doit ignorer les lignes vides dans la réponse LLM."""
    from dataagent.agent import nodes

    fake_llm = _FakeLLM("\nCA 2017 ?\n\nNombre de commandes ?\n")
    monkeypatch.setattr(nodes, "flash_llm", lambda: fake_llm)

    state = initial_state("CA total 2017 ?", conn)
    result = nodes.planner_node(state)

    assert result["plan"] == ["CA 2017 ?", "Nombre de commandes ?"]


# ---------------------------------------------------------------------------
# Tests sql_tool_node (Task 2)
# ---------------------------------------------------------------------------


def test_sql_tool_executes_and_pushes_finding(conn, monkeypatch):
    """sql_tool_node doit exécuter le SQL sur DuckDB et pousser un finding sourcé."""
    from dataagent.agent import nodes

    fake_llm = _FakeLLM("SELECT COUNT(*) AS n FROM orders")
    monkeypatch.setattr(nodes, "flash_llm", lambda: fake_llm)

    state = initial_state("Combien de commandes ?", conn)
    state["plan"] = ["Combien de commandes au total ?"]

    result = nodes.sql_tool_node(state)

    assert "findings" in result
    assert len(result["findings"]) >= 1
    finding = result["findings"][0]
    assert "sql" in finding
    assert "rows" in finding
    assert "columns" in finding
    assert finding["source"] == "sql_tool"
    # iterations n'est plus retourné par sql_tool_node (possédé par critic, D-06 Phase 4)
    assert "iterations" not in result


def test_sql_tool_handles_sql_error(conn, monkeypatch):
    """Sur SQL invalide, sql_tool_node doit pousser un finding d'erreur sans crasher."""
    from dataagent.agent import nodes

    fake_llm = _FakeLLM("SELECT * FROM table_inexistante")
    monkeypatch.setattr(nodes, "flash_llm", lambda: fake_llm)

    state = initial_state("Question quelconque ?", conn)
    state["plan"] = ["Sous-question invalide ?"]

    # Ne doit pas lever d'exception
    result = nodes.sql_tool_node(state)

    assert "findings" in result
    finding = result["findings"][0]
    assert "error" in finding
    assert finding["source"] == "sql_tool"
    # iterations n'est plus retourné par sql_tool_node (possédé par critic, D-06 Phase 4)
    assert "iterations" not in result


def test_sql_tool_strips_markdown_fence(conn, monkeypatch):
    """sql_tool_node doit nettoyer les fences ```sql ... ``` si présentes."""
    from dataagent.agent import nodes

    fake_llm = _FakeLLM("```sql\nSELECT COUNT(*) AS n FROM orders\n```")
    monkeypatch.setattr(nodes, "flash_llm", lambda: fake_llm)

    state = initial_state("Combien de commandes ?", conn)
    state["plan"] = ["Combien de commandes au total ?"]

    result = nodes.sql_tool_node(state)

    assert "findings" in result
    finding = result["findings"][0]
    assert "rows" in finding  # exécution réussie
    assert "```" not in finding["sql"]


# ---------------------------------------------------------------------------
# Tests synthesizer_node (Task 3)
# ---------------------------------------------------------------------------


def test_synthesizer_produces_markdown_with_sources(conn, monkeypatch):
    """synthesizer_node doit retourner un rapport str non vide."""
    from dataagent.agent import nodes

    fake_report = "## Rapport\n\nLe CA total est de 350€.\n\nSource: table `orders`."
    fake_llm = _FakeLLM(fake_report)
    monkeypatch.setattr(nodes, "pro_llm", lambda: fake_llm)

    state = initial_state("CA total ?", conn)
    state["findings"] = [
        {
            "source": "sql_tool",
            "subquestion": "CA total ?",
            "sql": "SELECT SUM(price) FROM order_items",
            "tables": ["order_items"],
            "rows": [(350.0,)],
            "columns": ["sum(price)"],
        }
    ]

    result = nodes.synthesizer_node(state)

    assert "report" in result
    assert isinstance(result["report"], str)
    assert len(result["report"]) > 0


def test_synthesizer_handles_empty_findings(conn, monkeypatch):
    """Avec findings vides, synthesizer_node doit produire un rapport d'échec en markdown."""
    from dataagent.agent import nodes

    fake_report = "## Rapport\n\nAucune donnée disponible."
    fake_llm = _FakeLLM(fake_report)
    monkeypatch.setattr(nodes, "pro_llm", lambda: fake_llm)

    state = initial_state("CA total ?", conn)
    state["findings"] = []

    result = nodes.synthesizer_node(state)

    assert "report" in result
    assert isinstance(result["report"], str)
    assert len(result["report"]) > 0


def test_synthesizer_handles_error_findings(conn, monkeypatch):
    """Avec tous findings en erreur, synthesizer_node doit quand même retourner un rapport."""
    from dataagent.agent import nodes

    fake_report = "## Rapport\n\nLes requêtes ont échoué."
    fake_llm = _FakeLLM(fake_report)
    monkeypatch.setattr(nodes, "pro_llm", lambda: fake_llm)

    state = initial_state("CA total ?", conn)
    state["findings"] = [
        {
            "source": "sql_tool",
            "subquestion": "CA total ?",
            "sql": "SELECT * FROM table_inexistante",
            "error": "Table 'table_inexistante' not found",
        }
    ]

    result = nodes.synthesizer_node(state)

    assert "report" in result
    assert len(result["report"]) > 0


# ---------------------------------------------------------------------------
# Tests sql_tool_node durci — Phase 2 (validation EXPLAIN + retry borné)
# ---------------------------------------------------------------------------


def test_sql_tool_retries_and_corrects(conn, monkeypatch):
    """Génération initiale invalide puis correcte → finding succès avec attempts == 2."""
    from dataagent.agent import nodes

    seq_llm = _SequenceLLM(
        ["SELECT * FROM table_inexistante", "SELECT COUNT(*) AS n FROM orders"]
    )
    monkeypatch.setattr(nodes, "flash_llm", lambda: seq_llm)

    state = initial_state("Combien de commandes ?", conn)
    state["plan"] = ["Combien de commandes au total ?"]

    result = nodes.sql_tool_node(state)

    assert "findings" in result
    finding = result["findings"][0]
    assert "error" not in finding, f"Attendu finding succès, reçu erreur: {finding.get('error')}"
    assert "rows" in finding
    assert "columns" in finding
    assert finding.get("attempts") == 2


def test_sql_tool_valid_first_try_attempts_one(conn, monkeypatch):
    """Query valide dès le premier coup → finding succès avec attempts == 1 et format Phase 1."""
    from dataagent.agent import nodes

    fake_llm = _FakeLLM("SELECT COUNT(*) AS n FROM orders")
    monkeypatch.setattr(nodes, "flash_llm", lambda: fake_llm)

    state = initial_state("Combien de commandes ?", conn)
    state["plan"] = ["Combien de commandes au total ?"]

    result = nodes.sql_tool_node(state)

    assert "findings" in result
    finding = result["findings"][0]
    # Format Phase 1 préservé
    assert finding["source"] == "sql_tool"
    assert "subquestion" in finding
    assert "sql" in finding
    assert "tables" in finding
    assert "rows" in finding
    assert "columns" in finding
    # Nouvelle clé Phase 2
    assert finding.get("attempts") == 1


def test_sql_tool_exhausts_retries_pushes_error(conn, monkeypatch):
    """Toutes les tentatives échouent → finding d'erreur avec attempts == SQL_MAX_RETRIES+1, sans exception."""
    from dataagent.agent import nodes

    # Toujours une query invalide
    always_bad = _SequenceLLM(["SELECT * FROM table_inexistante"] * (SQL_MAX_RETRIES + 2))
    monkeypatch.setattr(nodes, "flash_llm", lambda: always_bad)

    state = initial_state("Question quelconque ?", conn)
    state["plan"] = ["Sous-question dont SQL échoue toujours ?"]

    # Ne doit pas lever d'exception
    result = nodes.sql_tool_node(state)

    assert "findings" in result
    finding = result["findings"][0]
    assert "error" in finding
    assert finding["source"] == "sql_tool"
    assert finding.get("attempts") == SQL_MAX_RETRIES + 1
    # iterations n'est plus retourné par sql_tool_node (possédé par critic, D-06 Phase 4)
    assert "iterations" not in result


# ---------------------------------------------------------------------------
# Tests end-to-end node + couverture ≥80% — Phase 2 Task 3
# ---------------------------------------------------------------------------


def test_sql_tool_node_recovers_from_failed_initial_sql(conn, monkeypatch):
    """sql_tool_node récupère sur SQL initial invalide et produit un finding correct (critère #4)."""
    from dataagent.agent import nodes

    seq_llm = _SequenceLLM(
        ["SELECT * FROM commandes_inexistantes", "SELECT COUNT(*) AS n FROM orders"]
    )
    monkeypatch.setattr(nodes, "flash_llm", lambda: seq_llm)

    state = initial_state("Combien de commandes ?", conn)
    state["plan"] = ["Combien de commandes ?"]
    initial_iterations = state["iterations"]

    result = nodes.sql_tool_node(state)

    assert "findings" in result
    finding = result["findings"][0]
    # Pas d'erreur — finding succès malgré SQL initial invalide
    assert "error" not in finding, f"Attendu finding succès, reçu erreur: {finding.get('error')}"
    assert "rows" in finding
    assert len(finding["rows"]) > 0
    # iterations n'est plus retourné par sql_tool_node (possédé par critic, D-06 Phase 4)
    assert "iterations" not in result


def test_validate_sql_rejects_unknown_column(conn):
    """_validate_sql rejette une colonne inexistante via EXPLAIN (critère #1 au niveau colonne)."""
    from dataagent.agent.nodes import _validate_sql

    result = _validate_sql(conn, "SELECT colonne_bidon FROM orders")
    assert result is not None
    assert isinstance(result, str)
    assert len(result) > 0


# ---------------------------------------------------------------------------
# Tests write/DDL guard — HARD-03 (D-04, plan 07-02 Task 1)
# ---------------------------------------------------------------------------


def test_is_write_sql_detects_drop():
    """_is_write_sql retourne True sur DROP TABLE."""
    from dataagent.agent.nodes import _is_write_sql

    assert _is_write_sql("DROP TABLE orders") is True


def test_is_write_sql_detects_delete():
    """_is_write_sql retourne True sur DELETE FROM."""
    from dataagent.agent.nodes import _is_write_sql

    assert _is_write_sql("DELETE FROM orders") is True


def test_is_write_sql_false_positive_guard():
    """_is_write_sql retourne False sur SELECT contenant 'undropped' (word-boundary)."""
    from dataagent.agent.nodes import _is_write_sql

    assert _is_write_sql("SELECT * FROM orders WHERE name='undropped'") is False


def test_is_write_sql_select_passes():
    """_is_write_sql retourne False sur un SELECT normal."""
    from dataagent.agent.nodes import _is_write_sql

    assert _is_write_sql("SELECT COUNT(*) FROM orders") is False


def test_is_write_sql_with_passes():
    """_is_write_sql retourne False sur un CTE WITH."""
    from dataagent.agent.nodes import _is_write_sql

    assert _is_write_sql("WITH t AS (SELECT 1) SELECT * FROM t") is False


def test_is_write_sql_explain_passes():
    """_is_write_sql retourne False sur EXPLAIN SELECT."""
    from dataagent.agent.nodes import _is_write_sql

    assert _is_write_sql("EXPLAIN SELECT 1") is False


def test_is_write_sql_detects_insert():
    """_is_write_sql retourne True sur INSERT INTO."""
    from dataagent.agent.nodes import _is_write_sql

    assert _is_write_sql("INSERT INTO orders VALUES (1)") is True


def test_is_write_sql_detects_create():
    """_is_write_sql retourne True sur CREATE TABLE."""
    from dataagent.agent.nodes import _is_write_sql

    assert _is_write_sql("CREATE TABLE foo AS SELECT 1") is True


def test_execute_subquestion_write_guard_blocks_drop(conn, monkeypatch):
    """_execute_subquestion retourne un finding d'erreur sans exécuter DROP TABLE."""
    from dataagent.agent import nodes
    from dataagent.agent.schema_introspect import schema_description

    # LLM génère un SQL write/DDL
    monkeypatch.setattr(nodes, "flash_llm", lambda: _FakeLLM("DROP TABLE orders"))

    schema = schema_description(conn)
    # Vérifier que la table orders existe avant la tentative
    count_before = conn.execute("SELECT COUNT(*) FROM orders").fetchone()[0]

    finding = nodes._execute_subquestion(conn, schema, "Supprimer les commandes")

    # Finding d'erreur — pas d'exécution
    assert "error" in finding
    assert (
        "non autorisé" in finding["error"].lower()
        or "write" in finding["error"].lower()
        or "bloqué" in finding["error"].lower()
    )
    assert finding["source"] == "sql_tool"

    # Table intacte — pas de retry, pas d'exécution
    count_after = conn.execute("SELECT COUNT(*) FROM orders").fetchone()[0]
    assert count_after == count_before


def test_execute_subquestion_write_guard_no_retry(conn, monkeypatch):
    """Write guard bloque immédiatement sans retry (LLM appelé une seule fois)."""
    from dataagent.agent import nodes
    from dataagent.agent.schema_introspect import schema_description

    call_count = 0

    class _CountingLLM:
        def invoke(self, messages):  # noqa: ANN001
            nonlocal call_count
            call_count += 1

            class _R:
                content = "DROP TABLE orders"

            return _R()

    monkeypatch.setattr(nodes, "flash_llm", lambda: _CountingLLM())

    schema = schema_description(conn)
    finding = nodes._execute_subquestion(conn, schema, "Supprimer les commandes")

    assert "error" in finding
    assert call_count == 1, f"LLM appelé {call_count} fois — attendu 1 (pas de retry)"
