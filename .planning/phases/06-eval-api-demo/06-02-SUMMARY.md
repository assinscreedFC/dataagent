---
phase: 06-eval-api-demo
plan: 02
subsystem: api
tags: [fastapi, pydantic, testclient, http, api]
dependency_graph:
  requires: [dataagent.agent.graph.run]
  provides: [dataagent.api.app, POST /ask, GET /health]
  affects: []
tech_stack:
  added: []
  patterns: [FastAPI sync handler in threadpool, Pydantic boundary validation, monkeypatch TestClient mock]
key_files:
  created:
    - src/dataagent/api.py
    - tests/test_api.py
  modified: []
decisions:
  - "AskRequest min_length=1 rejects empty question at Pydantic layer → 422 (T-06-01)"
  - "run() imported at module top so monkeypatch.setattr(api, 'run', fake_run) works in tests (D-05)"
  - "Sync handlers used — FastAPI threadpool correct for blocking run() in single-user Labs demo (D-04)"
  - "Per-request DuckDB conn via run(conn=None) — no lifespan complexity (D-04 Claude's Discretion)"
metrics:
  duration_min: 12
  completed_date: "2026-06-13"
  tasks_completed: 2
  files_created: 2
  files_modified: 0
---

# Phase 6 Plan 2: FastAPI API Summary

**One-liner:** FastAPI app `POST /ask` + `GET /health` exposant `run()` avec validation Pydantic min_length=1, 100 % testée via TestClient avec run() mocké (zéro quota Gemini).

## Tasks Completed

| Task | Name | Commit | Files |
|------|------|--------|-------|
| 1 | FastAPI app — POST /ask + GET /health | c981a98 | src/dataagent/api.py |
| 2 | TestClient tests — mocked run(), no quota | 68ddd89 | tests/test_api.py |

## Implementation Notes

`src/dataagent/api.py` expose deux routes :

- `GET /health` → `{"status": "ok"}` — health check sans dépendances.
- `POST /ask` body `AskRequest(question: str, min_length=1)` → appelle `run(body.question)` → retourne `{"report": str, "findings": list}`. Les findings incluent `png_path` pour les viz (D-04).

L'import `from dataagent.agent.graph import run` au niveau module permet le patch `monkeypatch.setattr(api, "run", fake_run)` dans les tests (D-05).

## Verification Results

- `from dataagent.api import app` : ok — routes `/ask` et `/health` enregistrées.
- `pytest tests/test_api.py` : 5/5 tests passent.
- `pytest tests/` (suite complète) : 0 régression.
- Coverage api.py : 100 % (13/13 statements).

## Deviations from Plan

None — plan exécuté exactement comme écrit.

## Threat Surface Scan

Aucune nouvelle surface non couverte par le threat model du plan :

| Flag | File | Description |
|------|------|-------------|
| T-06-01 mitigated | src/dataagent/api.py | AskRequest min_length=1 valide question à l'entrée HTTP |
| T-06-02 mitigated | src/dataagent/api.py | Seuls report+findings retournés — pas de stack trace ni secret |
| T-06-03 accepted | src/dataagent/api.py | Pas de rate limiting — usage Labs mono-utilisateur documenté |
| T-06-04 accepted | src/dataagent/api.py | SQL injection mitigée en amont par sql_tool (TOOL-01, Phase 2) |

## Known Stubs

None.

## Self-Check: PASSED

- src/dataagent/api.py : FOUND
- tests/test_api.py : FOUND
- Commit c981a98 : FOUND
- Commit 68ddd89 : FOUND
