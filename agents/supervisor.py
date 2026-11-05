"""Coordination des agents et cycle de validation humaine."""

from __future__ import annotations

from collections import Counter
from collections.abc import Mapping
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path
import logging
import sqlite3
from typing import Any

from agents.base_agent import BaseAgent
from agents.classification_agent import ClassificationAgent
from agents.documentation_agent import (
    DocumentationAgent,
    GeminiDescriptionGenerator,
)
from agents.gemini_metadata import MetadataAssistant
from agents.lineage_agent import LineageAgent
from agents.quality_agent import QualityAgent
from agents.security_agent import SecurityAgent
from storage import db


logger = logging.getLogger(__name__)

_AGENT_IDS = ("qualite", "classification", "securisation", "lignage")
_ALL_AGENT_IDS = (*_AGENT_IDS, "documentation")
_MOTS_CLES_AGENTS = {
    "qualite": ("qualite", "qualité", "doublon", "manquant", "anomalie"),
    "classification": ("classif", "categorie", "catégorie", "sensibilite", "sensibilité"),
    "securisation": ("securite", "sécurité", "acces", "accès", "sensible", "iban"),
    "lignage": ("lignage", "relation", "dependance", "dépendance", "origine"),
}


class ConsigneIncompleteError(ValueError):
    """Signale une consigne ou un périmètre qui demande une clarification."""


class Supervisor:
    """Reçoit les demandes, coordonne les agents et pilote leur validation."""

    def __init__(
        self,
        db_path_governance: str | Path,
        db_path_demo: str | Path,
        agents: Mapping[str, BaseAgent] | None = None,
        max_workers: int = 4,
        gemini_assistant: MetadataAssistant | None = None,
    ) -> None:
        """Configure les bases, les agents et le nombre de tâches concurrentes."""
        self.db_path_governance = Path(db_path_governance)
        self.db_path_demo = Path(db_path_demo)
        self.gemini_assistant = gemini_assistant
        self._syntheses_gemini: dict[int, dict[str, str]] = {}
        if max_workers < 1:
            raise ValueError("Le nombre de travailleurs doit être positif.")
        self.max_workers = max_workers
        self.agents: dict[str, BaseAgent] = {
            "qualite": QualityAgent(
                self.db_path_governance, self.db_path_demo, gemini_assistant
            ),
            "classification": ClassificationAgent(
                self.db_path_governance, self.db_path_demo, gemini_assistant
            ),
            "securisation": SecurityAgent(
                self.db_path_governance,
                self.db_path_demo,
                gemini_assistant=gemini_assistant,
            ),
            "lignage": LineageAgent(
                self.db_path_governance, self.db_path_demo, gemini_assistant
            ),
            "documentation": DocumentationAgent(
                self.db_path_governance,
                self.db_path_demo,
                GeminiDescriptionGenerator(assistant=gemini_assistant)
                if gemini_assistant is not None
                else None,
                gemini_assistant,
            ),
        }
        if agents:
            self.agents.update(agents)
        if gemini_assistant is not None:
            for agent in self.agents.values():
                if agent.gemini_assistant is None:
                    agent.gemini_assistant = gemini_assistant
        self._agents_actifs_par_requete: dict[int, list[str]] = {}

    def recevoir_consigne(
        self,
        operateur: str,
        consigne: str,
        perimetre: list[str],
        agents_actifs: list[str] | None = None,
    ) -> int:
        """Valide et enregistre la demande d'analyse de l'opérateur."""
        if not isinstance(operateur, str) or not operateur.strip():
            raise ConsigneIncompleteError("Veuillez préciser le nom de l'opérateur.")
        if not isinstance(consigne, str) or not consigne.strip():
            raise ConsigneIncompleteError("Veuillez préciser les objectifs de l'analyse.")
        if (
            not isinstance(perimetre, list)
            or not perimetre
            or any(not isinstance(table, str) or not table.strip() for table in perimetre)
        ):
            raise ConsigneIncompleteError(
                "Veuillez préciser au moins une table à analyser."
            )
        if len(set(perimetre)) != len(perimetre):
            raise ConsigneIncompleteError("Le périmètre contient des tables en doublon.")

        tables = self._lister_tables_demo()
        unknown_tables = [table for table in perimetre if table not in tables]
        if unknown_tables:
            raise ConsigneIncompleteError(
                "Tables introuvables dans la base métier : "
                + ", ".join(unknown_tables)
                + ". Précisez des tables existantes."
            )

        selected = agents_actifs or []
        if any(agent not in _ALL_AGENT_IDS for agent in selected):
            raise ConsigneIncompleteError(
                "Agent inconnu. Choisissez parmi : " + ", ".join(_ALL_AGENT_IDS) + "."
            )

        connection = db.get_connection(self.db_path_governance)
        try:
            with connection:
                request_id = db.insert_request(
                    connection,
                    operateur.strip(),
                    consigne.strip(),
                    ", ".join(perimetre),
                )
                db.insert_audit_log(
                    connection,
                    operateur.strip(),
                    "creation_consigne",
                    "request",
                    request_id,
                )
        finally:
            connection.close()

        if selected:
            self._agents_actifs_par_requete[request_id] = list(dict.fromkeys(selected))
        return request_id

    def analyser_besoin(self, requete: Mapping[str, Any]) -> list[str]:
        """Choisit les agents à partir des agents actifs ou des mots-clés."""
        request_id = int(requete["id"])
        if request_id in self._agents_actifs_par_requete:
            requested = self._agents_actifs_par_requete[request_id]
            selected = [agent for agent in requested if agent in _AGENT_IDS]
        else:
            consigne = str(requete["consigne"]).casefold()
            selected = [
                agent
                for agent, keywords in _MOTS_CLES_AGENTS.items()
                if any(keyword in consigne for keyword in keywords)
            ]
            if not selected:
                selected = list(_AGENT_IDS)
        return selected

    def coordonner(self, request_id: int) -> dict[str, Any]:
        """Crée un run, exécute les agents et consolide les résultats."""
        connection = db.get_connection(self.db_path_governance)
        try:
            with connection:
                request = db.get_request(connection, request_id)
                if request is None:
                    raise LookupError(f"La demande {request_id} n'existe pas.")
                if request["statut"] in ("valide", "a_valider", "en_cours"):
                    raise ValueError(
                        f"La demande {request_id} ne peut pas être relancée dans son état actuel."
                    )
                previous = connection.execute(
                    "SELECT MAX(numero_iteration) FROM runs WHERE request_id = ?",
                    (request_id,),
                ).fetchone()[0]
                iteration = int(previous or 0) + 1
                run_id = db.insert_run(connection, request_id, iteration)
                connection.execute(
                    "UPDATE requests SET statut = 'en_cours' WHERE id = ?",
                    (request_id,),
                )
                db.insert_audit_log(
                    connection, "superviseur", "creation_run", "run", run_id
                )
                request_data = dict(request)
                request_data["statut"] = "en_cours"
        finally:
            connection.close()

        perimetre = [
            table.strip()
            for table in str(request_data["perimetre"]).split(",")
            if table.strip()
        ]
        selected = self.analyser_besoin(request_data)
        agent_results: list[dict[str, Any]] = []
        futures = {}
        with ThreadPoolExecutor(max_workers=self.max_workers) as executor:
            for agent_id in selected:
                agent = self.agents[agent_id]
                futures[
                    executor.submit(agent.executer, run_id, perimetre)
                ] = agent_id
            for future in as_completed(futures):
                agent_id = futures[future]
                try:
                    agent_results.append(future.result())
                except Exception as erreur:
                    logger.exception(
                        "Erreur non interceptée de l'agent %s pour le run %s",
                        agent_id,
                        run_id,
                    )
                    agent_results.append(
                        {
                            "agent": agent_id,
                            "statut": "echec",
                            "resume": str(erreur),
                            "details": {"type_erreur": type(erreur).__name__},
                        }
                    )

        documentation_result = self.agents["documentation"].executer(
            run_id, perimetre
        )
        agent_results.append(documentation_result)
        report = self.consolider(run_id)
        report["run_id"] = run_id
        report["numero_iteration"] = iteration
        report["agents_execution"] = agent_results
        return report

    def consolider(self, run_id: int) -> dict[str, Any]:
        """Construit un rapport des résultats, anomalies et non-conformités."""
        connection = db.get_connection(self.db_path_governance)
        try:
            results = connection.execute(
                "SELECT agent, statut FROM agent_results WHERE run_id = ? ORDER BY id",
                (run_id,),
            ).fetchall()
            issues = connection.execute(
                "SELECT table_name, column_name, type_anomalie, severite, "
                "nb_lignes, exemple FROM quality_issues WHERE run_id = ? "
                "AND severite = ? ORDER BY id",
                (run_id, "critique"),
            ).fetchall()
            findings = connection.execute(
                "SELECT table_name, column_name, niveau_sensibilite, type_donnee, "
                "recommandation FROM security_findings WHERE run_id = ? "
                "AND conforme_regle_acces = ? ORDER BY id",
                (run_id, 0),
            ).fetchall()
            db.insert_audit_log(
                connection, "superviseur", "consolidation", "run", run_id
            )
            connection.commit()
        finally:
            connection.close()

        counts = Counter(row["agent"] for row in results)
        status_counts = Counter(row["statut"] for row in results)
        if self.gemini_assistant is None:
            synthesis = {"statut": "desactive"}
        elif run_id in self._syntheses_gemini:
            synthesis = self._syntheses_gemini[run_id]
        else:
            metadata = {
                "statuts_agents": dict(status_counts),
                "anomalies_critiques": [
                    {
                        "table": issue["table_name"],
                        "colonne": issue["column_name"],
                        "type": issue["type_anomalie"],
                        "severite": issue["severite"],
                        "nombre_lignes": issue["nb_lignes"],
                    }
                    for issue in issues
                ],
                "colonnes_sensibles_non_conformes": [
                    {
                        "table": finding["table_name"],
                        "colonne": finding["column_name"],
                        "sensibilite": finding["niveau_sensibilite"],
                        "type_donnee": finding["type_donnee"],
                    }
                    for finding in findings
                ],
            }
            try:
                synthesis = {
                    "statut": "succes",
                    "avis": self.gemini_assistant.generer(
                        "Rédige une synthèse consultative des résultats agrégés "
                        "et des points à vérifier par le réviseur. Ne décide jamais "
                        "de la validation du run.",
                        metadata,
                    ),
                }
            except Exception as erreur:
                logger.exception(
                    "Gemini n'a pas pu produire la synthèse du run %s.", run_id
                )
                synthesis = {"statut": "echec", "erreur": str(erreur)}
            self._syntheses_gemini[run_id] = synthesis
        return {
            "compteurs_par_agent": dict(counts),
            "statuts_agents": dict(status_counts),
            "anomalies_critiques": [dict(row) for row in issues],
            "colonnes_sensibles_non_conformes": [dict(row) for row in findings],
            "synthese_gemini": synthesis,
        }

    def soumettre_a_validation(self, run_id: int) -> None:
        """Soumet le run à validation via l'API du stockage."""
        db.submit_for_validation(run_id, self.db_path_governance)

    def traiter_decision(
        self,
        run_id: int,
        reviewer: str,
        role: str,
        decision: str,
        commentaire: str | None,
    ) -> int:
        """Enregistre le verdict du réviseur et son commentaire."""
        return db.validate_run(
            run_id,
            reviewer,
            decision,
            commentaire,
            db_path=self.db_path_governance,
            role=role,
        )

    def re_coordonner(self, request_id: int) -> dict[str, Any]:
        """Relance un run rejeté après avoir ajouté le commentaire au contexte."""
        connection = db.get_connection(self.db_path_governance)
        try:
            with connection:
                request = db.get_request(connection, request_id)
                if request is None:
                    raise LookupError(f"La demande {request_id} n'existe pas.")
                validation = connection.execute(
                    "SELECT decision, commentaire FROM validations "
                    "JOIN runs ON runs.id = validations.run_id "
                    "WHERE runs.request_id = ? ORDER BY validations.id DESC LIMIT ?",
                    (request_id, 1),
                ).fetchone()
                if validation is None or validation["decision"] != "rejete":
                    raise ValueError(
                        "La re-coordination nécessite une dernière décision de rejet."
                    )
                comment = validation["commentaire"]
                if comment and comment.strip():
                    connection.execute(
                        "UPDATE requests SET consigne = consigne || ? WHERE id = ?",
                        (
                            "\nRetour de validation précédent : " + comment.strip(),
                            request_id,
                        ),
                    )
                db.insert_audit_log(
                    connection,
                    "superviseur",
                    "re_coordination",
                    "request",
                    request_id,
                )
        finally:
            connection.close()
        return self.coordonner(request_id)

    def _lister_tables_demo(self) -> set[str]:
        """Récupère les tables métier disponibles pour valider les périmètres."""
        connection = sqlite3.connect(self.db_path_demo)
        try:
            rows = connection.execute(
                "SELECT name FROM sqlite_master WHERE type = 'table' "
                "AND name NOT LIKE 'sqlite_%'"
            ).fetchall()
            return {str(row[0]) for row in rows}
        finally:
            connection.close()
