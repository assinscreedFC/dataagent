"""Tests des singletons module-level flash_llm / pro_llm (HARD-10, D-11).

Stratégie : patch ChatGoogleGenerativeAI pour éviter toute connexion réseau
ou exigence de clé API. Vérifie l'identité des objets retournés.
"""

from unittest.mock import MagicMock, patch

import pytest


@pytest.fixture(autouse=True)
def reset_llm_singletons():
    """Réinitialise les singletons avant chaque test pour isolation."""
    from dataagent.agent import llm as llm_module

    llm_module._reset_singletons()
    yield
    llm_module._reset_singletons()


class TestFlashLlmSingleton:
    def test_flash_llm_returns_same_object_on_two_calls(self):
        with patch("dataagent.agent.llm.ChatGoogleGenerativeAI") as mock_cls:
            mock_cls.return_value = MagicMock()
            from dataagent.agent.llm import flash_llm

            first = flash_llm()
            second = flash_llm()

            assert first is second

    def test_flash_llm_constructs_once(self):
        with patch("dataagent.agent.llm.ChatGoogleGenerativeAI") as mock_cls:
            mock_cls.return_value = MagicMock()
            from dataagent.agent.llm import flash_llm

            flash_llm()
            flash_llm()
            flash_llm()

            assert mock_cls.call_count == 1


class TestProLlmSingleton:
    def test_pro_llm_returns_same_object_on_two_calls(self):
        with patch("dataagent.agent.llm.ChatGoogleGenerativeAI") as mock_cls:
            mock_cls.return_value = MagicMock()
            from dataagent.agent.llm import pro_llm

            first = pro_llm()
            second = pro_llm()

            assert first is second

    def test_pro_llm_constructs_once(self):
        with patch("dataagent.agent.llm.ChatGoogleGenerativeAI") as mock_cls:
            mock_cls.return_value = MagicMock()
            from dataagent.agent.llm import pro_llm

            pro_llm()
            pro_llm()
            pro_llm()

            assert mock_cls.call_count == 1


class TestFlashProAreDistinct:
    def test_flash_and_pro_are_different_objects(self):
        with patch("dataagent.agent.llm.ChatGoogleGenerativeAI") as mock_cls:
            mock_cls.side_effect = [MagicMock(), MagicMock()]
            from dataagent.agent.llm import flash_llm, pro_llm

            flash = flash_llm()
            pro = pro_llm()

            assert flash is not pro
