---
phase: 03-stats-viz-tools
plan: "01"
subsystem: stats-tool
tags: [stats, polars, correlation, anomaly-detection, z-score]
dependency_graph:
  requires: [02-01]
  provides: [stats_tool_node, correlation, detect_anomalies, ANOMALY_Z_THRESHOLD]
  affects: [nodes.py, config.py]
tech_stack:
  added: []
  patterns: [pure-functions, findings-append-reducer, z-score-anomaly]
key_files:
  created:
    - src/dataagent/agent/stats.py
    - tests/test_stats.py
  modified:
    - src/dataagent/config.py
    - src/dataagent/agent/nodes.py
decisions:
  - "Used [10]*20+[100] fixture (z~4.47) instead of plan's [10]*6+[100] (z~2.24 < 3.0 threshold) — math constraint, not a design change"
  - "stats_tool_node does NOT increment iterations (router/critic owns that in Phase 4)"
  - "correlation() converts Polars NaN to None to prevent NaN propagation in findings"
metrics:
  duration_minutes: 10
  completed_date: "2026-06-13"
  tasks_completed: 3
  files_changed: 4
requirements: [TOOL-02]
---

# Phase 3 Plan 01: Stats Tool Summary

**One-liner:** Pearson correlation + z-score anomaly detection via Polars pure functions, orchestrated by `stats_tool_node` pushing typed findings.

## What Was Built

- `src/dataagent/config.py` — Added `ANOMALY_Z_THRESHOLD = 3.0` constant (D-03).
- `src/dataagent/agent/stats.py` — Two pure functions:
  - `correlation(df, col_a, col_b) -> float | None`: Pearson via `pl.corr()`, guards for <2 rows / non-numeric columns / NaN (constant series).
  - `detect_anomalies(series, threshold) -> list[dict]`: Z-score with ddof=0, guards for len<2 / std==0. Each anomaly: `{"index": int, "value": float, "z_score": float}`.
- `src/dataagent/agent/nodes.py` — `stats_tool_node(state) -> dict` added:
  - Reconstructs Polars DataFrames from sql_tool findings (rows+columns).
  - Pushes `{"source": "stats_tool", "analysis": "correlation", ...}` for first numeric pair.
  - Pushes `{"source": "stats_tool", "analysis": "anomaly", ...}` per column with z-score outliers.
  - Falls back to `{"source": "stats_tool", "analysis": "insufficient_data", ...}` when no stats computable (D-04).
- `tests/test_stats.py` — 21 deterministic tests, no LLM mock, no DuckDB needed.

## Commits

| Task | Commit | Description |
|------|--------|-------------|
| 1 | 1d08b7a | feat(03-01): add ANOMALY_Z_THRESHOLD + pure stats functions |
| 2 | 46be34c | feat(03-01): add stats_tool_node orchestrating stats fns into findings |
| 3 | — | No new files (coverage at 94%, full suite green, no prod changes needed) |

## Test Results

- `python -m pytest tests/test_stats.py`: 21/21 pass
- `python -m pytest`: 53/53 pass (zero regressions from Phase 1/2)
- `stats.py` coverage: **94%** (missing: missing-column edge case line 29, None-in-series line 86)

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] Test fixture series mathematically incompatible with z-threshold**
- **Found during:** Task 1 GREEN phase
- **Issue:** Plan specified `[10,10,10,10,10,100]` with `ANOMALY_Z_THRESHOLD=3.0`. With ddof=0, z-score for 100 is ~2.24 — below threshold. Tests would never pass with this fixture.
- **Fix:** Replaced test fixtures with `[10]*20 + [100]` which gives z~4.47 > 3.0. Production code unchanged — only test data adjusted to be mathematically consistent with the configured threshold.
- **Files modified:** tests/test_stats.py
- **Commits:** 1d08b7a

## Known Stubs

None — all functions produce real computed values. No placeholder data flows to callers.

## Threat Surface Scan

T-03-02 (Tampering) mitigated as required: `try/except` wraps DataFrame reconstruction in `stats_tool_node`; non-numeric/insufficient data routes to explicit `insufficient_data` finding. No new unplanned trust boundaries introduced.

## Self-Check

- [x] `src/dataagent/agent/stats.py` exists
- [x] `tests/test_stats.py` exists
- [x] `ANOMALY_Z_THRESHOLD` in `src/dataagent/config.py`
- [x] `stats_tool_node` in `src/dataagent/agent/nodes.py`
- [x] Commits 1d08b7a and 46be34c exist
- [x] Full suite 53/53 green

## Self-Check: PASSED
