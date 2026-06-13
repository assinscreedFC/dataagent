"""Tests end-to-end du graphe LangGraph.

Stratégie : vraie I/O DuckDB (fixture conn de conftest.py), mock UNIQUEMENT les LLMs.
- build_graph() compile le graphe branché (Phase 4 — 7 nodes, TOOL-04/05/06)
- run() produit plan[], report markdown sourcé, findings avec sql, max_iterations=5
- db injectée via conn=conn reste identique dans le state final (D-05, criterion #4)
"""

import pytest

from dataagent.agent.graph import build_graph, run


# ---------------------------------------------------------------------------
# Fake LLM helpers (seul mock autorisé)
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


# ---------------------------------------------------------------------------
# Tests structure du graphe
# ---------------------------------------------------------------------------


def test_build_graph_compiles():
    """build_graph() doit retourner un objet non None (D-04, GRAPH-02)."""
    app = build_graph()
    assert app is not None


def test_graph_branched_structure():
    """Le graphe branché doit contenir les 7 nodes : planner, router, sql_tool, stats_tool, viz_tool, critic, synthesizer."""
    app = build_graph()
    graph_nodes = app.get_graph().nodes
    expected = ["planner", "router", "sql_tool", "stats_tool", "viz_tool", "critic", "synthesizer"]
    for node in expected:
        assert node in graph_nodes, f"Node '{node}' absent du graphe branché"


# ---------------------------------------------------------------------------
# Test end-to-end
# ---------------------------------------------------------------------------


def test_run_end_to_end_produces_report(conn, monkeypatch):
    """run() doit produire un état final complet avec plan, report, findings et max_iterations.

    LLM mocké pour déterminisme ; DuckDB réel (fixture conn).
    Vérifie les 5 critères de succès (criterion #2, #3, #4, #5).
    """
    from dataagent.agent import nodes

    # Flash pour planner, sql_tool, critic : séquence déterministe
    # Graphe branché : appel 1=planner, 2=sql_tool, 3=critic (SUFFISANT -> synth au 1er tour)
    flash_calls: list[int] = [0]

    class _FakeFlash:
        """Fake Flash : planner (1), sql_tool (2), critic SUFFISANT (3+)."""

        def invoke(self, messages):  # noqa: ANN001
            flash_calls[0] += 1
            if flash_calls[0] == 1:
                # Premier appel : planner -> retourne une sous-question SQL
                return _FakeResponse("CA total 2017 ?")
            elif flash_calls[0] == 2:
                # Deuxième appel : sql_tool -> SQL valide sur mini Olist
                return _FakeResponse(
                    "SELECT SUM(price) AS total_ca FROM order_items"
                )
            else:
                # Troisième appel+ : critic -> SUFFISANT (sortie au 1er tour)
                return _FakeResponse("SUFFISANT")

    # Pro pour synthesizer : retourne un rapport markdown citant orders
    class _FakePro:
        def invoke(self, messages):  # noqa: ANN001
            return _FakeResponse(
                "## Rapport CA 2017\n\n"
                "Le CA total pour 2017 est de **350€**.\n\n"
                "**Sources** : tables `orders` et `order_items`, "
                "query : `SELECT SUM(price) AS total_ca FROM order_items`."
            )

    monkeypatch.setattr(nodes, "flash_llm", lambda: _FakeFlash())
    monkeypatch.setattr(nodes, "pro_llm", lambda: _FakePro())

    final = run("CA total 2017 ?", conn=conn)

    # criterion #5 : plan[] non vide
    assert final["plan"], "plan[] est vide"
    assert isinstance(final["plan"], list)
    assert len(final["plan"]) >= 1

    # criterion #2 : report est une str markdown non vide citant une source
    assert final["report"], "report est vide"
    assert isinstance(final["report"], str)
    assert "orders" in final["report"], "report ne cite aucune source (orders)"

    # findings avec au moins un finding contenant une clé 'sql'
    assert final["findings"], "findings est vide"
    assert any("sql" in f for f in final["findings"]), "Aucun finding avec clé 'sql'"

    # criterion #3 : max_iterations == 5 (hard stop observable)
    assert final["max_iterations"] == 5, (
        f"max_iterations == {final['max_iterations']}, attendu 5"
    )
    assert final["iterations"] >= 1, (
        f"iterations == {final['iterations']}, attendu >= 1"
    )

    # criterion #4 : la connexion DuckDB injectée est la même dans le state final
    assert final["db"] is conn, "db dans le state final n'est pas la conn injectée"
