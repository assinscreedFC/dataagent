"""Renderer markdown → HTML standalone (SolidScale rebrand, D-06).

Fournit deux fonctions pures sans LLM ni réseau :
- render_html : markdown + findings → str HTML complet
- render_report_to_file : écrit le HTML dans reports/<name>.html
"""

import html
from pathlib import Path

import markdown

from dataagent.config import REPORTS

# ---------------------------------------------------------------------------
# CSS SolidScale — palette sobre, typographie lisible, standalone
# ---------------------------------------------------------------------------

_SOLIDSCALE_CSS = """
:root {
    --bg:        #f7f7f5;
    --surface:   #ffffff;
    --border:    #e2e2de;
    --text:      #1a1a18;
    --muted:     #6b6b65;
    --accent:    #2a6496;
    --accent-lt: #d6e8f5;
    --code-bg:   #f0f0ec;
}

*, *::before, *::after { box-sizing: border-box; margin: 0; padding: 0; }

body {
    background: var(--bg);
    color: var(--text);
    font-family: "Georgia", "Times New Roman", serif;
    font-size: 17px;
    line-height: 1.75;
    padding: 2rem 1rem;
}

.container {
    max-width: 780px;
    margin: 0 auto;
    background: var(--surface);
    border: 1px solid var(--border);
    border-radius: 6px;
    padding: 2.5rem 3rem;
}

h1, h2, h3, h4 {
    font-family: "Helvetica Neue", "Arial", sans-serif;
    font-weight: 600;
    color: var(--text);
    margin-top: 2rem;
    margin-bottom: 0.6rem;
    line-height: 1.3;
}

h1 { font-size: 1.9rem; border-bottom: 2px solid var(--accent); padding-bottom: 0.4rem; }
h2 { font-size: 1.4rem; border-bottom: 1px solid var(--border); padding-bottom: 0.3rem; }
h3 { font-size: 1.15rem; }

p { margin-bottom: 1rem; }

a { color: var(--accent); text-decoration: none; }
a:hover { text-decoration: underline; }

code {
    background: var(--code-bg);
    border: 1px solid var(--border);
    border-radius: 3px;
    padding: 0.1em 0.35em;
    font-family: "Menlo", "Consolas", monospace;
    font-size: 0.88em;
}

pre {
    background: var(--code-bg);
    border: 1px solid var(--border);
    border-radius: 4px;
    padding: 1rem 1.2rem;
    overflow-x: auto;
    margin-bottom: 1.2rem;
}

pre code { background: none; border: none; padding: 0; font-size: 0.85em; }

blockquote {
    border-left: 3px solid var(--accent);
    background: var(--accent-lt);
    padding: 0.6rem 1rem;
    margin: 1rem 0;
    color: var(--muted);
    border-radius: 0 4px 4px 0;
}

table {
    border-collapse: collapse;
    width: 100%;
    margin-bottom: 1.2rem;
    font-size: 0.93em;
}

th {
    background: var(--accent);
    color: #fff;
    padding: 0.5rem 0.8rem;
    text-align: left;
    font-family: "Helvetica Neue", sans-serif;
    font-weight: 600;
    font-size: 0.85em;
    text-transform: uppercase;
    letter-spacing: 0.04em;
}

td {
    padding: 0.45rem 0.8rem;
    border-bottom: 1px solid var(--border);
}

tr:nth-child(even) td { background: var(--bg); }

ul, ol { padding-left: 1.5rem; margin-bottom: 1rem; }
li { margin-bottom: 0.25rem; }

img {
    max-width: 100%;
    height: auto;
    display: block;
    margin: 1.2rem auto;
    border: 1px solid var(--border);
    border-radius: 4px;
}

.viz-section {
    margin: 1.5rem 0;
    text-align: center;
}

hr {
    border: none;
    border-top: 1px solid var(--border);
    margin: 2rem 0;
}
"""

_HTML_TEMPLATE = """\
<!DOCTYPE html>
<html lang="fr">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>DataAgent — SolidScale Report</title>
  <style>
{css}
  </style>
</head>
<body>
  <div class="container">
{body}
  </div>
</body>
</html>"""


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


def render_html(
    report_md: str,
    findings: list[dict] | None = None,
) -> str:
    """Convertit un rapport markdown en HTML standalone stylé (SolidScale).

    Args:
        report_md: Rapport en markdown (peut être vide).
        findings:  Liste de findings agent ; les entrées avec "png_path"
                   dont l'image n'est pas déjà dans le markdown sont
                   injectées comme balises <img> dans le corps HTML.

    Returns:
        Document HTML complet (str) commençant par "<!DOCTYPE html>".
    """
    safe_md = report_md or ""

    # Convertir le markdown en HTML — extension "extra" pour tables/listes imbriquées
    body: str = markdown.markdown(safe_md, extensions=["extra"])

    # Injecter les png_path des findings non déjà présents dans le markdown
    if findings:
        for finding in findings:
            png_path = finding.get("png_path")
            if png_path and png_path not in safe_md:
                safe_src = html.escape(png_path, quote=True)
                safe_alt = html.escape("graphe", quote=True)
                body += (
                    f'\n<div class="viz-section">'
                    f'<img src="{safe_src}" alt="{safe_alt}">'
                    f"</div>"
                )

    # Indenter le body pour l'intégrer dans le template
    indented_body = "\n".join("    " + line for line in body.splitlines())

    return _HTML_TEMPLATE.format(css=_SOLIDSCALE_CSS, body=indented_body)


def render_report_to_file(
    report_md: str,
    findings: list[dict] | None = None,
    name: str = "report",
) -> Path:
    """Écrit le rapport HTML dans REPORTS/<name>.html et retourne le chemin.

    Args:
        report_md: Rapport en markdown.
        findings:  Findings agent (png_path embarqués si nouveaux).
        name:      Nom de fichier sans extension (défaut: "report").

    Returns:
        Path du fichier HTML écrit.
    """
    REPORTS.mkdir(parents=True, exist_ok=True)
    out_path = REPORTS / f"{name}.html"
    html_content = render_html(report_md, findings=findings)
    out_path.write_text(html_content, encoding="utf-8")
    return out_path
