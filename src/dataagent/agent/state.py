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
    """State de l'agent : 8 champs, conforme PLAN.md §State schema."""

    question: str
    plan: list[str]
    findings: Annotated[list[dict], add]
    messages: Annotated[list, add_messages]
    iterations: int
    max_iterations: int
    db: Annotated[DuckDBPyConnection, UntrackedValue(DuckDBPyConnection)]
    report: str


def initial_state(question: str, db: DuckDBPyConnection) -> AgentState:
    """Retourne l'état initial de l'agent pour une question donnée.

    Args:
        question: La question business en langage naturel.
        db: Connexion DuckDB déjà chargée avec les tables Olist.

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
        db=db,
        report="",
    )
