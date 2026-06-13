---
phase: 03-stats-viz-tools
plan: "02"
subsystem: viz-tool
tags: [viz, plotly, kaleido, png, deterministic, findings]
dependency_graph:
  requires: [03-01]
  provides: [viz_tool_node, render_chart]
  affects: [nodes.py, viz.py]
tech_stack:
  added: []
  patterns: [pure-function, findings-append-reducer, kaleido-png-export, slugify-path-safety]
key_files:
  created:
    - src/dataagent/agent/viz.py
    - tests/test_viz.py
  modified:
    - src/dataagent/agent/nodes.py
decisions:
  - "render_chart uses re.sub([^a-z0-9]+, '_') slugify for path-safe deterministic filenames (T-03-04)"
  - "kind heuristic: isinstance(first_x, str) -> bar, else line (D-06, simple and testable)"
  - "viz_tool_node renders only the first chartable sql_tool finding per call (one chart per invocation)"
  - "viz_tool_node does NOT increment iterations — router/critic owns that in Phase 4"
metrics:
  duration_minutes: 17
  completed_date: "2026-06-13"
  tasks_completed: 3
  files_changed: 3
requirements: [TOOL-03]
---

# Phase 3 Plan 02: Viz Tool Summary

**One-liner:** Plotly bar/line chart rendered to deterministic kaleido PNG in `config.REPORTS`, absolute path recorded in findings via `viz_tool_node`.

## What Was Built

- `src/dataagent/agent/viz.py` — Pure render function (no LLM, no randomness):
  - `render_chart(x, y, name, kind="auto") -> Path`: builds plotly figure, exports PNG via `fig.write_image()`, returns `path.resolve()`.
  - `_slugify(name)`: `re.sub(r"[^a-z0-9]+", "_", name.lower()).strip("_")` — path-traversal-safe, deterministic (T-03-04).
  - Kind heuristic (D-06): `isinstance(first_x_value, str)` → `go.Bar`; else `go.Scatter(mode="lines")`.
  - `REPORTS.mkdir(parents=True, exist_ok=True)` on every call (D-07).
- `src/dataagent/agent/nodes.py` — `viz_tool_node(state) -> dict` added:
  - Iterates findings, finds first `sql_tool` finding with ≥2 rows + ≥1 numeric column.
  - Calls `render_chart(x, y, name=subquestion)` → pushes `{"source": "viz_tool", "png_path": str(abs_path), "chart": "auto", "subquestion": ...}`.
  - Non-chartable data (error finding / <2 rows / no numeric col) → pushes `{"source": "viz_tool", "skipped": "no chartable data"}`, no crash (D-05, T-03-05).
  - `try/except` around DataFrame reconstruction and `render_chart` call.
- `tests/test_viz.py` — 21 real-I/O tests (no LLM mock, no DuckDB):
  - `TestRenderChartWritesPng` (3 tests): PNG exists, size>0, absolute path.
  - `TestRenderChartDeterministicFilename` (3 tests): same name → same path, slug chars, different names → different files.
  - `TestRenderChartAutoCreateReports` (1 test): REPORTS auto-created if absent.
  - `TestRenderChartKindHeuristic` (4 tests): auto/bar/line variants, no exception.
  - `TestVizToolNodeRendersChart` (5 tests): png_path in finding, file exists, absolute, source=viz_tool, chart key.
  - `TestVizToolNodeSkipsGracefully` (5 tests): empty findings, error finding, single row, no numeric column, returns dict with findings key.

## Commits

| Task | Commit | Description |
|------|--------|-------------|
| 1 | 6fe6c4a | feat(03-02): add render_chart (plotly -> kaleido PNG, deterministic slug filename) |
| 2 | 8b8324e | feat(03-02): add viz_tool_node in nodes.py + Task 2 tests |
| 3 | — | No code changes (100% coverage on viz.py, 78/78 full suite green) |

## Test Results

- `python -m pytest tests/test_viz.py`: 21/21 pass
- `python -m pytest`: 78/78 pass (zero regressions from Phase 1/2/3-01)
- `viz.py` coverage: **100%** (all branches exercised including bar/line heuristic and auto-mkdir)

## Deviations from Plan

None — plan executed exactly as written.

## Known Stubs

None — `render_chart` produces a real PNG file on disk. `viz_tool_node` records the real absolute path. No placeholder data.

## Threat Surface Scan

- T-03-04 (Tampering — filename from subquestion): mitigated via `_slugify()` — only `[a-z0-9_]` chars allowed in filename stem, fixed `.png` suffix, writes only inside `REPORTS`. No path traversal possible.
- T-03-05 (DoS — malformed findings): mitigated via `try/except` around DataFrame reconstruction and render; `<2 rows` guard; no numeric column guard → all routes to graceful `skipped` finding.
- T-03-06 (Info disclosure — PNG path): accepted — aggregate business data only, REPORTS is local and gitignored.

No new unplanned trust boundaries introduced.

## Self-Check

- [x] `src/dataagent/agent/viz.py` exists (24 statements, 100% coverage)
- [x] `tests/test_viz.py` exists (21 tests, all pass)
- [x] `viz_tool_node` in `src/dataagent/agent/nodes.py`
- [x] `render_chart` importable: `python -c "from dataagent.agent.viz import render_chart"`
- [x] `viz_tool_node` importable: `python -c "from dataagent.agent.nodes import viz_tool_node"`
- [x] Commits 6fe6c4a and 8b8324e exist
- [x] Full suite 78/78 green

## Self-Check: PASSED
