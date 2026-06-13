---
phase: 03-stats-viz-tools
verified: 2026-06-13T00:00:00Z
status: passed
score: 4/4 must-haves verified
re_verification: false
---

# Phase 3: Stats & Viz Tools — Verification Report

**Phase Goal:** L'agent dispose de deux nouveaux tools — analyse statistique (Polars) et visualisation (plotly) — qui enrichissent les findings.
**Verified:** 2026-06-13
**Status:** passed
**Re-verification:** No — initial verification

---

## Goal Achievement

### Observable Truths

| # | Truth | Status | Evidence |
|---|-------|--------|----------|
| 1 | stats_tool computes a Pearson correlation between two series and pushes it into findings | VERIFIED | `correlation()` in stats.py uses `pl.corr()`, returns float; `stats_tool_node` pushes `{"source":"stats_tool","analysis":"correlation","columns":[a,b],"value":float}`; `test_stats_tool_node_correlation_and_anomaly` asserts "correlation" in analyses |
| 2 | stats_tool detects >=1 anomaly on a known fixture series (z-score) | VERIFIED | `detect_anomalies([10]*20+[100])` produces z~4.47 > threshold 3.0; `test_stats_tool_node_anomaly_detected` asserts "anomaly" in analyses with >=1 anomaly entry |
| 3 | viz_tool produces a plotly PNG file on disk (kaleido) | VERIFIED | `render_chart()` calls `fig.write_image(str(path))` via kaleido; `TestRenderChartWritesPng` asserts `path.exists()` and `st_size > 0`; `TestVizToolNodeRendersChart.test_renders_png_from_sql_finding` asserts PNG on disk |
| 4 | The generated PNG path is recorded in findings (png_path) | VERIFIED | `viz_tool_node` pushes `{"source":"viz_tool","png_path":str(png_path),...}`; `test_png_path_is_absolute` asserts `Path(vf["png_path"]).is_absolute()` |

**Score:** 4/4 truths verified

### Scope Discipline

| Check | Expected | Status | Evidence |
|-------|----------|--------|----------|
| graph.py unmodified | No changes from Phase 3 | VERIFIED | `git log --follow graph.py` shows single commit `72758c8` from Phase 1 only |
| stats_tool_node not in graph | Standalone, not wired | VERIFIED | grep on graph.py: no match for `stats_tool_node` or `viz_tool_node` |
| viz_tool_node not in graph | Standalone, not wired | VERIFIED | Same grep — absent from graph.py |

---

### Required Artifacts

| Artifact | Expected | Status | Details |
|----------|----------|--------|---------|
| `src/dataagent/agent/stats.py` | Pure functions correlation + detect_anomalies via Polars, min 40 lines | VERIFIED | 92 lines; exports both functions; no LLM calls, no I/O |
| `src/dataagent/agent/viz.py` | render_chart(x,y,name) -> Path, min 40 lines | VERIFIED | 79 lines; exports render_chart + _slugify; kaleido PNG export confirmed |
| `src/dataagent/agent/nodes.py` | Contains stats_tool_node and viz_tool_node | VERIFIED | Both functions present at lines 261 and 340 respectively |
| `src/dataagent/config.py` | ANOMALY_Z_THRESHOLD constant | VERIFIED | Line 13: `ANOMALY_Z_THRESHOLD = 3.0` |
| `tests/test_stats.py` | Deterministic tests, contains def test_ | VERIFIED | 21 tests, all pass; covers correlation, anomaly, insufficient_data, node branches |
| `tests/test_viz.py` | Real-I/O tests, contains def test_ | VERIFIED | 21 tests, all pass; covers PNG write, deterministic filename, auto-mkdir, bar/line heuristic, node render and skip branches |

---

### Key Link Verification

| From | To | Via | Status | Details |
|------|----|-----|--------|---------|
| `nodes.py` | `stats.py` | `from dataagent.agent.stats import correlation, detect_anomalies` | WIRED | Line 18 of nodes.py; both functions called inside stats_tool_node |
| `stats.py` | `config.py` | `ANOMALY_Z_THRESHOLD` import | WIRED | Line 10 of stats.py; used as default argument on line 51 |
| `nodes.py` | `viz.py` | `from dataagent.agent.viz import render_chart` | WIRED | Line 19 of nodes.py; render_chart called inside viz_tool_node line 386 |
| `viz.py` | `config.py` | `REPORTS` output dir | WIRED | Line 12 of viz.py; used at line 52 (mkdir) and line 56 (path construction) |

---

### Data-Flow Trace (Level 4)

| Artifact | Data Variable | Source | Produces Real Data | Status |
|----------|---------------|--------|-------------------|--------|
| `stats_tool_node` | `new_findings` | `correlation()` + `detect_anomalies()` on reconstructed Polars DataFrame from sql_tool findings | Yes — Polars computes actual Pearson coefficient and z-scores from numeric rows | FLOWING |
| `viz_tool_node` | `png_path` | `render_chart()` → `fig.write_image()` via kaleido | Yes — real PNG written to disk, absolute path returned and stored in finding | FLOWING |

---

### Behavioral Spot-Checks

| Behavior | Command | Result | Status |
|----------|---------|--------|--------|
| correlation() imports cleanly | `python -c "from dataagent.agent.stats import correlation, detect_anomalies"` | exit 0 | PASS |
| viz_tool_node imports cleanly | `python -c "from dataagent.agent.nodes import viz_tool_node"` | exit 0 | PASS |
| Full test suite | `python -m pytest tests/ --tb=no -q` | 78 passed, 18 warnings (kaleido deprecation) in 105s | PASS |

---

### Requirements Coverage

| Requirement | Source Plan | Description | Status | Evidence |
|-------------|-------------|-------------|--------|----------|
| TOOL-02 | 03-01-PLAN.md | stats_tool: Pearson correlation + z-score anomaly detection via Polars | SATISFIED | stats.py implements both; stats_tool_node orchestrates them; 14 tests cover the node |
| TOOL-03 | 03-02-PLAN.md | viz_tool: plotly PNG generation via kaleido, png_path in findings | SATISFIED | viz.py implements render_chart; viz_tool_node records png_path; 21 tests cover all branches including real I/O |

---

### Anti-Patterns Found

No blockers or warnings found.

| File | Pattern | Severity | Assessment |
|------|---------|----------|------------|
| `nodes.py` line 369 | `import polars as pl` inside viz_tool_node function body | Info | Minor style issue (import already at top of file via stats), no functional impact |
| `tests/test_viz.py` line 18 warnings | kaleido deprecation for `engine` argument | Info | Third-party library deprecation, not project code; no action needed |

---

### Human Verification Required

None. All four success criteria are verifiable programmatically and confirmed by the passing test suite.

---

## Gaps Summary

No gaps. All four phase success criteria are met:

1. `stats_tool` computes Pearson correlation and pushes it into findings — verified by code inspection and 78/78 tests passing.
2. `stats_tool` detects >=1 anomaly on fixture `[10]*20+[100]` (z~4.47 > 3.0 threshold) — verified by `test_stats_tool_node_anomaly_detected`.
3. `viz_tool` produces a real plotly PNG via kaleido — verified by `TestRenderChartWritesPng` with real I/O.
4. PNG absolute path recorded in findings under `png_path` — verified by `test_png_path_is_absolute`.

Scope discipline confirmed: `graph.py` has a single Phase 1 commit and contains no reference to `stats_tool_node` or `viz_tool_node`. Both tools are standalone and not yet wired into the compiled graph, as required by Phase 3 scope.

---

_Verified: 2026-06-13_
_Verifier: Claude (gsd-verifier)_
