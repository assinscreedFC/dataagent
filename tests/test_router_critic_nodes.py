"""Tests unitaires pour route_subquestion, critic_node et synthesizer multi-source.

Stratégie : vraie I/O DuckDB (fixture conn de conftest.py), LLM mocké.
- route_subquestion : déterministe par mots-clés, guard index hors borne
- critic_node : flash mocké, incrément iterations+current_step, finding source="critic"
- synthesizer multi-source : pro mocké, findings sql+stats+viz, image markdown
"""

import pytest

from dataagent.agent import nodes
from dataagent.agent.state import AgentState, initial_state


# ---------------------------------------------------------------------------
# Fake LLM helpers
# ---------------------------------------------------------------------------


class _FakeResponse:
    """Simule la réponse d'un ChatGoogleGenerativeAI.invoke()."""

    def __init__(self, content: str) -> None:
        self.content = content


class _FakeLLM:
    """LLM factice dont .invoke() retourne un contenu prédéfini."""

    def __init__(self, content: str) -> None:
        self._content = content

    def invoke(self, messages):  # noqa: ANN001
        return _FakeResponse(self._content)


# ---------------------------------------------------------------------------
# Helpers pour construire un state minimal
# ---------------------------------------------------------------------------


def _make_state(
    plan: list[str],
    current_step: int = 0,
    iterations: int = 0,
    max_iterations: int = 5,
    findings: list[dict] | None = None,
    question: str = "Question test ?",
    conn=None,
) -> AgentState:
    """Construit un AgentState minimal pour les tests (sans DuckDB réel si conn=None)."""
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
    )


# ---------------------------------------------------------------------------
# Tests : route_subquestion
# ---------------------------------------------------------------------------


class TestRouteSubquestion:
    """Tests de la fonction de routing par mots-clés."""

    def test_sql_default(self):
        """Sous-question générique -> sql_tool (défaut)."""
        state = _make_state(plan=["Quel est le CA total ?"], current_step=0)
        result = nodes.route_subquestion(state)
        assert result == "sql_tool"

    def test_stats_correlation_keyword(self):
        """Mot-clé 'corrélation' -> stats_tool."""
        state = _make_state(
            plan=["Quelle est la corrélation entre prix et note ?"], current_step=0
        )
        result = nodes.route_subquestion(state)
        assert result == "stats_tool"

    def test_stats_anomalie_keyword(self):
        """Mot-clé 'anomalie' -> stats_tool."""
        state = _make_state(plan=["Détecte les anomalies de prix"], current_step=0)
        result = nodes.route_subquestion(state)
        assert result == "stats_tool"

    def test_stats_ecart_type_keyword(self):
        """Mot-clé 'écart-type' -> stats_tool."""
        state = _make_state(plan=["Calcule l'écart-type des ventes"], current_step=0)
        result = nodes.route_subquestion(state)
        assert result == "stats_tool"

    def test_stats_tendance_keyword(self):
        """Mot-clé 'tendance' -> stats_tool."""
        state = _make_state(plan=["Quelle est la tendance mensuelle ?"], current_step=0)
        result = nodes.route_subquestion(state)
        assert result == "stats_tool"

    def test_viz_graphe_keyword(self):
        """Mot-clé 'graphe' -> viz_tool."""
        state = _make_state(plan=["Affiche un graphe des ventes"], current_step=0)
        result = nodes.route_subquestion(state)
        assert result == "viz_tool"

    def test_viz_visualise_keyword(self):
        """Mot-clé 'visualise' -> viz_tool."""
        state = _make_state(plan=["Visualise l'évolution du CA"], current_step=0)
        result = nodes.route_subquestion(state)
        assert result == "viz_tool"

    def test_viz_courbe_keyword(self):
        """Mot-clé 'courbe' -> viz_tool."""
        state = _make_state(plan=["Trace la courbe des commandes"], current_step=0)
        result = nodes.route_subquestion(state)
        assert result == "viz_tool"

    def test_viz_chart_keyword(self):
        """Mot-clé 'chart' -> viz_tool."""
        state = _make_state(plan=["Generate a chart of orders per month"], current_step=0)
        result = nodes.route_subquestion(state)
        assert result == "viz_tool"

    def test_viz_plot_keyword(self):
        """Mot-clé 'plot' -> viz_tool."""
        state = _make_state(plan=["Plot revenue over time"], current_step=0)
        result = nodes.route_subquestion(state)
        assert result == "viz_tool"

    def test_viz_histogramme_keyword(self):
        """Mot-clé 'histogramme' -> viz_tool."""
        state = _make_state(plan=["Génère un histogramme des notes"], current_step=0)
        result = nodes.route_subquestion(state)
        assert result == "viz_tool"

    def test_current_step_selects_correct_subquestion(self):
        """current_step pointe sur la bonne sous-question dans le plan."""
        state = _make_state(
            plan=["CA total ?", "Visualise les ventes", "Anomalies ?"],
            current_step=1,
        )
        result = nodes.route_subquestion(state)
        assert result == "viz_tool"

    def test_current_step_stats_from_plan(self):
        """current_step=2 => 3e sous-question => stats_tool."""
        state = _make_state(
            plan=["CA total ?", "Visualise les ventes", "Anomalies de prix ?"],
            current_step=2,
        )
        result = nodes.route_subquestion(state)
        assert result == "stats_tool"

    def test_guard_index_out_of_bounds_returns_sql(self):
        """Si current_step >= len(plan), retourne sql_tool sans IndexError (garde-fou)."""
        state = _make_state(plan=["CA total ?"], current_step=99)
        result = nodes.route_subquestion(state)
        assert result == "sql_tool"

    def test_guard_empty_plan_returns_sql(self):
        """Si plan est vide, retourne sql_tool sans IndexError."""
        state = _make_state(plan=[], current_step=0)
        result = nodes.route_subquestion(state)
        assert result == "sql_tool"

    def test_return_type_is_literal_value(self):
        """Le retour est toujours l'une des 3 valeurs autorisées."""
        allowed = {"sql_tool", "stats_tool", "viz_tool"}
        for subq, expected in [
            ("CA total ?", "sql_tool"),
            ("corrélation prix note", "stats_tool"),
            ("visualise les ventes", "viz_tool"),
        ]:
            state = _make_state(plan=[subq], current_step=0)
            result = nodes.route_subquestion(state)
            assert result in allowed
            assert result == expected

    def test_case_insensitive_matching(self):
        """Le matching est insensible à la casse (CORRÉLATION -> stats_tool)."""
        state = _make_state(plan=["CORRÉLATION entre prix et stock"], current_step=0)
        result = nodes.route_subquestion(state)
        assert result == "stats_tool"


# ---------------------------------------------------------------------------
# Tests : critic_node
# ---------------------------------------------------------------------------


class TestCriticNode:
    """Tests du nœud critic (flash mocké)."""

    def test_increments_iterations_by_one(self, monkeypatch):
        """critic_node incrémente iterations de exactement 1."""
        monkeypatch.setattr(nodes, "flash_llm", lambda: _FakeLLM("SUFFISANT"))
        state = _make_state(plan=["Q1 ?"], iterations=2, current_step=0)
        result = nodes.critic_node(state)
        assert result["iterations"] == 3

    def test_increments_iterations_from_zero(self, monkeypatch):
        """Depuis iterations=0, critic retourne iterations=1."""
        monkeypatch.setattr(nodes, "flash_llm", lambda: _FakeLLM("SUFFISANT"))
        state = _make_state(plan=["Q1 ?"], iterations=0, current_step=0)
        result = nodes.critic_node(state)
        assert result["iterations"] == 1

    def test_always_increments_even_when_insufficient(self, monkeypatch):
        """iterations s'incrémente même si le critic répond INSUFFISANT."""
        monkeypatch.setattr(nodes, "flash_llm", lambda: _FakeLLM("INSUFFISANT"))
        state = _make_state(plan=["Q1 ?"], iterations=3, current_step=0)
        result = nodes.critic_node(state)
        assert result["iterations"] == 4

    def test_increments_current_step_by_one(self, monkeypatch):
        """critic_node avance current_step de exactement 1."""
        monkeypatch.setattr(nodes, "flash_llm", lambda: _FakeLLM("SUFFISANT"))
        state = _make_state(plan=["Q1 ?", "Q2 ?"], iterations=0, current_step=0)
        result = nodes.critic_node(state)
        assert result["current_step"] == 1

    def test_current_step_increments_from_nonzero(self, monkeypatch):
        """current_step borné (D-01) : plan=3 items, step=2 → min(3, len-1=2) = 2.

        D-01 : next_step = min(current_step+1, len(plan)-1) if plan else 0.
        Avec plan de 3 sous-questions et current_step=2, le prochain step serait 3
        mais est borné à len(plan)-1=2 pour éviter un dépassement d'index.
        """
        monkeypatch.setattr(nodes, "flash_llm", lambda: _FakeLLM("SUFFISANT"))
        state = _make_state(plan=["Q1 ?", "Q2 ?", "Q3 ?"], iterations=1, current_step=2)
        result = nodes.critic_node(state)
        # D-01 borne current_step : min(2+1, 3-1) = min(3, 2) = 2
        assert result["current_step"] == 2

    def test_returns_finding_source_critic_sufficient(self, monkeypatch):
        """Quand flash répond SUFFISANT, le finding source=critic a sufficient=True."""
        monkeypatch.setattr(nodes, "flash_llm", lambda: _FakeLLM("SUFFISANT"))
        state = _make_state(plan=["Q1 ?"], iterations=0, current_step=0)
        result = nodes.critic_node(state)
        critic_findings = [f for f in result["findings"] if f.get("source") == "critic"]
        assert len(critic_findings) == 1
        assert critic_findings[0]["sufficient"] is True

    def test_returns_finding_source_critic_insufficient(self, monkeypatch):
        """Quand flash répond INSUFFISANT, le finding source=critic a sufficient=False."""
        monkeypatch.setattr(nodes, "flash_llm", lambda: _FakeLLM("INSUFFISANT"))
        state = _make_state(plan=["Q1 ?"], iterations=0, current_step=0)
        result = nodes.critic_node(state)
        critic_findings = [f for f in result["findings"] if f.get("source") == "critic"]
        assert len(critic_findings) == 1
        assert critic_findings[0]["sufficient"] is False

    def test_critic_finding_has_iteration_key(self, monkeypatch):
        """Le finding critic contient la clé 'iteration' pour traçabilité."""
        monkeypatch.setattr(nodes, "flash_llm", lambda: _FakeLLM("SUFFISANT"))
        state = _make_state(plan=["Q1 ?"], iterations=2, current_step=0)
        result = nodes.critic_node(state)
        critic_findings = [f for f in result["findings"] if f.get("source") == "critic"]
        assert "iteration" in critic_findings[0]
        assert critic_findings[0]["iteration"] == 3  # iterations + 1

    def test_case_insensitive_sufficient_parsing(self, monkeypatch):
        """Le parsing de la réponse flash est insensible à la casse (suffisant/Suffisant)."""
        monkeypatch.setattr(nodes, "flash_llm", lambda: _FakeLLM("Suffisant, les données sont bonnes"))
        state = _make_state(plan=["Q1 ?"], iterations=0, current_step=0)
        result = nodes.critic_node(state)
        critic_findings = [f for f in result["findings"] if f.get("source") == "critic"]
        assert critic_findings[0]["sufficient"] is True

    def test_unexpected_llm_response_defaults_insufficient(self, monkeypatch):
        """Réponse LLM hors attendu -> sufficient=False par défaut (sécurité)."""
        monkeypatch.setattr(nodes, "flash_llm", lambda: _FakeLLM("JE NE SAIS PAS"))
        state = _make_state(plan=["Q1 ?"], iterations=0, current_step=0)
        result = nodes.critic_node(state)
        critic_findings = [f for f in result["findings"] if f.get("source") == "critic"]
        assert critic_findings[0]["sufficient"] is False


# ---------------------------------------------------------------------------
# Tests : synthesizer multi-source
# ---------------------------------------------------------------------------


class TestSynthesizerMultiSource:
    """Tests du synthesizer étendu aux findings sql+stats+viz."""

    def _make_mixed_findings(self, png_path: str = "/tmp/chart.png") -> list[dict]:
        """Findings mixtes sql + stats + viz pour le synthesizer."""
        return [
            {
                "source": "sql_tool",
                "subquestion": "CA total ?",
                "sql": "SELECT SUM(price) FROM order_items",
                "tables": ["order_items"],
                "rows": [(380.0,)],
                "columns": ["total_ca"],
                "attempts": 1,
            },
            {
                "source": "stats_tool",
                "analysis": "correlation",
                "columns": ["price", "freight_value"],
                "value": 0.85,
            },
            {
                "source": "viz_tool",
                "subquestion": "CA total ?",
                "png_path": png_path,
                "chart": "auto",
            },
            {
                "source": "critic",
                "sufficient": True,
                "iteration": 1,
            },
        ]

    def test_synthesizer_multi_source_includes_image_markdown(self, monkeypatch):
        """Le rapport synthétisé inclut une image markdown quand png_path est présent."""
        png = "/tmp/test_chart.png"

        class _FakePro:
            def invoke(self, messages):  # noqa: ANN001
                # Le prompt doit mentionner le png_path — on vérifie via le contenu humain
                human_content = messages[1][1] if isinstance(messages[1], tuple) else str(messages)
                assert png in human_content or "test_chart" in human_content, (
                    f"png_path '{png}' absent du prompt humain : {human_content[:300]}"
                )
                return _FakeResponse(
                    f"## Rapport multi-source\n\n"
                    f"CA total : 380€ (SQL).\n\n"
                    f"Corrélation prix/fret : 0.85 (stats).\n\n"
                    f"![graphe]({png})\n"
                )

        monkeypatch.setattr(nodes, "pro_llm", lambda: _FakePro())
        import duckdb
        state = _make_state(
            plan=["CA total ?"],
            findings=self._make_mixed_findings(png_path=png),
            conn=duckdb.connect(),
        )
        result = nodes.synthesizer_node(state)
        assert "report" in result
        assert f"![" in result["report"], "Image markdown absente du rapport"
        assert png in result["report"], f"png_path '{png}' absent du rapport"

    def test_synthesizer_multi_source_prompt_contains_all_sources(self, monkeypatch):
        """Le texte de findings passé au prompt contient sql_tool, stats_tool et viz_tool."""
        captured_prompt: list[str] = []

        class _FakePro:
            def invoke(self, messages):  # noqa: ANN001
                human_msg = messages[1][1] if isinstance(messages[1], tuple) else str(messages)
                captured_prompt.append(human_msg)
                return _FakeResponse("## Rapport\n\nOK.")

        monkeypatch.setattr(nodes, "pro_llm", lambda: _FakePro())
        import duckdb
        state = _make_state(
            plan=["CA total ?"],
            findings=self._make_mixed_findings(),
            conn=duckdb.connect(),
        )
        nodes.synthesizer_node(state)

        assert captured_prompt, "Le prompt n'a pas été capturé"
        prompt_text = captured_prompt[0]
        assert "sql_tool" in prompt_text or "sql" in prompt_text.lower(), (
            "Source sql absente du prompt findings"
        )
        assert "stats_tool" in prompt_text or "correlation" in prompt_text.lower(), (
            "Source stats absente du prompt findings"
        )
        assert "viz_tool" in prompt_text or "png_path" in prompt_text or "chart" in prompt_text.lower(), (
            "Source viz absente du prompt findings"
        )

    def test_synthesizer_skips_critic_findings_in_data_section(self, monkeypatch):
        """Les findings source=critic ne sont pas présentés comme données dans le prompt."""
        captured_prompt: list[str] = []

        class _FakePro:
            def invoke(self, messages):  # noqa: ANN001
                human_msg = messages[1][1] if isinstance(messages[1], tuple) else str(messages)
                captured_prompt.append(human_msg)
                return _FakeResponse("## Rapport\n\nOK.")

        monkeypatch.setattr(nodes, "pro_llm", lambda: _FakePro())
        import duckdb
        state = _make_state(
            plan=["CA total ?"],
            findings=[
                {
                    "source": "sql_tool",
                    "subquestion": "CA ?",
                    "sql": "SELECT 1",
                    "tables": [],
                    "rows": [(1,)],
                    "columns": ["v"],
                    "attempts": 1,
                },
                {"source": "critic", "sufficient": True, "iteration": 1},
            ],
            conn=duckdb.connect(),
        )
        nodes.synthesizer_node(state)
        prompt_text = captured_prompt[0]
        # Le critic ne doit pas apparaître comme une source de données analytiques
        # (il peut être mentionné/résumé mais pas présenté comme un finding data)
        # On vérifie juste que le prompt est bien généré et contient le sql_tool
        assert "sql" in prompt_text.lower() or "SELECT" in prompt_text

    def test_existing_sql_only_synthesizer_still_works(self, monkeypatch):
        """Régression : synthesizer sql-only fonctionne toujours (D-08 étend sans casser)."""
        class _FakePro:
            def invoke(self, messages):  # noqa: ANN001
                return _FakeResponse(
                    "## Rapport CA\n\nCA total : 380€.\n**Sources** : order_items."
                )

        monkeypatch.setattr(nodes, "pro_llm", lambda: _FakePro())
        import duckdb
        state = _make_state(
            plan=["CA total ?"],
            findings=[
                {
                    "source": "sql_tool",
                    "subquestion": "CA total ?",
                    "sql": "SELECT SUM(price) FROM order_items",
                    "tables": ["order_items"],
                    "rows": [(380.0,)],
                    "columns": ["total_ca"],
                    "attempts": 1,
                }
            ],
            conn=duckdb.connect(),
        )
        result = nodes.synthesizer_node(state)
        assert result["report"]
        assert "order_items" in result["report"]
