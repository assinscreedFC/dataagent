"""FastAPI app exposant l'agent DataAgent via HTTP (API-01, D-04).

POST /ask  : {"question": str} → run() → {"report": str, "findings": list}
GET  /health : {"status": "ok"}

Le run() ouvre sa propre connexion DuckDB + charge Olist quand conn=None (D-04).
Les handlers sont synchrones (run() est bloquant) — FastAPI exécute les handlers
synchrones dans un threadpool, ce qui est correct pour un usage Labs mono-utilisateur.

Sécurité (T-06-01, T-06-02) :
- AskRequest valide `question` avec min_length=1 → 422 sur body vide/manquant.
- Aucun secret ni stack trace n'est renvoyé au client.
"""

from fastapi import FastAPI
from pydantic import BaseModel, Field

from dataagent.agent.graph import run

app = FastAPI(title="DataAgent API")


class AskRequest(BaseModel):
    """Corps de la requête POST /ask.

    question doit être une chaîne non-vide (T-06-01 — validation boundary HTTP).
    """

    question: str = Field(..., min_length=1, description="Question business en langage naturel")


@app.get("/health")
def health() -> dict:
    """Health check — confirme que l'API est opérationnelle."""
    return {"status": "ok"}


@app.post("/ask")
def ask(body: AskRequest) -> dict:
    """Exécute l'agent sur la question et retourne le rapport + findings.

    Appelle run() qui ouvre DuckDB et charge Olist si aucune conn n'est injectée (D-04).
    Retourne report (str) et findings (list[dict], incl. png_path pour les viz).

    Sécurité (T-06-02) : seuls report et findings sont retournés — pas de stack trace,
    pas de clé API, pas d'informations internes.
    """
    result = run(body.question)
    return {
        "report": result.get("report", ""),
        "findings": result.get("findings", []),
    }
