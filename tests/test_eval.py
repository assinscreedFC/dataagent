"""Tests du harness eval : score_report + run_eval avec run_fn mocké (D-03 — zéro quota).

Stratégie : runner.py exporte score_report + run_eval(conn, run_fn).
Les tests remplacent run_fn par un lambda deterministe — aucun appel Gemini.
"""

import pytest

from dataagent.eval.dataset import QUESTIONS


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _fake_run_fn(report_text: str):
    """Retourne un run_fn qui ignore la question et renvoie toujours report_text."""
    return lambda question, conn=None: {"report": report_text}


# ---------------------------------------------------------------------------
# Tests dataset
# ---------------------------------------------------------------------------


def test_dataset_has_10_questions():
    assert len(QUESTIONS) == 10


def test_dataset_entries_well_formed():
    for entry in QUESTIONS:
        assert isinstance(entry["question"], str) and entry["question"]
        assert isinstance(entry["expected_keywords"], list)
        assert len(entry["expected_keywords"]) >= 1
        for kw in entry["expected_keywords"]:
            assert isinstance(kw, str) and kw


# ---------------------------------------------------------------------------
# Tests score_report
# ---------------------------------------------------------------------------


def test_score_report_all_present():
    from dataagent.eval.runner import score_report

    report = "Chiffre d'affaires order_items price 2017 mois"
    kws = ["chiffre", "order_items", "price", "2017", "mois"]
    assert score_report(report, kws) == pytest.approx(1.0)


def test_score_report_none_present():
    from dataagent.eval.runner import score_report

    report = "quelque chose de complètement différent"
    kws = ["chiffre", "order_items", "price"]
    assert score_report(report, kws) == pytest.approx(0.0)


def test_score_report_half_present():
    from dataagent.eval.runner import score_report

    report = "chiffre order_items absent-key-xyz"
    kws = ["chiffre", "order_items", "completelymissing", "alsoabsent"]
    assert score_report(report, kws) == pytest.approx(0.5)


def test_score_report_case_insensitive():
    from dataagent.eval.runner import score_report

    report = "CHIFFRE ORDER_ITEMS PRICE"
    kws = ["chiffre", "order_items", "price"]
    assert score_report(report, kws) == pytest.approx(1.0)


def test_score_report_empty_keywords_no_division_error():
    from dataagent.eval.runner import score_report

    # Doit retourner 0.0 (ou 1.0) sans lever ZeroDivisionError
    result = score_report("rapport quelconque", [])
    assert isinstance(result, float)
    assert result == 0.0 or result == 1.0


def test_score_report_single_keyword_found():
    from dataagent.eval.runner import score_report

    assert score_report("livraison rapide", ["livraison"]) == pytest.approx(1.0)


def test_score_report_single_keyword_missing():
    from dataagent.eval.runner import score_report

    assert score_report("rapport sans rien", ["livraison"]) == pytest.approx(0.0)


# ---------------------------------------------------------------------------
# Tests run_eval (run_fn mocké — zéro quota Gemini)
# ---------------------------------------------------------------------------


def test_run_eval_structure():
    """run_eval retourne {"per_question": list, "aggregate": float, "n": int}."""
    from dataagent.eval.runner import run_eval

    # Rapport qui contient au moins un mot-clé de chaque question => score > 0
    fake_report = (
        "chiffre order_items price 2017 mois catégorie product_category revenus top "
        "livraison orders jours état customer retard review_score corrélation "
        "score review produit moyen vendeur seller commandes volume "
        "fret freight_value annulée canceled livrée delivered proportion "
        "client géographique distribution quantité achetés"
    )
    result = run_eval(conn=None, run_fn=_fake_run_fn(fake_report))

    assert "per_question" in result
    assert "aggregate" in result
    assert "n" in result
    assert result["n"] == 10
    assert len(result["per_question"]) == 10


def test_run_eval_per_question_has_question_and_score():
    from dataagent.eval.runner import run_eval

    fake_report = "chiffre order_items price 2017 mois"
    result = run_eval(conn=None, run_fn=_fake_run_fn(fake_report))

    for entry in result["per_question"]:
        assert "question" in entry
        assert "score" in entry
        assert isinstance(entry["score"], float)
        assert 0.0 <= entry["score"] <= 1.0


def test_run_eval_aggregate_is_mean():
    """aggregate == mean(per_question scores)."""
    from dataagent.eval.runner import run_eval

    fake_report = "chiffre order_items price 2017 mois"
    result = run_eval(conn=None, run_fn=_fake_run_fn(fake_report))

    scores = [e["score"] for e in result["per_question"]]
    expected_mean = sum(scores) / len(scores)
    assert result["aggregate"] == pytest.approx(expected_mean)


def test_run_eval_perfect_score():
    """Rapport contenant tous les mots-clés => aggregate == 1.0."""
    from dataagent.eval.runner import run_eval

    # Tous les expected_keywords de toutes les questions
    all_kws = set()
    for q in QUESTIONS:
        all_kws.update(q["expected_keywords"])
    fake_report = " ".join(all_kws)

    result = run_eval(conn=None, run_fn=_fake_run_fn(fake_report))
    assert result["aggregate"] == pytest.approx(1.0)


def test_run_eval_zero_score():
    """Rapport vide => aggregate == 0.0."""
    from dataagent.eval.runner import run_eval

    result = run_eval(conn=None, run_fn=_fake_run_fn(""))
    assert result["aggregate"] == pytest.approx(0.0)


def test_run_eval_no_real_agent_called():
    """Le fake run_fn est appelé 10 fois, jamais le vrai run()."""
    from dataagent.eval.runner import run_eval

    call_count = {"n": 0}

    def counting_fake(question, conn=None):
        call_count["n"] += 1
        return {"report": "chiffre order_items"}

    result = run_eval(conn=None, run_fn=counting_fake)
    assert call_count["n"] == 10
    assert result["n"] == 10
