"""Constantes et chemins du projet."""

from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[2]
DATA_RAW = PROJECT_ROOT / "data" / "raw"
REPORTS = PROJECT_ROOT / "reports"

DEFAULT_TOP_N = 10
MAX_ITERATIONS = 5
