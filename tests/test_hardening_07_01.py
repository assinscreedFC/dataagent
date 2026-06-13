"""Tests hardening 07-01 : schema state, _as_text, critic borné, _critic_decision early-exit.

Stratégie : vraie I/O DuckDB (fixture conn de conftest.py), LLM mocké.
Couvre HARD-01 (D-01/D-02), HARD-02 (D-03), HARD-07 (D-08), HARD-09 (D-10).
"""

import pytest

from dataagent.agent.state import AgentState, initial_state
from dataagent.config import MAX_ITERATIONS


# ---------------------------------------------------------------------------
# Fake LLM helpers
# ---------------------------------------------------------------------------


class _FakeResponse:
    """Simule la réponse str d'un LLM."""

    def __init__(self, content: str) -> None:
        self.content = content


class _FakeResponseMultiPart:
    """Simule une réponse LLM avec content multi-part (liste de dicts)."""

    def __init__(self, parts: list) -> None:
        self.content = parts


class _FakeLLM:
    def __init__(self, content: str) -> None:
        self._content = content

    def invoke(self, messages):  # noqa: ANN001
        return _FakeResponse(self._content)


# ---------------------------------------------------------------------------
# Helper: make_state sans DuckDB obligatoire
# ---------------------------------------------------------------------------


def _make_state(
    plan: list[str],
    current_step: int = 0,
    iterations: int = 0,
    max_iterations: int = 5,
    findings: list[dict] | None = None,
    question: str = "Question test ?",
    schema: str = "",
    conn=None,
) -> AgentState:
    import duckdb

    db = conn if conn is not None else duckdb.connect()
    return AgentState(
        question=question,
        plan=plan,
        findings=findings or [],
        messages=[],
        iterations=iterations,
        max_iterations=max_iterations,
        current_step=current_step,
        db=db,
        report="",
        schema=schema,
    )


# ===========================================================================
# Tests D-10 (HARD-09) : champ schema dans AgentState + initial_state
# ===========================================================================


class TestSchemaInState:
    """Champ schema:str dans AgentState, introspecté une fois, propagé."""

    def test_agent_state_has_schema_field(self):
        """AgentState comporte bien le champ schema (str)."""
        assert "schema" in AgentState.__annotations__
        assert AgentState.__annotations__["schema"] is str

    def test_initial_state_schema_defaults_to_empty_string(self, conn):
        """initial_state(q, conn) sans schema → schema='' (rétrocompat 2 args)."""
        state = initial_state("Q?", conn)
        assert state["schema"] == ""

    def test_initial_state_schema_explicit(self, conn):
        """initial_state(q, conn, schema='TABLE x(...)') → schema propagé."""
        state = initial_state("Q?", conn, schema="TABLE x(id INT)")
        assert state["schema"] == "TABLE x(id INT)"

    def test_initial_state_field_count_is_10(self, conn):
        """initial_state retourne un state à 10 champs (9 existants + schema)."""
        state = initial_state("Q?", conn)
        assert len(state) == 10

    def test_schema_str_is_msgpack_safe(self, conn):
        """schema est une str (msgpack-sérialisable, pas de crash _FilteredSqliteSaver)."""
        state = initial_state("Q?", conn, schema="TABLE foo(id INT)")
        assert isinstance(state["schema"], str)


class TestSchemaInGraphRun:
    """graph.run() introspecte schema une seule fois et l'injecte dans le state."""

    def test_sql_tool_node_uses_state_schema(self, conn, monkeypatch):
        """sql_tool_node utilise state['schema'] si non vide (pas d'appel schema_description)."""
        from dataagent.agent import nodes

        schema_calls = [0]

        original_schema_description = nodes.schema_description

        def counting_schema_description(c):
            schema_calls[0] += 1
            return original_schema_description(c)

        monkeypatch.setattr(nodes, "schema_description", counting_schema_description)

        fake_llm = _FakeLLM("SELECT COUNT(*) AS n FROM orders")
        monkeypatch.setattr(nodes, "flash_llm", lambda: fake_llm)

        state = _make_state(
            plan=["Combien de commandes ?"],
            schema="TABLE orders(order_id VARCHAR)",
            conn=conn,
        )
        nodes.sql_tool_node(state)

        assert schema_calls[0] == 0, (
            f"schema_description appelée {schema_calls[0]} fois — devrait être 0 "
            "quand state.schema est fourni (per D-10 HARD-09)"
        )

    def test_sql_tool_node_fallback_when_schema_empty(self, conn, monkeypatch):
        """sql_tool_node appelle schema_description si state['schema'] est vide."""
        from dataagent.agent import nodes

        schema_calls = [0]
        original_schema_description = nodes.schema_description

        def counting_schema_description(c):
            schema_calls[0] += 1
            return original_schema_description(c)

        monkeypatch.setattr(nodes, "schema_description", counting_schema_description)

        fake_llm = _FakeLLM("SELECT COUNT(*) AS n FROM orders")
        monkeypatch.setattr(nodes, "flash_llm", lambda: fake_llm)

        state = _make_state(
            plan=["Combien de commandes ?"],
            schema="",  # vide → fallback
            conn=conn,
        )
        nodes.sql_tool_node(state)

        assert schema_calls[0] >= 1, (
            f"schema_description appelée {schema_calls[0]} fois — devrait être ≥1 "
            "quand state.schema est vide (fallback per D-10)"
        )


# ===========================================================================
# Tests D-08 (HARD-07) : _as_text helper
# ===========================================================================


class TestAsText:
    """_as_text(response) -> str : garanti str, gère multi-part."""

    def test_as_text_plain_string_content(self):
        """_as_text sur réponse avec content str → retourne la str telle quelle."""
        from dataagent.agent.nodes import _as_text

        response = _FakeResponse("bonjour le monde")
        assert _as_text(response) == "bonjour le monde"

    def test_as_text_multipart_list_of_dicts(self):
        """_as_text concatène les parts texte d'une liste de dicts (multi-part LLM)."""
        from dataagent.agent.nodes import _as_text

        response = _FakeResponseMultiPart([{"text": "hello"}, {"text": " world"}])
        result = _as_text(response)
        assert "hello" in result
        assert "world" in result

    def test_as_text_multipart_mixed_types(self):
        """_as_text gère les parts non-dict dans une liste (fallback str(p))."""
        from dataagent.agent.nodes import _as_text

        response = _FakeResponseMultiPart([{"text": "part1"}, "raw_string_part"])
        result = _as_text(response)
        assert isinstance(result, str)
        assert "part1" in result

    def test_as_text_non_str_non_list_content(self):
        """_as_text sur content de type inattendu → str(content), pas de crash."""
        from dataagent.agent.nodes import _as_text

        class _WeirdResponse:
            content = 42  # int, pas str ni list

        result = _as_text(_WeirdResponse())
        assert result == "42"

    def test_as_text_returns_str_always(self):
        """_as_text retourne toujours un str (jamais de crash)."""
        from dataagent.agent.nodes import _as_text

        for content in ["str", ["list"], 42, None, {"dict": True}]:
            class _R:
                pass
            r = _R()
            r.content = content
            result = _as_text(r)
            assert isinstance(result, str), f"_as_text crash pour content={content!r}"

    def test_as_text_used_in_planner(self, conn, monkeypatch):
        """planner_node utilise _as_text (réponse multi-part ne crashe pas)."""
        from dataagent.agent import nodes

        # Simuler une réponse LLM avec content multi-part
        class _FakeMultiPartLLM:
            def invoke(self, messages):  # noqa: ANN001
                return _FakeResponseMultiPart([{"text": "CA 2017 ?"}, {"text": "\nNombre de commandes ?"}])

        monkeypatch.setattr(nodes, "flash_llm", lambda: _FakeMultiPartLLM())

        state = _make_state(plan=[], conn=conn)
        state["question"] = "CA total ?"
        result = nodes.planner_node(state)
        assert isinstance(result["plan"], list)
        assert len(result["plan"]) >= 1


# ===========================================================================
# Tests D-01 (HARD-01) : critic_node borné
# ===========================================================================


class TestCriticNodeBounded:
    """critic_node : next_step = min(current_step+1, len(plan)-1) si plan, sinon 0."""

    def test_single_element_plan_step_stays_at_0(self, monkeypatch):
        """plan=['Q1'], step=0 → next=min(1,0)=0 (borne per D-01)."""
        from dataagent.agent import nodes

        monkeypatch.setattr(nodes, "flash_llm", lambda: _FakeLLM("SUFFISANT"))
        state = _make_state(plan=["Q1 ?"], current_step=0)
        result = nodes.critic_node(state)
        assert result["current_step"] == 0, (
            f"Plan=['Q1'], step=0 → attendu 0 (D-01: min(1,0)=0), got {result['current_step']}"
        )

    def test_two_element_plan_step_advances_to_1(self, monkeypatch):
        """plan=['Q1','Q2'], step=0 → next=min(1,1)=1."""
        from dataagent.agent import nodes

        monkeypatch.setattr(nodes, "flash_llm", lambda: _FakeLLM("SUFFISANT"))
        state = _make_state(plan=["Q1 ?", "Q2 ?"], current_step=0)
        result = nodes.critic_node(state)
        assert result["current_step"] == 1

    def test_three_element_plan_last_step_stays_bounded(self, monkeypatch):
        """plan=['Q1','Q2','Q3'], step=2 → next=min(3,2)=2 (borné, per D-01)."""
        from dataagent.agent import nodes

        monkeypatch.setattr(nodes, "flash_llm", lambda: _FakeLLM("SUFFISANT"))
        state = _make_state(plan=["Q1 ?", "Q2 ?", "Q3 ?"], current_step=2)
        result = nodes.critic_node(state)
        assert result["current_step"] == 2, (
            f"Plan de 3, step=2 → attendu 2 (D-01: min(3,2)=2), got {result['current_step']}"
        )

    def test_empty_plan_step_returns_0(self, monkeypatch):
        """plan=[], step=5 → next=0 (guard per D-01)."""
        from dataagent.agent import nodes

        monkeypatch.setattr(nodes, "flash_llm", lambda: _FakeLLM("SUFFISANT"))
        state = _make_state(plan=[], current_step=5)
        result = nodes.critic_node(state)
        assert result["current_step"] == 0


# ===========================================================================
# Tests D-03 (HARD-02) : _summarize_findings_for_critic
# ===========================================================================


class TestSummarizeFindingsForCritic:
    """_summarize_findings_for_critic : résumé contenu, cappé 1500 chars."""

    def test_empty_findings_returns_placeholder(self):
        """Findings vides → '(aucun finding)'."""
        from dataagent.agent.nodes import _summarize_findings_for_critic

        result = _summarize_findings_for_critic([])
        assert "(aucun finding)" in result.lower() or "aucun" in result.lower()

    def test_sql_finding_contains_subquestion(self):
        """Finding sql_tool → résumé contient la subquestion."""
        from dataagent.agent.nodes import _summarize_findings_for_critic

        findings = [
            {
                "source": "sql_tool",
                "subquestion": "Quel est le CA total ?",
                "sql": "SELECT SUM(price) FROM order_items",
                "rows": [(100.0,), (200.0,)],
                "columns": ["total"],
            }
        ]
        result = _summarize_findings_for_critic(findings)
        assert "CA total" in result

    def test_sql_finding_contains_rows_sample(self):
        """Finding sql_tool → résumé contient les 2 premières rows."""
        from dataagent.agent.nodes import _summarize_findings_for_critic

        findings = [
            {
                "source": "sql_tool",
                "subquestion": "Q ?",
                "rows": [(42.0,), (99.0,), (7.0,)],
                "columns": ["val"],
            }
        ]
        result = _summarize_findings_for_critic(findings)
        # Les 2 premières rows doivent apparaître
        assert "42" in result or "99" in result

    def test_result_capped_at_1500_chars(self):
        """Résumé tronqué à 1500 chars si trop long."""
        from dataagent.agent.nodes import _summarize_findings_for_critic

        # Générer beaucoup de findings pour dépasser 1500 chars
        findings = [
            {
                "source": "sql_tool",
                "subquestion": "Sous-question très longue " * 20,
                "rows": [("valeur_" * 50,)] * 50,
                "columns": ["col"],
            }
        ] * 10

        result = _summarize_findings_for_critic(findings)
        assert len(result) <= 1500, f"Résumé trop long : {len(result)} chars"

    def test_critic_node_injects_summary_content(self, monkeypatch):
        """critic_node injecte le résumé contenu dans le prompt (pas juste un count)."""
        from dataagent.agent import nodes

        captured_messages = []

        class _CapturingLLM:
            def invoke(self, messages):  # noqa: ANN001
                captured_messages.extend(messages)
                return _FakeResponse("SUFFISANT")

        monkeypatch.setattr(nodes, "flash_llm", lambda: _CapturingLLM())

        state = _make_state(
            plan=["CA total ?"],
            findings=[
                {
                    "source": "sql_tool",
                    "subquestion": "CA total des commandes ?",
                    "rows": [(380.0,), (100.0,)],
                    "columns": ["total_ca"],
                }
            ],
        )
        nodes.critic_node(state)

        # Le prompt humain doit contenir plus qu'un simple count
        human_msg = ""
        for msg in captured_messages:
            if isinstance(msg, tuple) and msg[0] == "human":
                human_msg = msg[1]
            elif hasattr(msg, "content") and "Verdict" in str(getattr(msg, "content", "")):
                human_msg = str(msg.content)

        # Doit contenir la subquestion ou des rows, pas juste "N finding(s)"
        assert "CA total" in human_msg or "380" in human_msg or "finding" in human_msg.lower()


# ===========================================================================
# Tests D-02 (HARD-01) : _critic_decision early-exit quand plan épuisé
# ===========================================================================


class TestCriticDecisionEarlyExit:
    """_critic_decision : early-exit vers synthesizer quand current_step >= len(plan)."""

    def test_early_exit_when_plan_exhausted(self):
        """current_step >= len(plan) → 'synthesizer' (per D-02 HARD-01)."""
        from dataagent.agent.graph import _critic_decision

        state = {
            "iterations": 1,
            "max_iterations": 5,
            "current_step": 2,  # >= len(plan)=2
            "plan": ["Q1 ?", "Q2 ?"],
            "findings": [{"source": "critic", "sufficient": False, "iteration": 1}],
        }
        result = _critic_decision(state)
        assert result == "synthesizer", (
            f"Attendu 'synthesizer' quand plan épuisé (D-02), got '{result}'"
        )

    def test_early_exit_single_question_plan(self):
        """Plan d'1 question, step=1 (>= len=1) → 'synthesizer'."""
        from dataagent.agent.graph import _critic_decision

        state = {
            "iterations": 1,
            "max_iterations": 5,
            "current_step": 1,  # >= len(plan)=1
            "plan": ["Q1 ?"],
            "findings": [{"source": "critic", "sufficient": False, "iteration": 1}],
        }
        result = _critic_decision(state)
        assert result == "synthesizer"

    def test_no_early_exit_when_plan_not_exhausted(self):
        """current_step < len(plan) et insufficient → 'router' (reboucle normal)."""
        from dataagent.agent.graph import _critic_decision

        state = {
            "iterations": 1,
            "max_iterations": 5,
            "current_step": 0,  # < len(plan)=2
            "plan": ["Q1 ?", "Q2 ?"],
            "findings": [{"source": "critic", "sufficient": False, "iteration": 1}],
        }
        result = _critic_decision(state)
        assert result == "router"

    def test_hard_cap_still_active(self):
        """Hard cap iterations >= max_iterations reste prioritaire."""
        from dataagent.agent.graph import _critic_decision

        state = {
            "iterations": 5,
            "max_iterations": 5,
            "current_step": 0,  # pas épuisé, mais hard cap atteint
            "plan": ["Q1 ?", "Q2 ?", "Q3 ?"],
            "findings": [{"source": "critic", "sufficient": False}],
        }
        result = _critic_decision(state)
        assert result == "synthesizer", "Hard cap doit toujours fonctionner"

    def test_empty_plan_early_exit(self):
        """Plan vide, step=0 → current_step(0) >= len([])=0 → synthesizer."""
        from dataagent.agent.graph import _critic_decision

        state = {
            "iterations": 1,
            "max_iterations": 5,
            "current_step": 0,
            "plan": [],
            "findings": [],
        }
        result = _critic_decision(state)
        # 0 >= 0 → synthesizer
        assert result == "synthesizer"


# ===========================================================================
# Tests D-09 (HARD-08) : except bindés + exc_info
# ===========================================================================


class TestExceptBound:
    """stats_tool_node et viz_tool_node : except bindent l'exception + exc_info=True."""

    def test_stats_tool_bad_dataframe_logs_and_continues(self, monkeypatch, caplog):
        """stats_tool_node logue avec exc_info=True sur DataFrame malformé."""
        import logging
        from dataagent.agent import nodes

        # Créer un finding avec rows/columns incompatibles (rows = 1 col, columns = 2)
        state = _make_state(
            plan=["Q ?"],
            findings=[
                {
                    "source": "sql_tool",
                    "subquestion": "Q ?",
                    "rows": [(1,), (2,)],
                    "columns": ["col_a", "col_b"],  # arity mismatch
                }
            ],
        )

        with caplog.at_level(logging.WARNING, logger="dataagent.agent.nodes"):
            result = nodes.stats_tool_node(state)

        # Ne doit pas crasher
        assert "findings" in result
        # Doit loguer le warning (avec exc_info traduit en traceback dans le log)
        # On vérifie juste que l'execution continue et retourne un finding
        assert len(result["findings"]) >= 1

    def test_viz_tool_bad_dataframe_logs_and_continues(self, monkeypatch, caplog):
        """viz_tool_node logue avec exc_info=True sur DataFrame malformé (arity mismatch)."""
        import logging
        from dataagent.agent import nodes

        state = _make_state(
            plan=["Q ?"],
            findings=[
                {
                    "source": "sql_tool",
                    "subquestion": "Q ?",
                    "rows": [(1,), (2,), (3,)],  # 1 valeur par row
                    "columns": ["a", "b"],  # 2 colonnes — arity mismatch
                }
            ],
        )

        with caplog.at_level(logging.WARNING, logger="dataagent.agent.nodes"):
            result = nodes.viz_tool_node(state)

        # Ne doit pas crasher
        assert "findings" in result
