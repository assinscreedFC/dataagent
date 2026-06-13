---
phase: 07-hardening-bug-fixes
plan: "02"
subsystem: security-api
tags: [hardening, sql-guard, loader, api, render, lifespan, xss, write-guard]
dependency_graph:
  requires: [schema-in-state, _as_text-helper]
  provides: [write-ddl-guard, table-name-validation, html-escape, filtered-findings, lifespan-conn, max-length-ask]
  affects: [config.py, nodes.py, loader.py, render.py, api.py]
tech_stack:
  added: []
  patterns: [word-boundary-regex-guard, html-escape-attribute, lifespan-fastapi, pydantic-max-length, findings-filter]
key_files:
  created:
    - (tests appended to existing files)
  modified:
    - src/dataagent/config.py
    - src/dataagent/agent/nodes.py
    - src/dataagent/data/loader.py
    - src/dataagent/render.py
    - src/dataagent/api.py
    - tests/test_nodes.py
    - tests/test_loader.py
    - tests/test_render.py
    - tests/test_api.py
decisions:
  - "D-04 (HARD-03): SQL_FORBIDDEN_KEYWORDS + _is_write_sql regex word-boundary; guard in _execute_subquestion before validate/exec, no retry on write"
  - "D-05 (HARD-04): _TABLE_NAME_RE ^[A-Za-z_][A-Za-z0-9_]*$ in loader; non-conforming file skipped with warning"
  - "D-06 (HARD-05): max_length=2000 on AskRequest.question; _filter_findings removes sql/rows/columns; ?debug=true opt-in for full findings"
  - "D-07 (HARD-06): html.escape(png_path, quote=True) before injection into <img src> attribute in render.py"
  - "D-12 (HARD-11): FastAPI lifespan opens persistent DuckDB conn at startup; ask() uses getattr(app.state, 'conn', None) for test compat"
metrics:
  duration_minutes: 20
  completed_date: "2026-06-13"
  tasks_completed: 3
  files_changed: 9
---

# Phase 7 Plan 02: Security Hardening — SQL Guard, Loader, /ask, Render, Lifespan Summary

Write/DDL guard on LLM-generated SQL, table name validation before DDL interpolation, XSS escape in render, /ask bounded + findings filtered, and persistent DuckDB connection via FastAPI lifespan.

## Tasks Completed

| Task | Name | Commit | Files |
|------|------|--------|-------|
| 1 | Write/DDL guard (HARD-03) + table name validation (HARD-04) | d80a855 | config.py, nodes.py, loader.py, test_nodes.py, test_loader.py |
| 2 | html.escape in render.py (HARD-06) | 03f6ed2 | render.py, test_render.py |
| 3 | /ask max_length + filtered findings + lifespan conn (HARD-05, HARD-11) | d97ffd1 | api.py, test_api.py |

## Decisions Made

- **D-04 (HARD-03):** `SQL_FORBIDDEN_KEYWORDS` tuple in config.py (14 keywords). `_is_write_sql(sql)` compiled regex `\b(DROP|DELETE|…)\b` IGNORECASE at module level. In `_execute_subquestion`, guard fires after SQL generation and BEFORE `_validate_sql`/exec — returns error finding immediately, no retry on write motif.
- **D-05 (HARD-04):** `_TABLE_NAME_RE = re.compile(r"^[A-Za-z_][A-Za-z0-9_]*$")` in loader.py. Non-conforming table names skip the file with `logger.warning()` and `continue` — does not crash the rest of the load. `FileNotFoundError` still raised if all files skipped (loaded remains empty).
- **D-06 (HARD-05):** `AskRequest.question` gets `max_length=2000` alongside existing `min_length=1`. `_filter_findings()` helper strips `sql`, `rows`, `columns` from each finding dict. `?debug=true` query param on `/ask` returns unfiltered findings.
- **D-07 (HARD-06):** `import html` added to render.py. `png_path` escaped with `html.escape(png_path, quote=True)` before interpolation into `<img src="…">` attribute. Markdown body rendered unchanged (trust synthesizer).
- **D-12 (HARD-11):** `@asynccontextmanager lifespan(app)` creates one DuckDB connection at startup, stores it on `app.state.conn`, closes at shutdown. `ask()` retrieves it via `getattr(request.app.state, "conn", None)` — fallback `None` preserves monkeypatch compat in tests (fake_run accepts `conn=None`).

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] TestClient lifespan not triggered in module-level client**

- **Found during:** Task 3 — 6 tests failed with `AttributeError: 'State' object has no attribute 'conn'`
- **Issue:** `client = TestClient(api.app)` at module level does not trigger the lifespan context manager, so `app.state.conn` is never set.
- **Fix:** Changed `conn = request.app.state.conn` to `conn = getattr(request.app.state, "conn", None)` in the `ask()` handler. This is safe because monkeypatched `fake_run` accepts `conn=None` and ignores it. In production the lifespan runs normally and conn is always set.
- **Files modified:** `src/dataagent/api.py`
- **Commit:** d97ffd1

## Test Results

```
tests/test_loader.py    9 passed  (5 original + 4 new table-name validation)
tests/test_nodes.py    28 passed  (18 original + 10 new write-guard tests)
tests/test_render.py   15 passed  (12 original + 3 new html.escape tests)
tests/test_api.py      10 passed  (4 original + 6 new hardening tests)

Full suite: 212 passed, 3 expected failures (pre-existing from 07-01, deferred to 07-04)
```

## Acceptance Criteria Check

- `grep "SQL_FORBIDDEN_KEYWORDS" src/dataagent/config.py` → constante tuple 14 mots-clés ✓
- `grep "_is_write_sql" src/dataagent/agent/nodes.py` → définition + usage dans _execute_subquestion ✓
- `grep "non autorisé" src/dataagent/agent/nodes.py` → finding d'erreur write-guard ✓
- `grep "A-Za-z_" src/dataagent/data/loader.py` → regex _TABLE_NAME_RE ✓
- `grep "html.escape" src/dataagent/render.py` → échappement du png_path ✓
- `grep "max_length=2000" src/dataagent/api.py` → borne question ✓
- `grep "lifespan" src/dataagent/api.py` → contextmanager + passage à FastAPI ✓
- `grep "_filter_findings" src/dataagent/api.py` → définition + usage ✓
- `grep "from dataagent.agent.graph import run" src/dataagent/api.py` → point de monkeypatch préservé ✓

## Threat Surface Scan

No new network endpoints, auth paths, or schema changes at trust boundaries introduced. All changes reduce the attack surface (write guard, XSS escape, length bound, filtered response, table name validation).

## Known Stubs

None — all changes implement real security controls.

## Self-Check: PASSED
