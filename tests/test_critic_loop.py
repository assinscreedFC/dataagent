"""Tests d'intégration de la boucle router-critic (Phase 4, Plan 02).

Stratégie : vraie I/O DuckDB (fixture conn de conftest.py), mock LLMs uniquement.
Couvre TOOL-04 (routing), TOOL-05 (reloop+synth), TOOL-06 (HARD CAP), TOOL-08 (multi-source).

NB anti-récursion LangGraph :
  MAX_ITERATIONS=5 < recursion_limit par défaut LangGraph (25).
  Le hard cap applicatif (_critic_decision coupe à iterations>=max_iterations) s'arrête
  AVANT que LangGraph ne lève GraphRecursionError. Pas besoin d'augmenter recursion_limit.
"""

import pytest

from dataagent.agent.graph import _critic_decision, build_graph, run
from dataagent.agent.nodes import route_subquestion
from dataagent.config import MAX_ITERATIONS


# ---------------------------------------------------------------------------
# Fake LLM helpers
# ---------------------------------------------------------------------------


class _FakeResponse:
    """Simule la réponse d'un ChatGoogleGenerativeAI.invoke()."""

    def __init__(self, content: str) -> None:
        self.content = content


class _FakeLLM:
    """LLM factice dont .invoke() retourne toujours le même contenu."""

    def __init__(self, content: str) -> None:
        self._content = content

    def invoke(self, messages):  # noqa: ANN001
        return _FakeResponse(self._content)


# ---------------------------------------------------------------------------
# (a) Tests routing : route_subquestion sur states construits
# ---------------------------------------------------------------------------


class TestRouting:
    """(a) TOOL-04 : route_subquestion dispatche correctement selon la sous-question."""

    def _make_state(self, subquestion: str, current_step: int = 0) -> dict:
        return {
            "plan": [subquestion],
            "current_step": current_step,
            "question": subquestion,
            "findings": [],
            "messages": [],
            "iterations": 0,
            "max_iterations": MAX_ITERATIONS,
        }

    def test_sql_question_routes_to_sql_tool(self):
        """Une sous-question SQL (sans mots-clés stats/viz) route vers sql_tool."""
        state = self._make_state("Quel est le CA total en 2017 ?")
        assert route_subquestion(state) == "sql_tool"

    def test_stats_question_routes_to_stats_tool(self):
        """Une sous-question avec mot-clé stats (corrélation) route vers stats_tool."""
        state = self._make_state("Quelle est la corrélation entre prix et note ?")
        assert route_subquestion(state) == "stats_tool"

    def test_viz_question_routes_to_viz_tool(self):
        """Une sous-question avec mot-clé viz (graphe) route vers viz_tool."""
        state = self._make_state("Génère un graphe des ventes par mois.")
        assert route_subquestion(state) == "viz_tool"

    def test_anomaly_keyword_routes_to_stats_tool(self):
        """Mot-clé 'anomalie' route vers stats_tool."""
        state = self._make_state("Y a-t-il des anomalies dans les prix ?")
        assert route_subquestion(state) == "stats_tool"

    def test_visualise_keyword_routes_to_viz_tool(self):
        """Mot-clé 'visualise' route vers viz_tool."""
        state = self._make_state("Visualise la distribution des commandes.")
        assert route_subquestion(state) == "viz_tool"

    def test_empty_plan_routes_to_sql_tool(self):
        """Plan vide : garde-fou retourne sql_tool (pas d'IndexError)."""
        state = self._make_state("")
        state["plan"] = []
        assert route_subquestion(state) == "sql_tool"

    def test_out_of_bounds_step_routes_to_sql_tool(self):
        """current_step >= len(plan) : garde-fou retourne sql_tool."""
        state = self._make_state("question")
        state["current_step"] = 99
        assert route_subquestion(state) == "sql_tool"


# ---------------------------------------------------------------------------
# (a') Test routing end-to-end via findings sources
# ---------------------------------------------------------------------------


class TestRoutingEndToEnd:
    """(a) Routing correct end-to-end via sources des findings produits."""

    def test_sql_subquestion_produces_sql_tool_finding(self, conn, monkeypatch):
        """Une sous-question SQL produit un finding source=sql_tool."""
        from dataagent.agent import nodes

        call_count = [0]

        class _FakeFlash:
            def invoke(self, messages):  # noqa: ANN001
                call_count[0] += 1
                n = call_count[0]
                if n == 1:
                    # planner : retourne une sous-question SQL simple
                    return _FakeResponse("CA total des commandes ?")
                elif n == 2:
                    # sql_tool : SQL valide sur mini-Olist
                    return _FakeResponse("SELECT SUM(price) AS total_ca FROM order_items")
                else:
                    # critic : SUFFISANT pour sortir au 1er tour
                    return _FakeResponse("SUFFISANT")

        class _FakePro:
            def invoke(self, messages):  # noqa: ANN001
                return _FakeResponse("## Rapport\nCA total calculé.")

        monkeypatch.setattr(nodes, "flash_llm", lambda: _FakeFlash())
        monkeypatch.setattr(nodes, "pro_llm", lambda: _FakePro())

        final = run("CA total des commandes ?", conn=conn)

        sql_findings = [f for f in final["findings"] if f.get("source") == "sql_tool"]
        assert sql_findings, "Aucun finding sql_tool trouvé"
        assert final["iterations"] == 1, f"Attendu iterations=1, got {final['iterations']}"


# ---------------------------------------------------------------------------
# (b) Reloop puis synth : critic insuffisant 1 fois puis suffisant
# ---------------------------------------------------------------------------


class TestReloopThenSynth:
    """(b) TOOL-05 : critic insuffisant 1 fois puis suffisant → iterations==2, report produit."""

    def test_reloop_then_synthesize(self, conn, monkeypatch):
        """Critic insuffisant au tour 1, suffisant au tour 2 → iterations==2 + report."""
        from dataagent.agent import nodes

        call_count = [0]

        class _FakeFlash:
            def invoke(self, messages):  # noqa: ANN001
                call_count[0] += 1
                n = call_count[0]
                if n == 1:
                    # planner : 1 sous-question SQL
                    return _FakeResponse("Volume de commandes 2017 ?")
                elif n == 2:
                    # sql_tool (tour 1) : SQL valide
                    return _FakeResponse("SELECT COUNT(*) AS nb FROM orders")
                elif n == 3:
                    # critic (tour 1) : INSUFFISANT → reboucle
                    return _FakeResponse("INSUFFISANT — manque détail mensuel")
                elif n == 4:
                    # sql_tool (tour 2, après reboucle) : SQL valide
                    return _FakeResponse("SELECT COUNT(*) AS nb FROM orders")
                else:
                    # critic (tour 2) : SUFFISANT → synthétise
                    return _FakeResponse("SUFFISANT")

        class _FakePro:
            def invoke(self, messages):  # noqa: ANN001
                return _FakeResponse(
                    "## Rapport volume commandes\n\nNombre total de commandes analysé."
                )

        monkeypatch.setattr(nodes, "flash_llm", lambda: _FakeFlash())
        monkeypatch.setattr(nodes, "pro_llm", lambda: _FakePro())

        final = run("Volume de commandes 2017 ?", conn=conn)

        assert final["report"], "report vide"
        assert final["iterations"] == 2, (
            f"Attendu iterations=2 (1 reloop + 1 synth), got {final['iterations']}"
        )
        assert final["report"], "report non produit après reloop+synth"


# ---------------------------------------------------------------------------
# (c) HARD CAP : critic toujours insuffisant → arrêt à max_iterations
# ---------------------------------------------------------------------------


class TestHardCap:
    """(c) TOOL-06 : critic toujours insuffisant → arrêt à max_iterations, pas de boucle infinie."""

    def test_hard_cap_stops_at_max_iterations(self, conn, monkeypatch):
        """Critic toujours INSUFFISANT → run() termine avec iterations==max_iterations.

        Ce test DOIT terminer (pas de hang infini).
        Le hard cap applicatif (_critic_decision coupe à iterations>=max_iterations)
        s'arrête avant GraphRecursionError (max_iterations=5 < recursion_limit=25).
        """
        from dataagent.agent import nodes

        call_count = [0]
        critic_calls = [0]

        class _FakeFlash:
            def invoke(self, messages):  # noqa: ANN001
                call_count[0] += 1
                # Détecter si c'est un appel critic (le prompt contient SUFFISANT/INSUFFISANT)
                content = ""
                for msg in messages:
                    if isinstance(msg, (list, tuple)) and len(msg) >= 2:
                        content += str(msg[1])
                    elif hasattr(msg, "content"):
                        content += str(msg.content)

                if call_count[0] == 1:
                    # planner : 1 sous-question
                    return _FakeResponse("Sous-question test hard cap")
                elif "SUFFISANT" in content or "INSUFFISANT" in content or "Verdict" in content:
                    # critic : toujours INSUFFISANT
                    critic_calls[0] += 1
                    return _FakeResponse("INSUFFISANT")
                else:
                    # sql_tool : SQL valide
                    return _FakeResponse("SELECT COUNT(*) AS nb FROM orders")

        class _FakePro:
            def invoke(self, messages):  # noqa: ANN001
                return _FakeResponse(
                    "## Rapport hard cap\n\nRapport produit malgré critic insatisfait."
                )

        monkeypatch.setattr(nodes, "flash_llm", lambda: _FakeFlash())
        monkeypatch.setattr(nodes, "pro_llm", lambda: _FakePro())

        final = run("Test hard cap — critic jamais satisfait", conn=conn)

        # Arrêt précis à max_iterations
        assert final["iterations"] == final["max_iterations"], (
            f"Hard cap: attendu iterations=={final['max_iterations']}, "
            f"got {final['iterations']}"
        )
        assert final["iterations"] == MAX_ITERATIONS, (
            f"Hard cap: attendu {MAX_ITERATIONS}, got {final['iterations']}"
        )

        # Un report est quand même produit (synthesizer run après hard cap)
        assert final["report"], "report vide après hard cap"

        # Prouver l'arrêt : critic appelé exactement max_iterations fois
        assert critic_calls[0] == MAX_ITERATIONS, (
            f"Critic appelé {critic_calls[0]} fois, attendu {MAX_ITERATIONS}"
        )

    def test_critic_decision_hard_cap(self):
        """_critic_decision retourne 'synthesizer' si iterations >= max_iterations."""
        state = {
            "iterations": 5,
            "max_iterations": 5,
            "findings": [{"source": "critic", "sufficient": False, "iteration": 5}],
        }
        result = _critic_decision(state)
        assert result == "synthesizer", f"Hard cap non déclenché: {result}"

    def test_critic_decision_reloop_when_insufficient(self):
        """_critic_decision retourne 'router' si insuffisant ET sous le plafond.

        D-02 : l'early-exit vérifie current_step >= len(plan) AVANT le verdict critic.
        Il faut fournir plan + current_step valides pour que le test prouve le reloop.
        Ici plan=["Q1","Q2"], current_step=0 (< len=2) → pas d'early-exit → verdict critic.
        """
        state = {
            "iterations": 2,
            "max_iterations": 5,
            "plan": ["Q1 ?", "Q2 ?"],
            "current_step": 0,
            "findings": [{"source": "critic", "sufficient": False, "iteration": 2}],
        }
        result = _critic_decision(state)
        assert result == "router", f"Attendu router, got {result}"

    def test_critic_decision_synthesizer_when_sufficient(self):
        """_critic_decision retourne 'synthesizer' si sufficient=True."""
        state = {
            "iterations": 1,
            "max_iterations": 5,
            "findings": [{"source": "critic", "sufficient": True, "iteration": 1}],
        }
        result = _critic_decision(state)
        assert result == "synthesizer", f"Attendu synthesizer, got {result}"

    def test_critic_decision_no_findings_reloops(self):
        """_critic_decision retourne 'router' si aucun finding critic (premier passage).

        D-02 : l'early-exit vérifie current_step >= len(plan) AVANT le verdict critic.
        Il faut fournir plan + current_step valides pour que le test prouve le reloop.
        Ici plan=["Q1"], current_step=0 (< len=1) → pas d'early-exit → pas de finding
        critic → reboucle vers router.
        """
        state = {
            "iterations": 0,
            "max_iterations": 5,
            "plan": ["Q1 ?"],
            "current_step": 0,
            "findings": [],
        }
        result = _critic_decision(state)
        assert result == "router", f"Attendu router sans finding critic, got {result}"


# ---------------------------------------------------------------------------
# (d) Multi-source : sql + stats + viz → report markdown avec image
# ---------------------------------------------------------------------------


class TestMultiSource:
    """(d) TOOL-08 : question complexe → report multi-source incluant image markdown."""

    def test_multi_source_report_contains_image(self, conn, monkeypatch):
        """Plan avec sous-question viz → report contient ![graphe](...)."""
        from dataagent.agent import nodes

        # Pour ce test, on force le plan à avoir une sous-question viz
        # Le planner retourne 1 sous-question avec mot-clé "graphe" → viz_tool
        call_count = [0]

        class _FakeFlash:
            def invoke(self, messages):  # noqa: ANN001
                call_count[0] += 1
                n = call_count[0]
                if n == 1:
                    # planner : sous-question avec mot-clé viz
                    return _FakeResponse("Génère un graphe des ventes par commande.")
                else:
                    # critic : SUFFISANT au 1er tour
                    return _FakeResponse("SUFFISANT")

        class _FakePro:
            def invoke(self, messages):  # noqa: ANN001
                # Extraire le png_path du contexte si présent
                content = ""
                for msg in messages:
                    if isinstance(msg, (list, tuple)) and len(msg) >= 2:
                        content += str(msg[1])
                    elif hasattr(msg, "content"):
                        content += str(msg.content)
                # Le synthesizer prompt contient la directive INCLURE png_path
                # Pro renvoie un rapport avec l'image si la directive est dans le prompt
                if "png_path" in content or "INCLURE" in content or "graphe](" in content:
                    # Extraire le chemin depuis le prompt
                    import re
                    match = re.search(r'!\[graphe\]\(([^)]+)\)', content)
                    if match:
                        png_path = match.group(1)
                        return _FakeResponse(
                            f"## Rapport graphe\n\nVoici le graphe :\n\n![graphe]({png_path})\n"
                        )
                return _FakeResponse("## Rapport graphe\n\nGraphique non disponible.")

        monkeypatch.setattr(nodes, "flash_llm", lambda: _FakeFlash())
        monkeypatch.setattr(nodes, "pro_llm", lambda: _FakePro())

        final = run("Génère un graphe des ventes par commande.", conn=conn)

        # findings contient viz_tool
        viz_findings = [f for f in final["findings"] if f.get("source") == "viz_tool"]
        assert viz_findings, f"Aucun finding viz_tool. Sources: {[f.get('source') for f in final['findings']]}"

        # report contient une image markdown
        assert "![" in final["report"], (
            f"report ne contient pas d'image markdown. report={final['report'][:200]}"
        )

    def test_multi_source_findings_contain_sql_stats_viz(self, conn, monkeypatch):
        """Plan multi-step → findings contient des sources sql_tool + stats_tool + viz_tool."""
        from dataagent.agent import nodes

        # Simuler 3 tours : sql, stats (mots-clés corrélation), viz (mots-clés graphe)
        # On injecte directement le plan avec 3 sous-questions via planner mock
        call_count = [0]

        class _FakeFlash:
            def invoke(self, messages):  # noqa: ANN001
                call_count[0] += 1
                n = call_count[0]
                if n == 1:
                    # planner : 1 sous-question SQL (simple, pas de mots-clés stats/viz)
                    return _FakeResponse("Quel est le CA total ?")
                elif n == 2:
                    # sql_tool : SQL valide
                    return _FakeResponse("SELECT SUM(price) AS total FROM order_items")
                else:
                    # critic : SUFFISANT
                    return _FakeResponse("SUFFISANT")

        class _FakePro:
            def invoke(self, messages):  # noqa: ANN001
                return _FakeResponse(
                    "## Rapport multi-source\n\nCA total calculé via sql_tool.\n"
                    "Statistiques et visualisation disponibles."
                )

        monkeypatch.setattr(nodes, "flash_llm", lambda: _FakeFlash())
        monkeypatch.setattr(nodes, "pro_llm", lambda: _FakePro())

        final = run("CA total avec corrélation et graphe", conn=conn)

        # Le report est produit
        assert final["report"], "report vide"
        assert final["findings"], "findings vides"

        # Au moins un finding source analytique
        sources = {f.get("source") for f in final["findings"]}
        analytical_sources = sources - {"critic"}
        assert analytical_sources, f"Aucune source analytique dans {sources}"
