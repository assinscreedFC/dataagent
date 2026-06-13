"""Tests pour AgentState et initial_state().

Vraie I/O DuckDB via fixture conn (conftest.py). Aucun mock I/O.
"""

import operator
import typing

import pytest

from dataagent.agent.state import AgentState, initial_state
from dataagent.config import MAX_ITERATIONS


_EXPECTED_FIELDS = {
    "question",
    "plan",
    "findings",
    "messages",
    "iterations",
    "max_iterations",
    "current_step",
    "db",
    "report",
    "schema",  # per D-10 (HARD-09) — introspecté une fois par run
}


def test_agent_state_has_exactly_10_fields() -> None:
    """AgentState porte exactement les 10 champs (9 existants + schema per D-10 HARD-09)."""
    assert set(AgentState.__annotations__) == _EXPECTED_FIELDS


def test_initial_state_has_schema_field() -> None:
    """initial_state() inclut le champ schema (str, défaut '')."""
    import duckdb
    conn = duckdb.connect()
    state = initial_state("Q?", conn)
    assert "schema" in state
    assert state["schema"] == ""
    conn.close()


def test_db_field_is_untracked() -> None:
    """Le champ db est annoté UntrackedValue (jamais checkpointé — D-02)."""
    from langgraph.channels import UntrackedValue

    hints = typing.get_type_hints(AgentState, include_extras=True)
    db_annotation = hints["db"]
    args = typing.get_args(db_annotation)
    # Annotated[DuckDBPyConnection, UntrackedValue()] -> args[1] est une instance UntrackedValue
    metadata = args[1:]
    assert any(isinstance(m, UntrackedValue) for m in metadata), (
        f"UntrackedValue introuvable dans les metadata de 'db': {metadata}"
    )


def test_findings_uses_add_reducer() -> None:
    """Le champ findings est annoté avec le reducer operator.add (D-03)."""
    hints = typing.get_type_hints(AgentState, include_extras=True)
    findings_annotation = hints["findings"]
    args = typing.get_args(findings_annotation)
    metadata = args[1:]
    assert operator.add in metadata, (
        f"operator.add introuvable dans les metadata de 'findings': {metadata}"
    )


def test_initial_state_defaults(conn) -> None:
    """initial_state() retourne les valeurs par défaut correctes (D-10)."""
    state = initial_state("Q?", conn)

    assert state["question"] == "Q?"
    assert state["db"] is conn
    assert state["plan"] == []
    assert state["findings"] == []
    assert state["messages"] == []
    assert state["iterations"] == 0
    assert state["max_iterations"] == MAX_ITERATIONS
    assert state["max_iterations"] == 5
    assert state["current_step"] == 0
    assert state["report"] == ""
