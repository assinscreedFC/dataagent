"""Factory LangChain pour les LLM Gemini.

Deux factories selon le rôle (D-06, D-07) :
- flash_llm() : rapide/cheap — planner + génération SQL (gemini-2.0-flash)
- pro_llm()   : qualité rapport — synthesizer (gemini-2.5-pro)

Les noms de modèles viennent de config.py (override possible via env).
La clé API est chargée depuis l'env (GEMINI_API_KEY / GOOGLE_API_KEY).
"""

from langchain_google_genai import ChatGoogleGenerativeAI

from dataagent.config import GEMINI_API_KEY, GEMINI_MODEL_FLASH, GEMINI_MODEL_PRO


def flash_llm() -> ChatGoogleGenerativeAI:
    """LLM rapide/cheap : planner + génération SQL."""
    return ChatGoogleGenerativeAI(
        model=GEMINI_MODEL_FLASH,
        api_key=GEMINI_API_KEY,
        temperature=0,
    )


def pro_llm() -> ChatGoogleGenerativeAI:
    """LLM qualité : synthesizer du rapport."""
    return ChatGoogleGenerativeAI(
        model=GEMINI_MODEL_PRO,
        api_key=GEMINI_API_KEY,
        temperature=0,
    )
