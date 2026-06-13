"""Nodes de la boucle agent LangGraph minimale.

Trois nodes (fonctions state -> dict) consommés par le graphe (plan 03) :
- planner_node  : question -> plan[] (sous-questions, Flash, GRAPH-03, D-08)
- sql_tool_node : plan[] -> findings[] (génère+exécute SQL, Flash, D-12)
- synthesizer_node : findings[] -> report (markdown sourcé, Pro, GRAPH-04, D-09)
"""

import logging
import re

import duckdb
import polars as pl

from dataagent.agent.llm import flash_llm, pro_llm
from dataagent.agent.schema_introspect import schema_description
from dataagent.agent.state import AgentState
from dataagent.agent.stats import correlation, detect_anomalies
from dataagent.config import SQL_MAX_RETRIES

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


def _validate_sql(conn: duckdb.DuckDBPyConnection, sql: str) -> str | None:
    """Valide la query SQL via EXPLAIN sans scanner les données.

    EXPLAIN parse + résout tables/colonnes contre le catalogue DuckDB.
    Une référence à une table/colonne inexistante lève une exception DuckDB
    (CatalogException/BinderException) capturée comme échec de validation.

    NB sécurité : sql est généré par le LLM à partir du schema (pas d'input
    utilisateur direct concaténé) ; EXPLAIN ne mute ni ne scanne les données.
    Ne pas paramétrer : EXPLAIN ne supporte pas les placeholders sur le corps.

    Args:
        conn: Connexion DuckDB active.
        sql: Requête SQL à valider.

    Returns:
        None si la query est valide, str(exc) si invalide.
    """
    try:
        conn.execute("EXPLAIN " + sql)
        return None
    except (duckdb.Error, Exception) as exc:  # noqa: BLE001
        logger.warning(
            "_validate_sql: EXPLAIN failed — sql=%r error=%s",
            sql,
            exc,
        )
        return str(exc)


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


def _generate_sql(schema: str, subquestion: str) -> str:
    """Génère une requête SQL initiale via Flash LLM à partir du schema et de la sous-question."""
    system_msg = (
        f"Voici le schema DuckDB :\n{schema}\n"
        "Écris UNE requête SQL DuckDB valide qui répond à la question suivante. "
        "Réponds avec le SQL brut uniquement, sans markdown."
    )
    response = flash_llm().invoke([("system", system_msg), ("human", subquestion)])
    return _clean_sql(response.content)


def _regenerate_sql(schema: str, subquestion: str, bad_sql: str, error: str) -> str:
    """Re-prompte Flash LLM avec la query fautive + erreur DuckDB exacte pour correction (D-04)."""
    system_msg = (
        f"Voici le schema DuckDB :\n{schema}\n"
        f"La query suivante a échoué :\n{bad_sql}\n"
        f"Erreur DuckDB : {error}\n"
        "Corrige cette query SQL DuckDB pour répondre à la question. "
        "SQL brut uniquement."
    )
    response = flash_llm().invoke([("system", system_msg), ("human", subquestion)])
    return _clean_sql(response.content)


def _execute_subquestion(
    conn: duckdb.DuckDBPyConnection,
    schema: str,
    subquestion: str,
) -> dict:
    """Génère et exécute le SQL pour une sous-question avec validation EXPLAIN + retry borné.

    Boucle bornée par SQL_MAX_RETRIES (D-03) :
    - attempt 1 : génération initiale (_generate_sql)
    - attempts > 1 : re-prompt avec query fautive + erreur DuckDB (_regenerate_sql, D-04)
    - Validation via EXPLAIN avant chaque exec (D-01, D-02)
    - Épuisement → finding d'erreur explicite, jamais de re-raise (D-05)
    - Finding succès étend format Phase 1 avec clé attempts (D-06)
    """
    last_sql: str = ""
    last_error: str = ""

    for attempt in range(1, SQL_MAX_RETRIES + 2):  # 1 initiale + SQL_MAX_RETRIES retries
        # Génération ou re-génération SQL
        if attempt == 1:
            sql = _generate_sql(schema, subquestion)
        else:
            sql = _regenerate_sql(schema, subquestion, bad_sql=last_sql, error=last_error)

        # Validation EXPLAIN (D-01) — parse + résout sans scanner les données
        validation_error = _validate_sql(conn, sql)
        if validation_error is not None:
            last_sql, last_error = sql, validation_error
            continue

        # Exécution sur les données
        try:
            cursor = conn.execute(sql)
            rows = cursor.fetchall()
            columns = [desc[0] for desc in cursor.description] if cursor.description else []
            tables = _extract_tables(sql, schema)
            return {
                "source": "sql_tool",
                "subquestion": subquestion,
                "sql": sql,
                "tables": tables,
                "rows": rows,
                "columns": columns,
                "attempts": attempt,
            }
        except (duckdb.Error, Exception) as exc:  # noqa: BLE001
            last_sql, last_error = sql, str(exc)
            logger.error(
                "sql_tool_node: SQL execution failed — subquestion=%r sql=%r error=%s attempt=%d",
                subquestion,
                sql,
                exc,
                attempt,
            )
            continue

    # Épuisement de tous les retries (D-05) — finding d'erreur, pas de crash
    logger.error(
        "sql_tool_node: all %d attempts exhausted — subquestion=%r last_sql=%r last_error=%s",
        SQL_MAX_RETRIES + 1,
        subquestion,
        last_sql,
        last_error,
    )
    return {
        "source": "sql_tool",
        "subquestion": subquestion,
        "sql": last_sql,
        "error": last_error,
        "attempts": SQL_MAX_RETRIES + 1,
    }


def sql_tool_node(state: AgentState) -> dict:
    """Génère et exécute du SQL pour chaque sous-question du plan.

    Durci (phase 2) : validation EXPLAIN pré-exec + retry borné (SQL_MAX_RETRIES).
    Erreur SQL persistante -> finding d'erreur propre, pas de crash, pas de re-raise.
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


# ---------------------------------------------------------------------------
# stats_tool_node
# ---------------------------------------------------------------------------


def stats_tool_node(state: AgentState) -> dict:
    """Orchestre les fonctions stats pures (corrélation, anomalies) sur les findings SQL.

    Consomme les findings existants (source sql_tool), reconstruit un DataFrame Polars
    depuis rows/columns, calcule corrélation Pearson + détection d'anomalies z-score.

    Données insuffisantes ou non numériques → finding explicit 'insufficient_data' (D-04).
    Pas d'appel LLM, pas d'incrément iterations (router/critic gère ça en Phase 4).

    Retourne {"findings": [...]}, appendé via reducer add.
    """
    existing_findings: list[dict] = state.get("findings", [])
    new_findings: list[dict] = []

    corr_pushed = False
    anomaly_pushed = False

    for f in existing_findings:
        # Ignorer les findings en erreur (pas de rows/columns)
        if "error" in f or "rows" not in f or "columns" not in f:
            continue

        rows = f["rows"]
        columns = f["columns"]

        # Reconstruire un DataFrame Polars (guard: try/except si rows mal formées)
        try:
            df = pl.DataFrame(rows, schema=columns, orient="row")
        except Exception:  # noqa: BLE001
            logger.warning("stats_tool_node: impossible de reconstruire DataFrame depuis finding")
            continue

        if df.height < 2:
            continue

        # Identifier les colonnes numériques
        numeric_cols = [c for c in df.columns if df[c].dtype.is_numeric()]

        # Corrélation sur la première paire numérique
        if len(numeric_cols) >= 2 and not corr_pushed:
            col_a, col_b = numeric_cols[0], numeric_cols[1]
            corr_val = correlation(df, col_a, col_b)
            if corr_val is not None:
                new_findings.append({
                    "source": "stats_tool",
                    "analysis": "correlation",
                    "columns": [col_a, col_b],
                    "value": corr_val,
                })
                corr_pushed = True

        # Détection d'anomalies sur chaque colonne numérique
        for col in numeric_cols:
            anomalies = detect_anomalies(df[col].to_list())
            if anomalies:
                new_findings.append({
                    "source": "stats_tool",
                    "analysis": "anomaly",
                    "column": col,
                    "anomalies": anomalies,
                })
                anomaly_pushed = True

    # Si aucune stat n'a pu être calculée → finding insufficient_data (D-04)
    if not corr_pushed and not anomaly_pushed:
        new_findings.append({
            "source": "stats_tool",
            "analysis": "insufficient_data",
            "detail": "<2 points numériques exploitables ou colonnes non numériques",
        })

    return {"findings": new_findings}


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
