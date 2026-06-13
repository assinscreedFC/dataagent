"""Entrypoint CLI : python -m dataagent "question".

Charge .env AVANT les imports dataagent (GEMINI_API_KEY requis à l'import de nodes/llm).
Conforme D-11, GRAPH-06.

Usage :
    python -m dataagent "CA total 2017 ?"
    python -m dataagent "CA total 2017 ?" --debug
"""

import sys

from dotenv import load_dotenv

# Charger .env AVANT tout import dataagent qui lit la clé (D-06)
load_dotenv()


def main() -> None:
    """Parse la question, vérifie la clé API, invoque le graphe, affiche le rapport."""
    import os

    # Récupérer les args non-option (question positionnelle)
    args = [a for a in sys.argv[1:] if not a.startswith("--")]
    debug = "--debug" in sys.argv

    if not args:
        print("Usage : python -m dataagent \"ta question\"", file=sys.stderr)
        print("Exemple : python -m dataagent \"CA total 2017 ?\"", file=sys.stderr)
        sys.exit(1)

    question = args[0]

    # Fail-fast si la clé API est absente (boundaries — D-06)
    api_key = os.environ.get("GEMINI_API_KEY") or os.environ.get("GOOGLE_API_KEY")
    if not api_key:
        print(
            "Erreur : GEMINI_API_KEY manquant dans .env\n"
            "Ajouter GEMINI_API_KEY=<votre_clé> dans le fichier .env à la racine.",
            file=sys.stderr,
        )
        sys.exit(1)

    # Import différé pour que load_dotenv() soit effectif avant que config.py soit lu
    from dataagent.agent.graph import run

    try:
        final = run(question)
    except Exception as exc:  # noqa: BLE001
        print(f"Erreur lors de l'exécution du graphe : {exc}", file=sys.stderr)
        sys.exit(1)

    report = final.get("report", "")
    print(report)

    if debug:
        print("\n--- DEBUG ---", file=sys.stderr)
        print(f"plan         : {final.get('plan')}", file=sys.stderr)
        print(f"iterations   : {final.get('iterations')}", file=sys.stderr)
        print(f"max_iterations: {final.get('max_iterations')}", file=sys.stderr)
        print(f"findings     : {len(final.get('findings', []))} finding(s)", file=sys.stderr)


if __name__ == "__main__":
    main()
