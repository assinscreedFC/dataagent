"""Tests FastAPI — POST /ask (run mocké, zéro quota Gemini) + GET /health.

Stratégie (D-05) :
- TestClient exerce la couche HTTP réelle (routing, validation Pydantic, codes HTTP).
- run() est monkeypatché via monkeypatch.setattr(api, "run", fake_run) → aucun appel Gemini.
- Pas de DuckDB ouvert dans ces tests.

Couverture visée : >= 80 % sur src/dataagent/api.py.
"""

from fastapi.testclient import TestClient

from dataagent import api


# ---------------------------------------------------------------------------
# Fake run — retour déterministe, aucun quota Gemini (D-05)
# ---------------------------------------------------------------------------


def fake_run(question: str, conn=None, thread_id: str | None = None) -> dict:
    """Mock de dataagent.agent.graph.run — retourne un état final minimal."""
    return {
        "report": f"## Rapport\nRésultat pour : {question}",
        "findings": [
            {
                "source": "viz_tool",
                "png_path": "reports/chart_test.png",
            }
        ],
    }


# ---------------------------------------------------------------------------
# Client partagé
# ---------------------------------------------------------------------------

client = TestClient(api.app)


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


def test_health():
    """GET /health retourne 200 + {status: ok}."""
    resp = client.get("/health")
    assert resp.status_code == 200
    assert resp.json() == {"status": "ok"}


def test_ask_returns_report(monkeypatch):
    """POST /ask avec question valide retourne 200, report non vide, findings list."""
    monkeypatch.setattr(api, "run", fake_run)

    resp = client.post("/ask", json={"question": "CA total 2017 ?"})

    assert resp.status_code == 200
    data = resp.json()
    assert data["report"] != "", "report ne doit pas être vide"
    assert isinstance(data["findings"], list)
    assert len(data["findings"]) > 0


def test_ask_preserves_png_path(monkeypatch):
    """POST /ask préserve png_path dans findings (D-04)."""
    monkeypatch.setattr(api, "run", fake_run)

    resp = client.post("/ask", json={"question": "Quelles catégories ?"})

    assert resp.status_code == 200
    findings = resp.json()["findings"]
    assert findings[0]["png_path"] == "reports/chart_test.png"


def test_ask_missing_question():
    """POST /ask avec body vide retourne 422 (Pydantic validation, T-06-01)."""
    resp = client.post("/ask", json={})
    assert resp.status_code == 422


def test_ask_empty_question():
    """POST /ask avec question='' retourne 422 (min_length=1, T-06-01)."""
    resp = client.post("/ask", json={"question": ""})
    assert resp.status_code == 422


# ---------------------------------------------------------------------------
# Tests HARD-05 — max_length + findings filtrés (plan 07-02 Task 3)
# ---------------------------------------------------------------------------


def test_ask_question_too_long_returns_422():
    """POST /ask avec question de 2001 chars retourne 422 (max_length=2000, D-06)."""
    resp = client.post("/ask", json={"question": "x" * 2001})
    assert resp.status_code == 422


def test_ask_question_max_length_accepted(monkeypatch):
    """POST /ask avec question de exactement 2000 chars retourne 200."""
    monkeypatch.setattr(api, "run", fake_run)
    resp = client.post("/ask", json={"question": "q" * 2000})
    assert resp.status_code == 200


def test_ask_default_filters_sql_rows_columns(monkeypatch):
    """POST /ask par défaut ne retourne pas sql/rows/columns dans findings (D-06)."""

    def fake_run_with_sql(question: str, conn=None, thread_id=None) -> dict:
        return {
            "report": "## Rapport",
            "findings": [
                {
                    "source": "sql_tool",
                    "subquestion": "CA total ?",
                    "sql": "SELECT SUM(price) FROM order_items",
                    "tables": ["order_items"],
                    "rows": [(350.0,)],
                    "columns": ["sum(price)"],
                    "attempts": 1,
                }
            ],
        }

    monkeypatch.setattr(api, "run", fake_run_with_sql)
    resp = client.post("/ask", json={"question": "CA total ?"})

    assert resp.status_code == 200
    finding = resp.json()["findings"][0]
    assert "sql" not in finding, "sql ne doit pas être exposé par défaut"
    assert "rows" not in finding, "rows ne doit pas être exposé par défaut"
    assert "columns" not in finding, "columns ne doit pas être exposé par défaut"


def test_ask_default_preserves_source_and_tables(monkeypatch):
    """POST /ask conserve source/subquestion/tables dans les findings filtrés."""

    def fake_run_with_sql(question: str, conn=None, thread_id=None) -> dict:
        return {
            "report": "## Rapport",
            "findings": [
                {
                    "source": "sql_tool",
                    "subquestion": "CA total ?",
                    "sql": "SELECT SUM(price) FROM order_items",
                    "tables": ["order_items"],
                    "rows": [(350.0,)],
                    "columns": ["sum(price)"],
                }
            ],
        }

    monkeypatch.setattr(api, "run", fake_run_with_sql)
    resp = client.post("/ask", json={"question": "CA total ?"})

    assert resp.status_code == 200
    finding = resp.json()["findings"][0]
    assert finding["source"] == "sql_tool"
    assert finding["subquestion"] == "CA total ?"
    assert finding["tables"] == ["order_items"]


def test_ask_debug_returns_full_findings(monkeypatch):
    """POST /ask?debug=true retourne findings complets avec sql/rows/columns."""

    def fake_run_with_sql(question: str, conn=None, thread_id=None) -> dict:
        return {
            "report": "## Rapport",
            "findings": [
                {
                    "source": "sql_tool",
                    "sql": "SELECT 1",
                    "rows": [(1,)],
                    "columns": ["1"],
                }
            ],
        }

    monkeypatch.setattr(api, "run", fake_run_with_sql)
    resp = client.post("/ask?debug=true", json={"question": "Test ?"})

    assert resp.status_code == 200
    finding = resp.json()["findings"][0]
    assert "sql" in finding
    assert "rows" in finding
    assert "columns" in finding
