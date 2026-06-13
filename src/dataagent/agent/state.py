"""Schema de state pour l'agent LangGraph.

Conforme D-01 (8 champs exacts), D-02 (db en UntrackedValue),
D-03 (findings reducer add, messages add_messages).
"""

from operator import add
from typing import Annotated, TypedDict

from duckdb import DuckDBPyConnection
from langgraph.channels import UntrackedValue
from langgraph.graph.message import add_messages

from dataagent.config import MAX_ITERATIONS


class AgentState(TypedDict):
    """State de l'agent : 10 champs, conforme PLAN.md §State schema + current_step (Phase 4).

    current_step = index de la sous-question courante dans plan[],
    avancé par le critic à chaque tour de boucle.
    schema = description textuelle du schéma DuckDB, introspecté une fois par run
    et propagé via le state (per D-10 HARD-09 — élimine ~150 queries/run).
    """

    question: str
    plan: list[str]
    findings: Annotated[list[dict], add]
    messages: Annotated[list, add_messages]
    iterations: int
    max_iterations: int
    current_step: int
    db: Annotated[DuckDBPyConnection, UntrackedValue(DuckDBPyConnection)]
    report: str
    schema: str  # per D-10 (HARD-09) — str msgpack-sérialisable, défaut "" (rétrocompat)


def initial_state(question: str, db: DuckDBPyConnection, schema: str = "") -> AgentState:
    """Retourne l'état initial de l'agent pour une question donnée.

    Args:
        question: La question business en langage naturel.
        db: Connexion DuckDB déjà chargée avec les tables Olist.
        schema: Description textuelle du schéma DuckDB (per D-10 HARD-09).
            Défaut "" préserve la rétrocompat à 2 args ; run() calcule schema_description(conn)
            une seule fois et l'injecte ici.

    Returns:
        AgentState avec les valeurs par défaut (iterations=0, max_iterations=MAX_ITERATIONS).
    """
    return AgentState(
        question=question,
        plan=[],
        findings=[],
        messages=[],
        iterations=0,
        max_iterations=MAX_ITERATIONS,
        current_step=0,
        db=db,
        report="",
        schema=schema,
    )
