"""Tests de resumabilité du graphe LangGraph via SqliteSaver (TOOL-07, Phase 5).

Stratégie : SQLite réel + DuckDB réel (fixture conn), LLM mocké déterministe.
Aucun appel LLM réel — pas de quota consommé.

Comportement LangGraph checkpoint avec thread_id sur graphe terminé :
  - Run 1 → graphe exécuté, état checkpointé dans SQLite
  - Run 2 (même thread_id) → graphe ré-exécuté depuis START, state_input mergé avec
    le checkpoint. Les channels avec reducer `add` (findings) ACCUMULENT les deux runs ;
    les channels sans reducer (plan, iterations) sont écrasés par le run 2.
  - Ce comportement est LA preuve que le checkpointer est actif : sans lui, run 2 ne
    lirait pas l'état du run 1 (findings ne s'accumulerait pas).

Critères couverts :
  #1 — build_graph(checkpointer=...) compile sans erreur
  #2 — run avec thread_id peuple le store SQLite (saver.list retourne ≥1 checkpoint)
  #3 — le checkpointer est actif : findings accumulés sur run 2 (add reducer + checkpoint)
  #4 — connexion DuckDB (UntrackedValue) ré-injectée fraîche à la reprise (D-05)
  #5 — run sans thread_id reste éphémère (aucun fichier SQLite créé, report produit)
"""

import sqlite3

import pytest
from langgraph.checkpoint.sqlite import SqliteSaver

from dataagent.agent.graph import build_graph, run
from dataagent.data.loader import connect, load_csvs_to_duckdb


# ---------------------------------------------------------------------------
# Fake LLM helpers (pattern identique à test_graph.py)
# ---------------------------------------------------------------------------


class _FakeResponse:
    """Simule la réponse d'un ChatGoogleGenerativeAI.invoke()."""

    def __init__(self, content: str) -> None:
        self.content = content


def _make_flash_llm(call_counter: list[int]):
    """Retourne un fake Flash LLM avec compteur d'appels partagé."""

    class _FakeFlash:
        def invoke(self, messages):  # noqa: ANN001
            call_counter[0] += 1
            n = call_counter[0]
            if n == 1:
                # Appel 1 : planner -> sous-question SQL
                return _FakeResponse("CA total 2017 ?")
            elif n == 2:
                # Appel 2 : sql_tool -> SQL valide sur mini Olist
                return _FakeResponse("SELECT SUM(price) AS total_ca FROM order_items")
            else:
                # Appel 3+ : critic -> SUFFISANT (sortie au 1er tour)
                return _FakeResponse("SUFFISANT")

    return _FakeFlash()


class _FakePro:
    """Fake Pro LLM pour le synthesizer."""

    def invoke(self, messages):  # noqa: ANN001
        return _FakeResponse(
            "## Rapport CA 2017\n\nCA total : **380€**.\n\n"
            "**Sources** : table `order_items`."
        )


# ---------------------------------------------------------------------------
# Fixture : connexion DuckDB fraîche (pour les runs de reprise — D-05)
# ---------------------------------------------------------------------------


@pytest.fixture
def fresh_conn(olist_csv_dir):
    """Crée une connexion DuckDB fraîche avec le mini Olist chargé.

    Séparée de la fixture `conn` pour simuler la ré-injection D-05 lors de la reprise :
    deux connexions distinctes, même données.
    """
    c = connect()
    load_csvs_to_duckdb(c, olist_csv_dir)
    yield c
    c.close()


# ---------------------------------------------------------------------------
# Test 1 : compile avec checkpointer (criterion #1)
# ---------------------------------------------------------------------------


def test_build_graph_with_checkpointer_compiles():
    """build_graph(checkpointer=SqliteSaver(...)) retourne un graphe non None (criterion #1)."""
    # Arrange
    saver_conn = sqlite3.connect(":memory:", check_same_thread=False)
    checkpointer = SqliteSaver(saver_conn)

    # Act
    app = build_graph(checkpointer=checkpointer)

    # Assert
    assert app is not None

    # Cleanup
    saver_conn.close()


def test_build_graph_without_checkpointer_compiles():
    """build_graph() sans arg compile comme avant (comportement Phase 4 intact)."""
    app = build_graph()
    assert app is not None


# ---------------------------------------------------------------------------
# Test 2 : store SQLite peuplé après run avec thread_id (criterion #2)
# ---------------------------------------------------------------------------


def test_run_with_thread_id_populates_sqlite_store(conn, monkeypatch, tmp_path):
    """run(..., thread_id='t1') écrit ≥1 checkpoint dans le store SQLite (criterion #2)."""
    from dataagent.agent import nodes

    # Arrange : monkeypatch CHECKPOINT_DB vers tmp_path
    ckpt_path = tmp_path / "ckpt.sqlite"
    monkeypatch.setattr("dataagent.agent.graph.CHECKPOINT_DB", ckpt_path)

    call_counter: list[int] = [0]
    monkeypatch.setattr(nodes, "flash_llm", lambda: _make_flash_llm(call_counter))
    monkeypatch.setattr(nodes, "pro_llm", lambda: _FakePro())

    # Act
    run("CA total 2017 ?", conn=conn, thread_id="t1")

    # Assert : le fichier SQLite existe et contient ≥1 checkpoint pour t1
    assert ckpt_path.exists(), "Le store SQLite n'a pas été créé"

    saver_conn = sqlite3.connect(str(ckpt_path), check_same_thread=False)
    try:
        saver = SqliteSaver(saver_conn)
        checkpoints = list(saver.list({"configurable": {"thread_id": "t1"}}))
        assert checkpoints, "Aucun checkpoint trouvé pour thread_id='t1'"
    finally:
        saver_conn.close()


# ---------------------------------------------------------------------------
# Test 3 : checkpointer actif — findings accumulés sur run 2 (criterion #3, D-04)
# ---------------------------------------------------------------------------


def test_checkpoint_active_findings_accumulate_across_runs(
    conn, fresh_conn, monkeypatch, tmp_path
):
    """Preuve que le checkpointer est actif : findings s'accumulent sur un 2e run.

    Comportement LangGraph avec checkpoint sur graphe terminé :
    - Run 1 : graphe exécuté, findings=[f1] checkpointé dans SQLite.
    - Run 2 (même thread_id) : graphe ré-exécuté depuis START, findings=[f1, f2]
      (reducer `add` merge les findings du checkpoint + du nouveau run).
    - Sans checkpointer (run éphémère), run 2 n'aurait que [f2] (pas d'accumulation).
    Cette accumulation prouve que le checkpoint est lu et mergé.
    """
    from dataagent.agent import nodes

    # Arrange
    ckpt_path = tmp_path / "ckpt_resume.sqlite"
    monkeypatch.setattr("dataagent.agent.graph.CHECKPOINT_DB", ckpt_path)

    # Run 1
    call_counter: list[int] = [0]
    monkeypatch.setattr(nodes, "flash_llm", lambda: _make_flash_llm(call_counter))
    monkeypatch.setattr(nodes, "pro_llm", lambda: _FakePro())
    result1 = run("CA total 2017 ?", conn=conn, thread_id="t2")
    findings_run1 = len(result1["findings"])
    assert findings_run1 >= 1, "Run 1 : aucun finding produit"

    # Run 2 (même thread_id, conn fraîche — ré-injection D-05)
    call_counter2: list[int] = [0]
    monkeypatch.setattr(nodes, "flash_llm", lambda: _make_flash_llm(call_counter2))
    monkeypatch.setattr(nodes, "pro_llm", lambda: _FakePro())
    result2 = run("CA total 2017 ?", conn=fresh_conn, thread_id="t2")
    findings_run2 = len(result2["findings"])

    # Assert : findings s'accumulent (add reducer + checkpoint actif)
    # Sans checkpointer : findings_run2 == findings_run1 (pas de merge)
    # Avec checkpointer : findings_run2 == findings_run1 * 2 (merge run1 + run2)
    assert findings_run2 > findings_run1, (
        f"findings run2 ({findings_run2}) n'est pas supérieur à run1 ({findings_run1}) "
        "— le checkpoint n'a pas été lu/mergé. "
        "Le reducer `add` devrait accumuler les findings des deux runs."
    )


# ---------------------------------------------------------------------------
# Test 4 : ré-injection conn fraîche à la reprise (D-05)
# ---------------------------------------------------------------------------


def test_resume_reinjects_fresh_conn(conn, fresh_conn, monkeypatch, tmp_path):
    """À chaque run, final['db'] est la conn fraîche injectée (UntrackedValue — D-05).

    Prouve que UntrackedValue n'est pas restauré depuis le checkpoint — la connexion
    DuckDB fournie à chaque run est disponible dans l'état final (pas None, pas l'ancienne).
    """
    from dataagent.agent import nodes

    # Arrange
    ckpt_path = tmp_path / "ckpt_conn.sqlite"
    monkeypatch.setattr("dataagent.agent.graph.CHECKPOINT_DB", ckpt_path)

    # Run 1
    call_counter: list[int] = [0]
    monkeypatch.setattr(nodes, "flash_llm", lambda: _make_flash_llm(call_counter))
    monkeypatch.setattr(nodes, "pro_llm", lambda: _FakePro())
    result1 = run("CA total 2017 ?", conn=conn, thread_id="t3")

    # Assert run 1 : db est la conn injectée (pas None)
    assert result1["db"] is not None, "Run 1 : db est None dans l'état final"
    assert result1["db"] is conn, "Run 1 : db n'est pas la conn injectée"

    # Run 2 (reprise avec fresh_conn — ré-injection D-05)
    call_counter2: list[int] = [0]
    monkeypatch.setattr(nodes, "flash_llm", lambda: _make_flash_llm(call_counter2))
    monkeypatch.setattr(nodes, "pro_llm", lambda: _FakePro())
    result2 = run("CA total 2017 ?", conn=fresh_conn, thread_id="t3")

    # Assert run 2 : db est fresh_conn (pas l'ancienne conn, pas None)
    assert result2["db"] is not None, "Run 2 : db est None dans l'état final"
    assert result2["db"] is not conn, (
        "Run 2 : db est l'ancienne connexion du run 1 — "
        "UntrackedValue devrait être ré-injecté avec fresh_conn"
    )


# ---------------------------------------------------------------------------
# Test 5 : run éphémère sans thread_id (D-03)
# ---------------------------------------------------------------------------


def test_ephemeral_run_without_thread_id_creates_no_checkpoint(
    conn, monkeypatch, tmp_path
):
    """run() sans thread_id reste éphémère : aucun fichier SQLite créé (D-03, criterion #5)."""
    from dataagent.agent import nodes

    # Arrange : monkeypatch CHECKPOINT_DB (ne doit PAS être créé)
    ckpt_path = tmp_path / "ckpt_ephemeral.sqlite"
    monkeypatch.setattr("dataagent.agent.graph.CHECKPOINT_DB", ckpt_path)

    call_counter: list[int] = [0]
    monkeypatch.setattr(nodes, "flash_llm", lambda: _make_flash_llm(call_counter))
    monkeypatch.setattr(nodes, "pro_llm", lambda: _FakePro())

    # Act
    result = run("CA total 2017 ?", conn=conn)

    # Assert : pas de fichier SQLite créé
    assert not ckpt_path.exists(), (
        "Un fichier SQLite a été créé pour un run éphémère (sans thread_id)"
    )

    # Et le run produit quand même un report (comportement Phase 4 intact)
    assert result["report"], "Run éphémère n'a pas produit de report"
    assert result["plan"], "Run éphémère n'a pas produit de plan"
