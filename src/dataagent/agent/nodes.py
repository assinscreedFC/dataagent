"""Nodes de la boucle agent LangGraph minimale.

Trois nodes (fonctions state -> dict) consommés par le graphe (plan 03) :
- planner_node  : question -> plan[] (sous-questions, Flash, GRAPH-03, D-08)
- sql_tool_node : plan[] -> findings[] (génère+exécute SQL, Flash, D-12)
- synthesizer_node : findings[] -> report (markdown sourcé, Pro, GRAPH-04, D-09)
"""

import logging
import re

import duckdb

from dataagent.agent.llm import flash_llm, pro_llm
from dataagent.agent.schema_introspect import schema_description
from dataagent.agent.state import AgentState

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# planner_node
# ---------------------------------------------------------------------------


def planner_node(state: AgentState) -> dict:
    """Décompose la question business en sous-questions analytiques (plan[]).

    Utilise Flash (cheap/rapide, D-07). Retourne {"plan": list[str]} non vide.
    """
    question = state["question"]

    system_msg = (
        "Décompose cette question business en 1 à 4 sous-questions analytiques "
        "précises, une par ligne, sans numérotation."
    )
    response = flash_llm().invoke([("system", system_msg), ("human", question)])
    raw: str = response.content

    # Parse les lignes non vides
    plan = [line.strip() for line in raw.splitlines() if line.strip()]

    # Garantir plan non vide : au minimum la question elle-même
    if not plan:
        plan = [question]

    return {"plan": plan}


# ---------------------------------------------------------------------------
# sql_tool_node
# ---------------------------------------------------------------------------

_SQL_FENCE_RE = re.compile(r"```(?:sql)?\s*\n?(.*?)\n?```", re.DOTALL | re.IGNORECASE)


def _clean_sql(raw_sql: str) -> str:
    """Supprime les fences markdown éventuelles autour du SQL."""
    match = _SQL_FENCE_RE.search(raw_sql)
    if match:
        return match.group(1).strip()
    return raw_sql.strip()


def _extract_tables(sql: str, schema: str) -> list[str]:
    """Extrait les noms de tables du SQL en les croisant avec le schéma connu."""
    known_tables = re.findall(r"^TABLE (\S+)\(", schema, re.MULTILINE)
    sql_upper = sql.upper()
    return [t for t in known_tables if t.upper() in sql_upper]


def _execute_subquestion(
    conn: duckdb.DuckDBPyConnection,
    schema: str,
    subquestion: str,
) -> dict:
    """Génère et exécute le SQL pour une sous-question. Retourne un finding dict."""
    # Génération SQL avec Flash
    system_msg = (
        f"Voici le schema DuckDB :\n{schema}\n"
        "Écris UNE requête SQL DuckDB valide qui répond à la question suivante. "
        "Réponds avec le SQL brut uniquement, sans markdown."
    )
    response = flash_llm().invoke([("system", system_msg), ("human", subquestion)])
    sql = _clean_sql(response.content)

    base_finding: dict = {
        "source": "sql_tool",
        "subquestion": subquestion,
        "sql": sql,
    }

    try:
        cursor = conn.execute(sql)
        rows = cursor.fetchall()
        columns = [desc[0] for desc in cursor.description] if cursor.description else []
        tables = _extract_tables(sql, schema)
        return {**base_finding, "tables": tables, "rows": rows, "columns": columns}
    except (duckdb.Error, Exception) as exc:  # noqa: BLE001
        logger.error(
            "sql_tool_node: SQL execution failed — subquestion=%r sql=%r error=%s",
            subquestion,
            sql,
            exc,
        )
        return {**base_finding, "error": str(exc)}


def sql_tool_node(state: AgentState) -> dict:
    """Génère et exécute du SQL pour chaque sous-question du plan.

    Minimal (D-12) : pas de validation ni retry (phase 2).
    Erreur SQL -> finding d'erreur propre, pas de crash, pas de re-raise.
    Incrémente iterations (structure prête phase 4, D-10).

    Retourne {"findings": [...], "iterations": N+1}.
    """
    conn: duckdb.DuckDBPyConnection = state["db"]
    schema = schema_description(conn)
    plan: list[str] = state.get("plan") or [state["question"]]

    findings = []
    for subquestion in plan:
        finding = _execute_subquestion(conn, schema, subquestion)
        findings.append(finding)

    return {
        "findings": findings,
        "iterations": state["iterations"] + 1,
    }


# ---------------------------------------------------------------------------
# synthesizer_node
# ---------------------------------------------------------------------------


def _serialize_findings(findings: list[dict]) -> str:
    """Sérialise les findings en texte structuré pour le prompt Pro."""
    if not findings:
        return "(aucun finding disponible)"

    parts: list[str] = []
    for i, f in enumerate(findings, 1):
        lines = [f"Finding {i}:"]
        lines.append(f"  Sous-question : {f.get('subquestion', '?')}")
        lines.append(f"  SQL : {f.get('sql', '?')}")
        if "error" in f:
            lines.append(f"  ERREUR : {f['error']}")
        else:
            tables = f.get("tables", [])
            rows = f.get("rows", [])
            cols = f.get("columns", [])
            lines.append(f"  Tables : {', '.join(tables) if tables else '?'}")
            lines.append(f"  Colonnes : {', '.join(cols)}")
            lines.append(f"  Résultats ({len(rows)} lignes) : {rows[:10]}")
        parts.append("\n".join(lines))

    return "\n\n".join(parts)


def synthesizer_node(state: AgentState) -> dict:
    """Produit un rapport markdown citant explicitement les sources (GRAPH-04, D-09).

    Utilise Pro (qualité rapport, D-07).
    Si findings vides ou tous en erreur : rapport markdown expliquant l'échec.

    Retourne {"report": str}.
    """
    question = state["question"]
    findings = state.get("findings", [])
    findings_text = _serialize_findings(findings)

    system_msg = (
        "Tu es analyste data. À partir de ces findings, rédige un rapport markdown "
        "concis qui répond à la question. "
        "CITE explicitement tes sources : pour chaque chiffre, indique la/les table(s) "
        "et la query SQL utilisées."
    )
    human_msg = (
        f"Question : {question}\n\nFindings :\n{findings_text}"
    )

    response = pro_llm().invoke([("system", system_msg), ("human", human_msg)])
    report: str = response.content

    return {"report": report}
