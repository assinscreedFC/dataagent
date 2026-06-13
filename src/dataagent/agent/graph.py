"""Graphe LangGraph agentique branché : START -> planner -> router -> {sql|stats|viz} -> critic -> {router|synthesizer} -> END.

Conforme D-01 (path_map obligatoire anti-misroute silencieux), D-04 (StateGraph compilé),
D-05 (connexion DuckDB créée à l'entrée), D-06 (hard cap max_iterations via _critic_decision),
GRAPH-06 (run helper pour le CLI), TOOL-04 (router conditionnel), TOOL-05 (critic reboucle),
TOOL-06 (arrêt hard cap), TOOL-07 (resumabilité via checkpointer SqliteSaver), TOOL-08 (rapport multi-source).
"""

import sqlite3
from typing import Literal

from langgraph.checkpoint.sqlite import SqliteSaver
from langgraph.graph import END, START, StateGraph

from dataagent.agent.nodes import (
    critic_node,
    planner_node,
    route_subquestion,
    sql_tool_node,
    stats_tool_node,
    synthesizer_node,
    viz_tool_node,
)
from dataagent.agent.state import AgentState, initial_state
from dataagent.config import CHECKPOINT_DB, DATA_RAW
from dataagent.data.loader import connect, load_csvs_to_duckdb


# ---------------------------------------------------------------------------
# Nodes internes au graphe
# ---------------------------------------------------------------------------


def _router_node(state: AgentState) -> dict:
    """Node pass-through servant de pivot pour add_conditional_edges du router.

    Ne modifie pas le state : retourne {} (pas de merge nécessaire).
    Le conditional edge add_conditional_edges("router", route_subquestion, path_map)
    appelle route_subquestion APRÈS ce node pour dispatcher vers sql/stats/viz.
    """
    return {}


# ---------------------------------------------------------------------------
# Fonction de décision critic (conditional edge)
# ---------------------------------------------------------------------------


def _critic_decision(state: AgentState) -> Literal["router", "synthesizer"]:
    """Décide si la boucle reboucle vers router ou sort vers synthesizer.

    Lit le DERNIER finding source="critic" (exposé par critic_node via Plan 01).
    Retourne "synthesizer" si :
      - le dernier critic finding est sufficient=True, OU
      - state["iterations"] >= state["max_iterations"] (HARD CAP D-06 — pas de boucle infinie)
    Retourne "router" sinon (reboucle — critic non satisfait ET sous le plafond).

    Type-hinté Literal (D-01, D-05 — anti-misroute silencieux).
    """
    iterations: int = state.get("iterations", 0)
    max_iterations: int = state.get("max_iterations", 5)

    # Hard cap : arrêt inconditionnel à max_iterations (TOOL-06)
    if iterations >= max_iterations:
        return "synthesizer"

    # Lire le dernier verdict du critic
    findings: list[dict] = state.get("findings", [])
    critic_findings = [f for f in findings if f.get("source") == "critic"]
    if critic_findings:
        last_critic = critic_findings[-1]
        if last_critic.get("sufficient", False):
            return "synthesizer"

    # Pas de finding critic ou insuffisant — reboucle
    return "router"


# ---------------------------------------------------------------------------
# build_graph
# ---------------------------------------------------------------------------


def build_graph(checkpointer=None):
    """Compile le graphe agentique branché conforme au schéma PLAN.md (TOOL-04/05/06/07/08).

    Topologie :
        START -> planner -> router -+-> sql_tool ---+
                                    +-> stats_tool -+-> critic -> (cond) -+-> router
                                    +-> viz_tool ---+                     +-> synthesizer -> END

    Câblage :
    - add_conditional_edges("router", route_subquestion, path_map) : dispatche vers le bon tool
      via path_map EXPLICITE (D-01 anti-misroute silencieux, TOOL-04).
    - add_edge tool -> critic pour chaque tool.
    - add_conditional_edges("critic", _critic_decision, path_map) : reboucle ou synthétise
      selon sufficient et hard cap (D-05, D-06, TOOL-05, TOOL-06).

    Returns:
        CompiledStateGraph prêt à invoquer.
    """
    g = StateGraph(AgentState)

    # Enregistrement des nodes
    g.add_node("planner", planner_node)
    g.add_node("router", _router_node)
    g.add_node("sql_tool", sql_tool_node)
    g.add_node("stats_tool", stats_tool_node)
    g.add_node("viz_tool", viz_tool_node)
    g.add_node("critic", critic_node)
    g.add_node("synthesizer", synthesizer_node)

    # Edges linéaires : START -> planner -> router
    g.add_edge(START, "planner")
    g.add_edge("planner", "router")

    # Conditional edge du router : dispatche vers sql/stats/viz selon route_subquestion
    # path_map OBLIGATOIRE (D-01) — chaque Literal retourné est mappé vers un node nommé
    g.add_conditional_edges(
        "router",
        route_subquestion,
        path_map={
            "sql_tool": "sql_tool",
            "stats_tool": "stats_tool",
            "viz_tool": "viz_tool",
        },
    )

    # Edges tool -> critic (chaque tool passe par le critic)
    g.add_edge("sql_tool", "critic")
    g.add_edge("stats_tool", "critic")
    g.add_edge("viz_tool", "critic")

    # Conditional edge du critic : reboucle ou synthétise
    # path_map OBLIGATOIRE (D-05) — anti-misroute silencieux
    g.add_conditional_edges(
        "critic",
        _critic_decision,
        path_map={
            "router": "router",
            "synthesizer": "synthesizer",
        },
    )

    # Edge de sortie : synthesizer -> END
    g.add_edge("synthesizer", END)

    return g.compile(checkpointer=checkpointer)


# ---------------------------------------------------------------------------
# run
# ---------------------------------------------------------------------------


def run(question: str, conn=None, thread_id: str | None = None) -> dict:
    """Invoque le graphe agentique pour une question donnée et retourne l'état final.

    Crée la connexion DuckDB + charge Olist si `conn` n'est pas injecté (D-05).
    Le paramètre optionnel `conn` permet l'injection en test (fixture mini-Olist,
    sans recharger les 9 CSV réels).

    Resumabilité (TOOL-07, D-03/D-04/D-05) :
    - Sans `thread_id` : run éphémère, comportement Phase 4 inchangé.
    - Avec `thread_id` : compile le graphe avec un SqliteSaver sur CHECKPOINT_DB et
      invoque avec config thread_id. LangGraph restaure automatiquement le dernier
      checkpoint du thread (plan/findings/iterations/current_step). La connexion DuckDB
      est UntrackedValue (jamais checkpointée) — elle est ré-injectée fraîche à chaque
      run via initial_state(), même à la reprise (D-05).

    Args:
        question: La question business en langage naturel.
        conn: Connexion DuckDB déjà chargée (optionnel — injection de test ou reprise).
        thread_id: Identifiant de thread pour la persistance SQLite (optionnel).
            Si fourni, l'état est checkpointé dans CHECKPOINT_DB et un run ultérieur
            avec le même thread_id reprendra depuis le dernier checkpoint.

    Returns:
        AgentState final (dict) contenant plan, findings, report, iterations, etc.
    """
    if conn is None:
        conn = connect()
        load_csvs_to_duckdb(conn, DATA_RAW)

    state = initial_state(question, conn)

    if thread_id is None:
        # Run éphémère : comportement Phase 4 intact (D-03)
        app = build_graph()
        return app.invoke(state)

    # Run persistant : checkpointer SqliteSaver sur CHECKPOINT_DB (TOOL-07, D-03/D-04)
    # Connexion sqlite3 explicite (pas from_conn_string — context manager incompatible
    # avec un graphe persistant retourné).
    saver_conn = sqlite3.connect(str(CHECKPOINT_DB), check_same_thread=False)
    try:
        checkpointer = SqliteSaver(saver_conn)
        app = build_graph(checkpointer=checkpointer)
        config = {"configurable": {"thread_id": thread_id}}
        return app.invoke(state, config=config)
    finally:
        saver_conn.close()
