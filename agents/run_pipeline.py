"""Exécute un scénario complet du système de gouvernance en ligne de commande."""

from __future__ import annotations

import argparse
import os
from pathlib import Path

from agents.gemini_metadata import GeminiMetadataAssistant
from agents.supervisor import Supervisor
from storage import db
from storage.seed_demo_data import create_demo_data


def main() -> None:
    """Lance les agents sur le jeu démo puis simule une validation humaine."""
    project_root = Path(__file__).resolve().parent.parent
    storage_dir = project_root / "storage"
    parser = argparse.ArgumentParser(
        description="Exécuter le pipeline de gouvernance sur les données de démonstration."
    )
    parser.add_argument("--operateur", default="Opérateur démo")
    parser.add_argument(
        "--decision",
        choices=("valide", "rejete"),
        default="valide",
        help="Décision simulée du Data Steward.",
    )
    parser.add_argument(
        "--commentaire",
        default="Validation simulée du scénario de démonstration.",
    )
    args = parser.parse_args()

    governance_path = storage_dir / "governance.db"
    demo_path = storage_dir / "demo_data.db"
    storage_dir.mkdir(parents=True, exist_ok=True)
    db.init_db(governance_path)
    if not demo_path.exists():
        create_demo_data(demo_path)

    gemini_enabled = os.environ.get("GEMINI_ENABLED", "false").casefold() == "true"
    gemini_api_key = os.environ.get("GEMINI_API_KEY", "").strip()
    if gemini_enabled and not gemini_api_key:
        raise SystemExit("GEMINI_ENABLED=true nécessite GEMINI_API_KEY.")
    gemini_assistant = (
        GeminiMetadataAssistant(
            gemini_api_key,
            os.environ.get("GEMINI_MODEL", "gemini-3.8-flash"),
        )
        if gemini_enabled
        else None
    )
    supervisor = Supervisor(
        governance_path,
        demo_path,
        gemini_assistant=gemini_assistant,
    )
    request_id = supervisor.recevoir_consigne(
        args.operateur,
        "Analyser la qualité, la classification, la sécurité et le lignage "
        "des données de démonstration.",
        ["clients", "commandes", "produits"],
    )
    report = supervisor.coordonner(request_id)
    supervisor.soumettre_a_validation(report["run_id"])
    supervisor.traiter_decision(
        report["run_id"],
        "Data Steward démo",
        "data_steward",
        args.decision,
        args.commentaire,
    )

    print(f"Demande : {request_id}")
    print(f"Run : {report['run_id']} (itération {report['numero_iteration']})")
    print(f"Décision simulée : {args.decision}")
    print("Résultats des agents :")
    for agent_result in report["agents_execution"]:
        print(
            f"- {agent_result['agent']} : {agent_result['statut']} — "
            f"{agent_result['resume']}"
        )
        details = agent_result.get("details", {})
        gemini_advice = details.get("avis_gemini")
        if gemini_advice and gemini_advice["statut"] == "echec":
            print(f"  Avis Gemini indisponible : {gemini_advice['erreur']}")
        if details.get("gemini_erreur"):
            print(f"  Descriptions Gemini indisponibles : {details['gemini_erreur']}")
    print(f"Anomalies critiques : {len(report['anomalies_critiques'])}")
    print(
        "Colonnes sensibles non conformes : "
        f"{len(report['colonnes_sensibles_non_conformes'])}"
    )
    synthesis = report["synthese_gemini"]
    if synthesis["statut"] == "succes":
        print(f"Avis Gemini (consultatif) : {synthesis['avis']}")
    elif synthesis["statut"] == "echec":
        print(f"Avis Gemini indisponible : {synthesis['erreur']}")


if __name__ == "__main__":
    main()
