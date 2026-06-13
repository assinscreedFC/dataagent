"""Tests pour src/dataagent/render.py — markdown → HTML standalone SolidScale.

Tous les tests utilisent la vraie I/O (fichier écrit sur disque), pas de mock.
Aucun appel LLM — quota-free (D-07).
"""

from pathlib import Path

import pytest

from dataagent.render import render_html, render_report_to_file


# ---------------------------------------------------------------------------
# render_html — unit tests
# ---------------------------------------------------------------------------


def test_render_html_returns_doctype():
    """render_html retourne un doc HTML commençant par <!DOCTYPE html>."""
    html = render_html("# Titre\n\nTexte **gras**.")
    assert html.startswith("<!DOCTYPE html>")


def test_render_html_contains_report_text():
    """Le contenu du rapport markdown apparaît dans le HTML rendu."""
    html = render_html("# Mon Titre\n\nCeci est un paragraphe.")
    assert "Mon Titre" in html
    assert "paragraphe" in html


def test_render_html_contains_style_block():
    """Le HTML contient un bloc <style> pour le rebrand SolidScale."""
    html = render_html("# Test")
    assert "<style>" in html


def test_render_html_embeds_png_path_from_findings():
    """Un png_path dans les findings (non présent dans le markdown) génère un <img>."""
    findings = [{"source": "viz_tool", "png_path": "reports/test_chart.png"}]
    html = render_html("# Rapport sans image", findings=findings)
    assert '<img' in html
    assert "reports/test_chart.png" in html


def test_render_html_no_duplicate_img_if_already_in_markdown():
    """Si le png_path est déjà dans le markdown, il n'est pas dupliqué en <img> extra."""
    png = "reports/existing.png"
    md = f"# Rapport\n\n![graphe]({png})\n\nTexte."
    findings = [{"source": "viz_tool", "png_path": png}]
    html = render_html(md, findings=findings)
    # L'image est présente (via le markdown converti) mais pas injectée une 2e fois
    count = html.count(png)
    assert count >= 1  # au moins une occurrence (le markdown converti)
    # Vérifier qu'il n'y a pas une balise <img extra injectée (la 2e occurrence)
    # Le markdown converti génère déjà un <img src="reports/existing.png"> donc count == 1
    assert count == 1


def test_render_html_empty_report_does_not_crash():
    """Un rapport vide ou whitespace ne crashe pas et retourne du HTML valide."""
    html = render_html("")
    assert html.startswith("<!DOCTYPE html>")

    html_ws = render_html("   ")
    assert html_ws.startswith("<!DOCTYPE html>")


def test_render_html_no_findings_no_img():
    """Pas de findings → pas de <img> injecté (sauf si le markdown en contient)."""
    html = render_html("# Rapport simple\n\nAucune image.")
    # Aucun <img> injecté depuis les findings
    assert "png_path" not in html


def test_render_html_findings_without_png_path_ignored():
    """Un finding sans png_path (ex: sql_tool) ne génère pas d'img."""
    findings = [{"source": "sql_tool", "rows": [], "columns": []}]
    html = render_html("# Test", findings=findings)
    # Pas d'injection <img> parasite
    assert "sql_tool" not in html  # les findings ne sont pas dumpés dans le HTML


# ---------------------------------------------------------------------------
# render_report_to_file — integration tests (vraie I/O)
# ---------------------------------------------------------------------------


def test_render_report_to_file_writes_file(tmp_path, monkeypatch):
    """render_report_to_file écrit un fichier .html dans REPORTS/<name>.html."""
    import dataagent.render as render_mod

    monkeypatch.setattr(render_mod, "REPORTS", tmp_path)

    out_path = render_report_to_file("# Titre\n\nContenu.", name="test_out")

    assert out_path.exists()
    assert out_path.suffix == ".html"
    assert out_path.name == "test_out.html"


def test_render_report_to_file_content_matches_render_html(tmp_path, monkeypatch):
    """Le fichier écrit contient exactement le résultat de render_html."""
    import dataagent.render as render_mod

    monkeypatch.setattr(render_mod, "REPORTS", tmp_path)

    md = "# Rapport\n\nDonnées business."
    findings = [{"source": "viz_tool", "png_path": "reports/chart.png"}]

    out_path = render_report_to_file(md, findings=findings, name="content_check")
    written = out_path.read_text(encoding="utf-8")
    expected = render_html(md, findings=findings)

    assert written == expected


def test_render_report_to_file_creates_reports_dir(tmp_path, monkeypatch):
    """render_report_to_file crée le dossier REPORTS s'il n'existe pas."""
    import dataagent.render as render_mod

    nested = tmp_path / "new_dir" / "reports"
    monkeypatch.setattr(render_mod, "REPORTS", nested)

    out_path = render_report_to_file("# Test", name="mkdir_test")
    assert out_path.exists()


def test_render_report_to_file_returns_path(tmp_path, monkeypatch):
    """render_report_to_file retourne un objet Path."""
    import dataagent.render as render_mod

    monkeypatch.setattr(render_mod, "REPORTS", tmp_path)

    result = render_report_to_file("# Test", name="path_type")
    assert isinstance(result, Path)
