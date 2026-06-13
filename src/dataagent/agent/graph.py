"""Graphe LangGraph minimal : START -> planner -> sql_tool -> synthesizer -> END.

Conforme D-04 (StateGraph compilé), D-05 (connexion DuckDB créée à l'entrée),
GRAPH-02 (boucle linéaire), GRAPH-06 (run helper pour le CLI).
"""

from langgraph.graph import END, START, StateGraph

from dataagent.agent.nodes import planner_node, sql_tool_node, synthesizer_node
from dataagent.agent.state import AgentState, initial_state
from dataagent.config import DATA_RAW
from dataagent.data.loader import connect, load_csvs_to_duckdb


def build_graph():
    """Compile le graphe linéaire minimal (D-04, GRAPH-02).

    Edges : START -> planner -> sql_tool -> synthesizer -> END.
    Appel à .compile() obligatoire avant invoke.

    Returns:
        CompiledStateGraph prêt à invoquer.
    """
    g = StateGraph(AgentState)
    g.add_node("planner", planner_node)
    g.add_node("sql_tool", sql_tool_node)
    g.add_node("synthesizer", synthesizer_node)
    g.add_edge(START, "planner")
    g.add_edge("planner", "sql_tool")
    g.add_edge("sql_tool", "synthesizer")
    g.add_edge("synthesizer", END)
    return g.compile()


def run(question: str, conn=None) -> dict:
    """Invoque le graphe pour une question donnée et retourne l'état final.

    Crée la connexion DuckDB + charge Olist si `conn` n'est pas injecté (D-05).
    Le paramètre optionnel `conn` permet l'injection en test (fixture mini-Olist,
    sans recharger les 9 CSV réels).

    Args:
        question: La question business en langage naturel.
        conn: Connexion DuckDB déjà chargée (optionnel — injection de test).

    Returns:
        AgentState final (dict) contenant plan, findings, report, etc.
    """
    if conn is None:
        conn = connect()
        load_csvs_to_duckdb(conn, DATA_RAW)

    state = initial_state(question, conn)
    app = build_graph()
    return app.invoke(state)
