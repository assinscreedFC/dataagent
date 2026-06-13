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
