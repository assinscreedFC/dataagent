"""Module de visualisation : render plotly figure -> PNG déterministe via kaleido.

Fournit render_chart(), fonction pure sans appel LLM ni aléatoire.
Le chemin PNG est déterministe (basé sur le nom slugifié) pour reproductibilité des tests.
"""

import re
from pathlib import Path

import plotly.graph_objects as go

from dataagent.config import REPORTS


def _slugify(name: str) -> str:
    """Convertit `name` en slug sûr pour un nom de fichier.

    Règles : minuscules, caractères non-alphanumériques remplacés par "_",
    tirets multiples condensés, strip des underscores en bord.
    Garantit l'absence de path traversal (aucun "/" ou ".." ne peut survivre).
    """
    slug = name.lower()
    slug = re.sub(r"[^a-z0-9]+", "_", slug)
    slug = slug.strip("_")
    return slug or "chart"


def render_chart(
    x: list,
    y: list,
    name: str,
    kind: str = "auto",
) -> Path:
    """Génère un graphique plotly et l'exporte en PNG via kaleido.

    Args:
        x: Valeurs de l'axe X (catégorielles → bar, numériques → line si kind="auto").
        y: Valeurs de l'axe Y (numériques).
        name: Nom logique du graphique. Utilisé pour construire le nom de fichier
              déterministe (slugifié). Même name → même fichier, pas de timestamp.
        kind: "auto" (heuristique) | "bar" | "line".
              "auto" choisit bar si x est catégoriel (str), line sinon.

    Returns:
        Chemin absolu du fichier PNG généré dans config.REPORTS.

    Side effects:
        - Crée config.REPORTS si absent (parents=True, exist_ok=True).
        - Écrase le fichier existant si même nom (idempotent).
    """
    # D-07 : créer REPORTS si absent
    REPORTS.mkdir(parents=True, exist_ok=True)

    # D-06 : nom de fichier déterministe, sans timestamp ni random (T-03-04 : slugify)
    slug = _slugify(name)
    path = REPORTS / f"{slug}.png"

    # Heuristique kind (D-06, Claude's discretion)
    if kind == "auto":
        # x est catégoriel si le premier élément non-None est une str
        first = next((v for v in x if v is not None), None)
        resolved_kind = "bar" if isinstance(first, str) else "line"
    else:
        resolved_kind = kind

    # Construction du tracé plotly
    if resolved_kind == "bar":
        trace = go.Bar(x=x, y=y)
    else:
        trace = go.Scatter(x=x, y=y, mode="lines")

    fig = go.Figure(data=[trace])
    fig.update_layout(title=name)

    # Export PNG via kaleido
    fig.write_image(str(path))

    return path.resolve()
