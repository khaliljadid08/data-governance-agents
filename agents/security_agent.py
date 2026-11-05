"""Agent de détection des champs sensibles et de contrôle d'accès."""

from __future__ import annotations

from collections.abc import Mapping
from contextlib import closing
import json
from pathlib import Path
import re
import sqlite3
from typing import Any

from agents.base_agent import BaseAgent
from agents.gemini_metadata import MetadataAssistant
from storage import db


_DEFAULT_RULES_PATH = Path(__file__).with_name("config") / "access_rules.json"


class SecurityAgent(BaseAgent):
    """Repère les données sensibles et vérifie leur conformité aux règles."""

    def __init__(
        self,
        db_path_governance: str | Path,
        db_path_demo: str | Path,
        access_rules_path: str | Path | None = None,
        gemini_assistant: MetadataAssistant | None = None,
    ) -> None:
        """Initialise l'agent avec le fichier JSON de règles d'accès."""
        super().__init__(
            "securisation", db_path_governance, db_path_demo, gemini_assistant
        )
        self.access_rules_path = Path(access_rules_path or _DEFAULT_RULES_PATH)

    def analyser(self, run_id: int, perimetre: list[str]) -> dict[str, Any]:
        """Identifie les colonnes sensibles et persiste les constats de sécurité."""
        rules = self._charger_regles()
        with closing(sqlite3.connect(self.db_path_demo)) as demo_connection:
            demo_connection.row_factory = sqlite3.Row
            tables = self._lister_tables(demo_connection)
            self._valider_perimetre(perimetre, tables)
            findings: list[dict[str, Any]] = []

            for table in perimetre:
                for column in self._lister_colonnes(demo_connection, table, tables):
                    policy = self._trouver_regle(column, rules)
                    if policy is None:
                        continue
                    values = self._echantillonner(
                        demo_connection, table, column, tables
                    )
                    masked_pattern = policy.get("masque_regex")
                    exposed_in_clear = bool(values) and not (
                        isinstance(masked_pattern, str)
                        and all(
                            re.fullmatch(masked_pattern, value) is not None
                            for value in values
                        )
                    )
                    complies = not (
                        policy.get("expose_en_clair") is False and exposed_in_clear
                    )
                    recommendation = policy.get("recommandation", "")
                    if not complies:
                        recommendation = (
                            f"{recommendation} Masquer les valeurs et limiter les accès."
                        ).strip()
                    findings.append(
                        {
                            "table_name": table,
                            "column_name": column,
                            "niveau_sensibilite": policy["niveau_sensibilite"],
                            "type_donnee": policy["type_donnee"],
                            "conforme_regle_acces": complies,
                            "recommandation": recommendation,
                            "valeurs_en_clair_detectees": exposed_in_clear,
                        }
                    )

        governance_connection = db.get_connection(self.db_path_governance)
        try:
            with governance_connection:
                for finding in findings:
                    db.insert_security_finding(
                        governance_connection,
                        run_id,
                        finding["table_name"],
                        finding["column_name"],
                        finding["niveau_sensibilite"],
                        finding["type_donnee"],
                        finding["conforme_regle_acces"],
                        finding["recommandation"],
                    )
        finally:
            governance_connection.close()

        non_compliant = sum(
            not finding["conforme_regle_acces"] for finding in findings
        )
        gemini_advice = self._avis_gemini(
            "Expliquer les constats de sécurité agrégés et proposer des pistes "
            "de remédiation. Les règles locales déterminent seules la conformité; "
            "ne prétends pas qu'une recommandation modifie cette décision.",
            {
                "nombre_constats": len(findings),
                "non_conformes": non_compliant,
                "constats": [
                    {
                        "table": finding["table_name"],
                        "colonne": finding["column_name"],
                        "type_donnee": finding["type_donnee"],
                        "sensibilite": finding["niveau_sensibilite"],
                        "conforme": finding["conforme_regle_acces"],
                    }
                    for finding in findings
                ],
            },
        )
        return {
            "resume": f"{len(findings)} colonne(s) sensible(s) examinée(s).",
            "nombre_constats": len(findings),
            "non_conformes": non_compliant,
            "constats": findings,
            "avis_gemini": gemini_advice,
        }

    @staticmethod
    def _charger_regles_depuis_fichier(path: Path) -> dict[str, Any]:
        """Charge et valide la structure générale du fichier de règles."""
        with path.open(encoding="utf-8") as file:
            rules = json.load(file)
        if not isinstance(rules, dict) or not isinstance(rules.get("regles"), list):
            raise ValueError("Le fichier de règles doit contenir une liste 'regles'.")
        for rule in rules["regles"]:
            if not isinstance(rule, dict):
                raise ValueError("Chaque règle de sécurité doit être un objet JSON.")
            if rule.get("niveau_sensibilite") not in (
                "public",
                "interne",
                "confidentiel",
                "sensible",
            ):
                raise ValueError("Une règle contient un niveau de sensibilité invalide.")
            if not isinstance(rule.get("type_donnee"), str):
                raise ValueError("Chaque règle doit déclarer un type de donnée.")
        return rules

    def _charger_regles(self) -> dict[str, Any]:
        """Charge le fichier de règles associé à l'agent."""
        return self._charger_regles_depuis_fichier(self.access_rules_path)

    @staticmethod
    def _trouver_regle(
        colonne: str, rules: Mapping[str, Any]
    ) -> dict[str, Any] | None:
        """Sélectionne la règle la plus spécifique correspondant au nom."""
        normalised_column = colonne.casefold()
        for rule in rules["regles"]:
            keywords = rule.get("mots_cles", [])
            if not isinstance(keywords, list):
                raise ValueError("Les mots-clés d'une règle doivent être une liste.")
            if any(
                isinstance(keyword, str)
                and keyword.casefold() in normalised_column
                for keyword in keywords
            ):
                return rule
        return None

    @staticmethod
    def _lister_tables(connection: sqlite3.Connection) -> set[str]:
        """Retourne les tables métier disponibles dans la base démo."""
        rows = connection.execute(
            "SELECT name FROM sqlite_master WHERE type = 'table' "
            "AND name NOT LIKE 'sqlite_%'"
        ).fetchall()
        return {str(row["name"]) for row in rows}

    @staticmethod
    def _valider_perimetre(perimetre: list[str], tables_autorisees: set[str]) -> None:
        """Vérifie que le périmètre contient uniquement des tables disponibles."""
        if not perimetre:
            raise ValueError("Le périmètre d'analyse ne contient aucune table.")
        if any(table not in tables_autorisees for table in perimetre):
            raise ValueError("Le périmètre contient une table absente de la base métier.")

    @staticmethod
    def _verifier_table(table: str, tables_autorisees: set[str]) -> str:
        """Vérifie un nom de table puis le protège comme identifiant SQL."""
        if table not in tables_autorisees:
            raise ValueError(f"Nom de table non autorisé : {table}")
        return '"' + table.replace('"', '""') + '"'

    @classmethod
    def _lister_colonnes(
        cls,
        connection: sqlite3.Connection,
        table: str,
        tables_autorisees: set[str],
    ) -> list[str]:
        """Récupère les colonnes par PRAGMA après validation de la table."""
        table_sql = cls._verifier_table(table, tables_autorisees)
        rows = connection.execute(f"PRAGMA table_info({table_sql})").fetchall()
        return [str(row["name"]) for row in rows]

    @classmethod
    def _echantillonner(
        cls,
        connection: sqlite3.Connection,
        table: str,
        colonne: str,
        tables_autorisees: set[str],
    ) -> list[str]:
        """Lit un échantillon de valeurs depuis des identifiants validés."""
        table_sql = cls._verifier_table(table, tables_autorisees)
        colonnes_autorisees = set(cls._lister_colonnes(connection, table, tables_autorisees))
        if colonne not in colonnes_autorisees:
            raise ValueError(f"Nom de colonne non autorisé : {colonne}")
        colonne_sql = '"' + colonne.replace('"', '""') + '"'
        rows = connection.execute(
            f"SELECT {colonne_sql} FROM {table_sql} "
            f"WHERE {colonne_sql} IS NOT NULL LIMIT ?",
            (100,),
        ).fetchall()
        return [str(row[0]).strip() for row in rows if str(row[0]).strip()]
