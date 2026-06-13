"""Tests unitaires pour __main__.main() (CLI dataagent).

Stratégie : sys.argv monkeypatché, run() mocké via monkeypatch sur le module importé
dans main() (import différé → patcher dataagent.agent.graph.run).
Vraie I/O absente ici — seul le CLI lui-même est testé.
"""

import sys

import pytest

import dataagent.__main__ as cli_module


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _fake_run_ok(question: str, **_kwargs) -> dict:
    """run() factice qui retourne un rapport normal."""
    return {
        "report": f"## Rapport\n\nRéponse à : {question}",
        "plan": [question],
        "iterations": 1,
        "max_iterations": 5,
        "findings": [{"source": "sql_tool"}],
    }


def _fake_run_raise(question: str, **_kwargs) -> dict:  # noqa: ARG001
    """run() factice qui lève une exception."""
    raise RuntimeError("Erreur simulée du graphe")


# ---------------------------------------------------------------------------
# Tests CLI
# ---------------------------------------------------------------------------


class TestCLIMain:
    """Tests de dataagent.__main__.main()."""

    def test_valid_question_prints_report(self, monkeypatch, capsys):
        """main() avec question valide et run mocké → imprime le report, exit 0."""
        monkeypatch.setenv("GEMINI_API_KEY", "fake-key")
        monkeypatch.setattr(sys, "argv", ["dataagent", "CA total 2017 ?"])

        # Patcher run dans le module graph (import différé dans main())
        import dataagent.agent.graph as graph_mod
        monkeypatch.setattr(graph_mod, "run", _fake_run_ok)

        # main() ne doit pas lever SystemExit (exit 0)
        cli_module.main()

        captured = capsys.readouterr()
        assert "Rapport" in captured.out
        assert "CA total 2017 ?" in captured.out

    def test_missing_argument_exits_nonzero(self, monkeypatch, capsys):
        """main() sans argument positionnel → SystemExit code 1 + message usage sur stderr."""
        monkeypatch.setenv("GEMINI_API_KEY", "fake-key")
        monkeypatch.setattr(sys, "argv", ["dataagent"])

        with pytest.raises(SystemExit) as exc_info:
            cli_module.main()

        assert exc_info.value.code != 0
        captured = capsys.readouterr()
        assert "Usage" in captured.err or "usage" in captured.err.lower()

    def test_missing_api_key_exits_nonzero(self, monkeypatch, capsys):
        """main() sans clé API → SystemExit(1) + message d'erreur sur stderr."""
        monkeypatch.delenv("GEMINI_API_KEY", raising=False)
        monkeypatch.delenv("GOOGLE_API_KEY", raising=False)
        monkeypatch.setattr(sys, "argv", ["dataagent", "CA total ?"])

        with pytest.raises(SystemExit) as exc_info:
            cli_module.main()

        assert exc_info.value.code == 1
        captured = capsys.readouterr()
        assert "GEMINI_API_KEY" in captured.err

    def test_run_raises_exits_nonzero(self, monkeypatch, capsys):
        """main() avec run() qui lève → SystemExit(1) + message d'erreur sur stderr."""
        monkeypatch.setenv("GEMINI_API_KEY", "fake-key")
        monkeypatch.setattr(sys, "argv", ["dataagent", "Question test ?"])

        import dataagent.agent.graph as graph_mod
        monkeypatch.setattr(graph_mod, "run", _fake_run_raise)

        with pytest.raises(SystemExit) as exc_info:
            cli_module.main()

        assert exc_info.value.code == 1
        captured = capsys.readouterr()
        assert "Erreur" in captured.err or "erreur" in captured.err.lower()

    def test_debug_flag_prints_debug_section(self, monkeypatch, capsys):
        """main() avec --debug → bloc DEBUG imprimé sur stderr."""
        monkeypatch.setenv("GEMINI_API_KEY", "fake-key")
        monkeypatch.setattr(sys, "argv", ["dataagent", "CA total ?", "--debug"])

        import dataagent.agent.graph as graph_mod
        monkeypatch.setattr(graph_mod, "run", _fake_run_ok)

        cli_module.main()

        captured = capsys.readouterr()
        assert "DEBUG" in captured.err
        # Les infos de debug doivent mentionner les clés attendues
        assert "plan" in captured.err
        assert "iterations" in captured.err

    def test_google_api_key_accepted(self, monkeypatch, capsys):
        """main() accepte GOOGLE_API_KEY comme alternative à GEMINI_API_KEY."""
        monkeypatch.delenv("GEMINI_API_KEY", raising=False)
        monkeypatch.setenv("GOOGLE_API_KEY", "fake-google-key")
        monkeypatch.setattr(sys, "argv", ["dataagent", "CA total ?"])

        import dataagent.agent.graph as graph_mod
        monkeypatch.setattr(graph_mod, "run", _fake_run_ok)

        # Ne doit pas lever SystemExit
        cli_module.main()
        captured = capsys.readouterr()
        assert "Rapport" in captured.out
