"""FastAPI app exposant l'agent DataAgent via HTTP (API-01, D-04).

POST /ask  : {"question": str} → run() → {"report": str, "findings": list}
GET  /health : {"status": "ok"}

Sécurité (T-06-01, T-06-02, HARD-05, HARD-11) :
- AskRequest valide `question` avec min_length=1 et max_length=2000 (D-06).
- Findings filtrés par défaut : sql/rows/columns retirés (D-06).
- Connexion DuckDB ouverte une fois au startup via lifespan, fermée au shutdown (D-12).
- Aucun secret ni stack trace n'est renvoyé au client.
"""

from contextlib import asynccontextmanager

from fastapi import FastAPI, Query, Request
from pydantic import BaseModel, Field

from dataagent.agent.graph import run
from dataagent.config import DATA_RAW
from dataagent.data.loader import connect, load_csvs_to_duckdb

# ---------------------------------------------------------------------------
# Lifespan — connexion DuckDB persistante (D-12, HARD-11)
# ---------------------------------------------------------------------------

# Clés retirées des findings par défaut (D-06, HARD-05)
_FINDINGS_HIDDEN_KEYS = {"sql", "rows", "columns"}


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Ouvre une connexion DuckDB persistante au startup, la ferme au shutdown."""
    app_conn = connect()
    load_csvs_to_duckdb(app_conn, DATA_RAW)
    app.state.conn = app_conn
    yield
    app_conn.close()


app = FastAPI(title="DataAgent API", lifespan=lifespan)


# ---------------------------------------------------------------------------
# Schemas
# ---------------------------------------------------------------------------


class AskRequest(BaseModel):
    """Corps de la requête POST /ask.

    question doit être une chaîne non-vide de 1 à 2000 caractères
    (T-06-01 — validation boundary HTTP, D-06 — borne longueur HARD-05).
    """

    question: str = Field(
        ...,
        min_length=1,
        max_length=2000,
        description="Question business en langage naturel",
    )


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _filter_findings(findings: list[dict]) -> list[dict]:
    """Retire les clés sensibles (sql, rows, columns) de chaque finding (D-06, HARD-05).

    Conserve : source, subquestion, tables, png_path, analysis, error, chart, attempts, etc.
    """
    return [
        {k: v for k, v in finding.items() if k not in _FINDINGS_HIDDEN_KEYS}
        for finding in findings
    ]


# ---------------------------------------------------------------------------
# Routes
# ---------------------------------------------------------------------------


@app.get("/health")
def health() -> dict:
    """Health check — confirme que l'API est opérationnelle."""
    return {"status": "ok"}


@app.post("/ask")
def ask(
    body: AskRequest,
    request: Request,
    debug: bool = Query(default=False, description="Retourne les findings complets (non filtrés)"),
) -> dict:
    """Exécute l'agent sur la question et retourne le rapport + findings.

    Utilise la connexion DuckDB persistante créée au startup (D-12, HARD-11).
    Par défaut, sql/rows/columns sont retirés des findings (D-06, HARD-05).
    Ajouter ?debug=true pour les findings complets.

    Sécurité (T-06-02) : seuls report et findings sont retournés — pas de stack
    trace, pas de clé API, pas d'informations internes.
    """
    conn = getattr(request.app.state, "conn", None)
    result = run(body.question, conn=conn)
    raw_findings = result.get("findings", [])
    return {
        "report": result.get("report", ""),
        "findings": raw_findings if debug else _filter_findings(raw_findings),
    }
