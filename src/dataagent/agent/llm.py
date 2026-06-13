"""Factory LangChain pour les LLM Gemini.

Deux factories selon le rôle (D-06, D-07) :
- flash_llm() : rapide/cheap — planner + génération SQL (gemini-2.0-flash)
- pro_llm()   : qualité rapport — synthesizer (gemini-2.5-pro)

Les noms de modèles viennent de config.py (override possible via env).
La clé API est chargée depuis l'env (GEMINI_API_KEY / GOOGLE_API_KEY).

Singletons module-level (D-11, HARD-10) : l'instance est créée au 1er appel
et réutilisée pour tous les appels suivants — évite ~30 ré-instanciations/run.
Les tests qui monkeypatchent flash_llm/pro_llm restent valides (ils remplacent
la fonction, pas le cache).
"""

from __future__ import annotations

from langchain_google_genai import ChatGoogleGenerativeAI

from dataagent.config import GEMINI_API_KEY, GEMINI_MODEL_FLASH, GEMINI_MODEL_PRO

_flash: ChatGoogleGenerativeAI | None = None
_pro: ChatGoogleGenerativeAI | None = None


def flash_llm() -> ChatGoogleGenerativeAI:
    """LLM rapide/cheap : planner + génération SQL (singleton module-level)."""
    global _flash
    if _flash is None:
        _flash = ChatGoogleGenerativeAI(
            model=GEMINI_MODEL_FLASH,
            api_key=GEMINI_API_KEY,
            temperature=0,
        )
    return _flash


def pro_llm() -> ChatGoogleGenerativeAI:
    """LLM qualité : synthesizer du rapport (singleton module-level)."""
    global _pro
    if _pro is None:
        _pro = ChatGoogleGenerativeAI(
            model=GEMINI_MODEL_PRO,
            api_key=GEMINI_API_KEY,
            temperature=0,
        )
    return _pro


def _reset_singletons() -> None:
    """Réinitialise les singletons — réservé aux tests qui en ont besoin."""
    global _flash, _pro
    _flash = None
    _pro = None
