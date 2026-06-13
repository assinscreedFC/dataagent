"""Tests pour viz.py (render_chart) et viz_tool_node.

Tests réels I/O : vrai PNG généré via kaleido, assertions sur le fichier disque.
Pas de mock LLM, pas de DuckDB nécessaire.
"""

import re
from pathlib import Path

import pytest

import dataagent.agent.viz as viz_module
from dataagent.agent.viz import render_chart


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_sql_finding(
    subquestion: str = "test question",
    rows: list | None = None,
    columns: list | None = None,
) -> dict:
    """Construit un finding sql_tool minimal pour les tests viz_tool_node."""
    if rows is None:
        rows = [("cat_a", 10), ("cat_b", 20), ("cat_c", 5)]
    if columns is None:
        columns = ["label", "value"]
    return {
        "source": "sql_tool",
        "subquestion": subquestion,
        "sql": "SELECT label, value FROM tbl",
        "tables": ["tbl"],
        "rows": rows,
        "columns": columns,
        "attempts": 1,
    }


# ---------------------------------------------------------------------------
# Task 1 — render_chart
# ---------------------------------------------------------------------------


class TestRenderChartWritesPng:
    """PNG généré sur disque, taille > 0, chemin absolu retourné."""

    def test_categorical_x_writes_png(self, tmp_path, monkeypatch):
        monkeypatch.setattr(viz_module, "REPORTS", tmp_path / "reports")
        path = render_chart(["a", "b", "c"], [1, 2, 3], "rev_test")
        assert path.exists(), "Le fichier PNG doit exister sur disque"
        assert path.stat().st_size > 0, "Le fichier PNG ne doit pas être vide"

    def test_returns_absolute_path(self, tmp_path, monkeypatch):
        monkeypatch.setattr(viz_module, "REPORTS", tmp_path / "reports")
        path = render_chart(["x", "y"], [10, 20], "abs_test")
        assert path.is_absolute(), "render_chart doit retourner un chemin absolu"

    def test_numeric_x_writes_png(self, tmp_path, monkeypatch):
        monkeypatch.setattr(viz_module, "REPORTS", tmp_path / "reports")
        path = render_chart([1, 2, 3], [10.0, 20.0, 15.0], "num_series")
        assert path.exists()
        assert path.stat().st_size > 0


class TestRenderChartDeterministicFilename:
    """Même name → même fichier (pas de timestamp/random)."""

    def test_same_name_same_path(self, tmp_path, monkeypatch):
        monkeypatch.setattr(viz_module, "REPORTS", tmp_path / "reports")
        p1 = render_chart(["a", "b"], [1, 2], "same_name")
        p2 = render_chart(["c", "d"], [3, 4], "same_name")
        assert p1 == p2, "Même name doit retourner le même chemin"

    def test_slug_no_special_chars(self, tmp_path, monkeypatch):
        monkeypatch.setattr(viz_module, "REPORTS", tmp_path / "reports")
        path = render_chart(["a", "b"], [1, 2], "Ca Fait Des Espaces & Accents!")
        # Le nom de fichier ne doit contenir que [a-z0-9_].png
        stem = path.stem
        assert re.match(r"^[a-z0-9_]+$", stem), f"Stem non-slugifié : {stem!r}"

    def test_different_names_different_files(self, tmp_path, monkeypatch):
        monkeypatch.setattr(viz_module, "REPORTS", tmp_path / "reports")
        p1 = render_chart(["a"], [1], "chart_one")
        p2 = render_chart(["b"], [2], "chart_two")
        assert p1 != p2, "Des noms différents doivent produire des fichiers différents"


class TestRenderChartAutoCreateReports:
    """REPORTS créé automatiquement s'il est absent."""

    def test_reports_created_if_absent(self, tmp_path, monkeypatch):
        reports_dir = tmp_path / "new_reports_dir"
        assert not reports_dir.exists(), "Le dossier ne doit pas exister avant le test"
        monkeypatch.setattr(viz_module, "REPORTS", reports_dir)
        render_chart(["a", "b"], [1, 2], "mkdir_test")
        assert reports_dir.exists(), "render_chart doit créer REPORTS si absent"


class TestRenderChartKindHeuristic:
    """Bar pour x catégoriel, line pour x numérique ; kind explicite respecté."""

    def test_auto_categorical_no_exception(self, tmp_path, monkeypatch):
        monkeypatch.setattr(viz_module, "REPORTS", tmp_path / "reports")
        # x = strings → bar
        path = render_chart(["cat_a", "cat_b", "cat_c"], [10, 20, 30], "bar_auto")
        assert path.exists()

    def test_auto_numeric_no_exception(self, tmp_path, monkeypatch):
        monkeypatch.setattr(viz_module, "REPORTS", tmp_path / "reports")
        # x = numbers → line
        path = render_chart([1, 2, 3, 4], [5.0, 10.0, 7.5, 12.0], "line_auto")
        assert path.exists()

    def test_explicit_bar_no_exception(self, tmp_path, monkeypatch):
        monkeypatch.setattr(viz_module, "REPORTS", tmp_path / "reports")
        path = render_chart([1, 2], [3, 4], "explicit_bar", kind="bar")
        assert path.exists()

    def test_explicit_line_no_exception(self, tmp_path, monkeypatch):
        monkeypatch.setattr(viz_module, "REPORTS", tmp_path / "reports")
        path = render_chart(["a", "b"], [1, 2], "explicit_line", kind="line")
        assert path.exists()


# ---------------------------------------------------------------------------
# Task 2 — viz_tool_node
# ---------------------------------------------------------------------------


class TestVizToolNodeRendersChart:
    """viz_tool_node rend un PNG et enregistre le png_path dans un finding viz_tool."""

    def test_renders_png_from_sql_finding(self, tmp_path, monkeypatch):
        monkeypatch.setattr(viz_module, "REPORTS", tmp_path / "reports")
        state = {
            "findings": [_make_sql_finding()],
            "question": "q",
            "iterations": 0,
        }
        from dataagent.agent.nodes import viz_tool_node
        result = viz_tool_node(state)
        new_findings = result["findings"]
        viz_findings = [f for f in new_findings if f.get("source") == "viz_tool"]
        assert len(viz_findings) == 1
        vf = viz_findings[0]
        assert "png_path" in vf, "Le finding doit contenir png_path"
        png = Path(vf["png_path"])
        assert png.exists(), f"Le fichier PNG doit exister : {png}"
        assert png.stat().st_size > 0

    def test_png_path_is_absolute(self, tmp_path, monkeypatch):
        monkeypatch.setattr(viz_module, "REPORTS", tmp_path / "reports")
        state = {"findings": [_make_sql_finding()], "question": "q", "iterations": 0}
        from dataagent.agent.nodes import viz_tool_node
        result = viz_tool_node(state)
        vf = next(f for f in result["findings"] if f.get("source") == "viz_tool")
        assert Path(vf["png_path"]).is_absolute()

    def test_finding_has_source_viz_tool(self, tmp_path, monkeypatch):
        monkeypatch.setattr(viz_module, "REPORTS", tmp_path / "reports")
        state = {"findings": [_make_sql_finding()], "question": "q", "iterations": 0}
        from dataagent.agent.nodes import viz_tool_node
        result = viz_tool_node(state)
        sources = [f.get("source") for f in result["findings"]]
        assert "viz_tool" in sources

    def test_finding_contains_chart_key(self, tmp_path, monkeypatch):
        monkeypatch.setattr(viz_module, "REPORTS", tmp_path / "reports")
        state = {"findings": [_make_sql_finding()], "question": "q", "iterations": 0}
        from dataagent.agent.nodes import viz_tool_node
        result = viz_tool_node(state)
        vf = next(f for f in result["findings"] if f.get("source") == "viz_tool")
        assert "chart" in vf

    def test_finding_contains_subquestion(self, tmp_path, monkeypatch):
        monkeypatch.setattr(viz_module, "REPORTS", tmp_path / "reports")
        state = {"findings": [_make_sql_finding(subquestion="ventes par mois")], "question": "q", "iterations": 0}
        from dataagent.agent.nodes import viz_tool_node
        result = viz_tool_node(state)
        vf = next(f for f in result["findings"] if f.get("source") == "viz_tool")
        assert vf.get("subquestion") == "ventes par mois"


class TestVizToolNodeSkipsGracefully:
    """Pas de données visualisables → finding skipped, pas de crash."""

    def test_no_findings_produces_skipped(self, tmp_path, monkeypatch):
        monkeypatch.setattr(viz_module, "REPORTS", tmp_path / "reports")
        state = {"findings": [], "question": "q", "iterations": 0}
        from dataagent.agent.nodes import viz_tool_node
        result = viz_tool_node(state)
        vf = next(f for f in result["findings"] if f.get("source") == "viz_tool")
        assert "skipped" in vf

    def test_error_finding_produces_skipped(self, tmp_path, monkeypatch):
        monkeypatch.setattr(viz_module, "REPORTS", tmp_path / "reports")
        error_finding = {"source": "sql_tool", "subquestion": "q", "error": "SQL error", "attempts": 2}
        state = {"findings": [error_finding], "question": "q", "iterations": 0}
        from dataagent.agent.nodes import viz_tool_node
        result = viz_tool_node(state)
        vf = next(f for f in result["findings"] if f.get("source") == "viz_tool")
        assert "skipped" in vf

    def test_single_row_produces_skipped(self, tmp_path, monkeypatch):
        """Moins de 2 rows → skipped."""
        monkeypatch.setattr(viz_module, "REPORTS", tmp_path / "reports")
        finding = _make_sql_finding(
            rows=[("cat_a", 10)],  # une seule ligne
            columns=["label", "value"],
        )
        state = {"findings": [finding], "question": "q", "iterations": 0}
        from dataagent.agent.nodes import viz_tool_node
        result = viz_tool_node(state)
        vf = next(f for f in result["findings"] if f.get("source") == "viz_tool")
        assert "skipped" in vf

    def test_no_numeric_column_produces_skipped(self, tmp_path, monkeypatch):
        """Que des colonnes textuelles → skipped."""
        monkeypatch.setattr(viz_module, "REPORTS", tmp_path / "reports")
        finding = _make_sql_finding(
            rows=[("cat_a", "foo"), ("cat_b", "bar"), ("cat_c", "baz")],
            columns=["label", "category"],
        )
        state = {"findings": [finding], "question": "q", "iterations": 0}
        from dataagent.agent.nodes import viz_tool_node
        result = viz_tool_node(state)
        vf = next(f for f in result["findings"] if f.get("source") == "viz_tool")
        assert "skipped" in vf

    def test_returns_dict_with_findings_key(self, tmp_path, monkeypatch):
        monkeypatch.setattr(viz_module, "REPORTS", tmp_path / "reports")
        state = {"findings": [], "question": "q", "iterations": 0}
        from dataagent.agent.nodes import viz_tool_node
        result = viz_tool_node(state)
        assert isinstance(result, dict)
        assert "findings" in result
