"""Runner d'évaluation : score_report + run_eval (D-02, D-03).

Le harness est entièrement testable avec un run_fn mocké (pas de quota Gemini).
Le run live sur les 10 questions réelles est un item manuel (human-verify, D-03).
"""

from typing import Callable

from dataagent.agent.graph import run as _default_run
from dataagent.eval.dataset import QUESTIONS


def score_report(report: str, expected_keywords: list[str]) -> float:
    """Calcule le ratio de mots-clés attendus trouvés dans le rapport.

    La correspondance est insensible à la casse (substring match).

    Args:
        report: Texte du rapport produit par l'agent.
        expected_keywords: Liste de tokens attendus dans le rapport.

    Returns:
        Ratio float en [0.0, 1.0]. Retourne 0.0 si expected_keywords est vide.
    """
    if not expected_keywords:
        return 0.0

    report_lower = report.lower()
    matched = sum(1 for kw in expected_keywords if kw.lower() in report_lower)
    return matched / len(expected_keywords)


def run_eval(
    conn=None,
    run_fn: Callable[..., dict] = _default_run,
) -> dict:
    """Exécute l'eval sur les 10 questions QUESTIONS et retourne les scores.

    Pour chaque question, appelle run_fn(question, conn=conn) et score le rapport
    retourné via score_report. Agrège en moyenne.

    Args:
        conn: Connexion DuckDB (optionnel — None ok si run_fn l'ignore, ex. tests).
        run_fn: Callable(question, conn=...) -> dict avec clé "report": str.
            Par défaut : dataagent.agent.graph.run (injection pour les tests).

    Returns:
        dict avec :
            - "per_question": list[dict] — {question: str, score: float} par question
            - "aggregate": float — moyenne des scores
            - "n": int — nombre de questions évaluées (10)
    """
    per_question: list[dict] = []

    for entry in QUESTIONS:
        question = entry["question"]
        expected_keywords: list[str] = entry["expected_keywords"]

        result = run_fn(question, conn=conn)
        report: str = result.get("report", "")
        score = score_report(report, expected_keywords)

        per_question.append({"question": question, "score": score})

    n = len(per_question)
    aggregate = sum(e["score"] for e in per_question) / n if n > 0 else 0.0

    return {
        "per_question": per_question,
        "aggregate": aggregate,
        "n": n,
    }
