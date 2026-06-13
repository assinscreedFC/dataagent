"""Constantes et chemins du projet."""

import os
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[2]
DATA_RAW = PROJECT_ROOT / "data" / "raw"
REPORTS = PROJECT_ROOT / "reports"

DEFAULT_TOP_N = 10
MAX_ITERATIONS = 5  # garde-fou coût boucle critic (J4)
SQL_MAX_RETRIES = 2  # garde-fou retry intra-tool sql (D-03), distinct de MAX_ITERATIONS (critic loop)
ANOMALY_Z_THRESHOLD = 3.0  # |z| > seuil => anomalie (D-03)

# Modèles Gemini — override possible via variables d'environnement (D-07)
# NB: gemini-2.0-flash et gemini-2.5-pro renvoient 429 (free tier limit:0) sur la clé
# actuelle. Seul gemini-2.5-flash a du quota → utilisé pour planner ET synthesizer.
# Repasser PRO sur gemini-2.5-pro quand le billing Gemini sera activé.
GEMINI_MODEL_FLASH = os.environ.get("GEMINI_MODEL_FLASH", "gemini-2.5-flash")
GEMINI_MODEL_PRO = os.environ.get("GEMINI_MODEL_PRO", "gemini-2.5-flash")

# Clé API Gemini — chargée depuis l'env/.env (D-06)
GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY") or os.environ.get("GOOGLE_API_KEY")
