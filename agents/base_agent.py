"""Classe commune aux agents d'analyse de gouvernance."""

from __future__ import annotations

from abc import ABC, abstractmethod
import json
import logging
from pathlib import Path
import sqlite3
from typing import Any

from agents.gemini_metadata import MetadataAssistant
from storage import db


logger = logging.getLogger(__name__)


class BaseAgent(ABC):
    """Définit le cycle d'exécution isolé d'un agent spécialisé."""

    def __init__(
        self,
        nom: str,
        db_path_governance: str | Path,
        db_path_demo: str | Path,
        gemini_assistant: MetadataAssistant | None = None,
    ) -> None:
        """Initialise l'agent avec les chemins des deux bases SQLite."""
        self.nom = nom
        self.db_path_governance = Path(db_path_governance)
        self.db_path_demo = Path(db_path_demo)
        self.gemini_assistant = gemini_assistant

    @abstractmethod
    def analyser(self, run_id: int, perimetre: list[str]) -> dict[str, Any]:
        """Analyse les tables demandées et renvoie ses détails structurés."""
        raise NotImplementedError

    def executer(self, run_id: int, perimetre: list[str]) -> dict[str, Any]:
        """Exécute l'analyse, enregistre son résultat et ne propage pas ses erreurs."""
        statut = "succes"
        details: dict[str, Any]
        try:
            resultat = self.analyser(run_id, perimetre)
            details = resultat if isinstance(resultat, dict) else {"resultat": resultat}
            resume = self._creer_resume(details)
        except Exception as erreur:
            statut = "echec"
            resume = f"Échec de l'agent {self.nom} : {erreur}"
            details = {
                "erreur": str(erreur),
                "type_erreur": type(erreur).__name__,
            }
            logger.exception("Échec de l'analyse de l'agent %s (run_id=%s)", self.nom, run_id)

        try:
            self._enregistrer_resultat(run_id, statut, resume, details)
        except Exception:
            # Une panne d'enregistrement ne doit pas faire échouer le thread superviseur.
            statut = "echec"
            logger.exception(
                "Impossible d'enregistrer le résultat de %s (run_id=%s)",
                self.nom,
                run_id,
            )
            details = {
                **details,
                "erreur_enregistrement": "Échec de l'écriture dans la base de gouvernance.",
            }
            resume = f"Échec de l'enregistrement du résultat de l'agent {self.nom}."

        return {
            "agent": self.nom,
            "statut": statut,
            "resume": resume,
            "details": details,
        }

    @staticmethod
    def _creer_resume(details: dict[str, Any]) -> str:
        """Construit un résumé court à partir des détails fournis par l'agent."""
        resume = details.get("resume")
        if isinstance(resume, str):
            return resume
        return f"Analyse terminée ({len(details)} élément(s) de détail)."

    def _avis_gemini(
        self, objectif: str, metadonnees: dict[str, Any]
    ) -> dict[str, str]:
        """Ajoute un avis Gemini explicite sans bloquer les contrôles déterministes."""
        if self.gemini_assistant is None:
            return {"statut": "desactive"}
        try:
            avis = self.gemini_assistant.generer(objectif, metadonnees)
        except Exception as erreur:
            logger.exception(
                "Gemini n'a pas pu produire l'avis de %s.", self.nom
            )
            return {
                "statut": "echec",
                "erreur": str(erreur),
            }
        return {"statut": "succes", "avis": avis}

    def _enregistrer_resultat(
        self,
        run_id: int,
        statut: str,
        resume: str,
        details: dict[str, Any],
    ) -> None:
        """Écrit le résultat en utilisant une connexion dédiée à cette opération."""
        connection: sqlite3.Connection | None = None
        try:
            connection = db.get_connection(self.db_path_governance)
            with connection:
                db.insert_agent_result(
                    connection,
                    run_id,
                    self.nom,
                    statut,
                    resume,
                    json.dumps(details, ensure_ascii=False),
                )
        finally:
            if connection is not None:
                connection.close()
