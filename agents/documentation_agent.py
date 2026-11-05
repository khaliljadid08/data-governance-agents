"""Agent de génération du dictionnaire de données."""

from __future__ import annotations

from abc import ABC, abstractmethod
from collections.abc import Mapping
from contextlib import closing
import logging
from pathlib import Path
import sqlite3
from typing import Any

from agents.base_agent import BaseAgent
from agents.gemini_metadata import GeminiMetadataAssistant, MetadataAssistant
from storage import db


logger = logging.getLogger(__name__)


class DescriptionGenerator(ABC):
    """Interface des générateurs de descriptions de colonnes."""

    @abstractmethod
    def generer(
        self, table: str, colonne: str, contexte: Mapping[str, Any]
    ) -> str:
        """Génère une description métier à partir du contexte d'une colonne."""
        raise NotImplementedError


class TemplateDescriptionGenerator(DescriptionGenerator):
    """Génère des descriptions à l'aide de gabarits français déterministes."""

    _TEMPLATES = {
        "client": "Identifiant ou information permettant de décrire un client.",
        "financier": "Information financière utilisée dans les opérations de données.",
        "personnel": "Information à caractère personnel relative à une personne.",
        "produit": "Information décrivant un produit du catalogue.",
        "technique": "Champ technique utilisé pour identifier ou structurer les données.",
    }

    def generer(
        self, table: str, colonne: str, contexte: Mapping[str, Any]
    ) -> str:
        """Compose une phrase à partir de la catégorie et des métadonnées."""
        categorie = str(contexte.get("categorie") or "technique")
        base = self._TEMPLATES.get(categorie, self._TEMPLATES["technique"])
        return (
            f"{base} Colonne « {colonne} » de la table « {table} »."
        )


class GeminiDescriptionGenerator(DescriptionGenerator):
    """Génère les descriptions avec Gemini sans transmettre les valeurs métier."""

    def __init__(
        self,
        api_key: str | None = None,
        model: str = "gemini-3.8-flash",
        assistant: MetadataAssistant | None = None,
    ) -> None:
        """Initialise le générateur avec un assistant partagé ou une clé API."""
        if assistant is None:
            if api_key is None:
                raise ValueError(
                    "Fournissez un assistant Gemini ou une clé GEMINI_API_KEY."
                )
            assistant = GeminiMetadataAssistant(api_key, model)
        self._assistant = assistant

    def generer(
        self, table: str, colonne: str, contexte: Mapping[str, Any]
    ) -> str:
        """Demande une description française à partir des seules métadonnées."""
        metadata = {
            "table": table,
            "colonne": colonne,
            "type_sql": str(contexte.get("type_sql") or ""),
            "categorie": str(contexte.get("categorie") or "technique"),
            "sensibilite": str(contexte.get("sensibilite") or "public"),
        }
        return self._assistant.generer(
            "Rédige une seule phrase concise décrivant cette colonne de dictionnaire. "
            "N'invente aucune règle métier et ne donne aucun exemple de valeur.",
            metadata,
        )


class DocumentationAgent(BaseAgent):
    """Enrichit le dictionnaire avec les analyses réalisées pour un run."""

    def __init__(
        self,
        db_path_governance: str | Path,
        db_path_demo: str | Path,
        description_generator: DescriptionGenerator | None = None,
        gemini_assistant: MetadataAssistant | None = None,
    ) -> None:
        """Initialise l'agent et son générateur de descriptions extensible."""
        super().__init__(
            "documentation",
            db_path_governance,
            db_path_demo,
            gemini_assistant,
        )
        self.description_generator = (
            description_generator or TemplateDescriptionGenerator()
        )

    def analyser(self, run_id: int, perimetre: list[str]) -> dict[str, Any]:
        """Met à jour les entrées du dictionnaire pour chaque colonne du périmètre."""
        with closing(sqlite3.connect(self.db_path_demo)) as demo_connection:
            demo_connection.row_factory = sqlite3.Row
            tables = self._lister_tables(demo_connection)
            self._valider_perimetre(perimetre, tables)
            columns: list[dict[str, str]] = []
            for table in perimetre:
                columns.extend(self._lister_colonnes(demo_connection, table, tables))

        governance_connection = db.get_connection(self.db_path_governance)
        template_generator = TemplateDescriptionGenerator()
        gemini_enabled = isinstance(
            self.description_generator, GeminiDescriptionGenerator
        )
        gemini_available = gemini_enabled
        gemini_error: str | None = None
        gemini_descriptions = 0
        try:
            with governance_connection:
                classification_rows = governance_connection.execute(
                    "SELECT table_name, column_name, categorie FROM classifications "
                    "WHERE run_id = ? ORDER BY id",
                    (run_id,),
                ).fetchall()
                security_rows = governance_connection.execute(
                    "SELECT table_name, column_name, niveau_sensibilite "
                    "FROM security_findings WHERE run_id = ? ORDER BY id",
                    (run_id,),
                ).fetchall()
                categories = {
                    (row["table_name"], row["column_name"]): row["categorie"]
                    for row in classification_rows
                }
                sensitivities = {
                    (row["table_name"], row["column_name"]): row[
                        "niveau_sensibilite"
                    ]
                    for row in security_rows
                }

                for column in columns:
                    table = column["table_name"]
                    name = column["column_name"]
                    category = categories.get((table, name), "technique")
                    sensitivity = sensitivities.get((table, name), "public")
                    context = {
                        "categorie": category,
                        "sensibilite": sensitivity,
                        "run_id": run_id,
                    }
                    if gemini_available:
                        try:
                            description = self.description_generator.generer(
                                table, name, context
                            )
                            gemini_descriptions += 1
                        except Exception as erreur:
                            logger.exception(
                                "Gemini indisponible pour la description de %s.%s.",
                                table,
                                name,
                            )
                            gemini_error = str(erreur)
                            gemini_available = False
                            description = template_generator.generer(
                                table, name, context
                            )
                    elif gemini_enabled:
                        description = template_generator.generer(
                            table, name, context
                        )
                    else:
                        description = self.description_generator.generer(
                            table, name, context
                        )
                    existing = governance_connection.execute(
                        "SELECT id FROM data_dictionary "
                        "WHERE table_name = ? AND column_name = ?",
                        (table, name),
                    ).fetchone()
                    if existing is None:
                        db.insert_data_dictionary_entry(
                            governance_connection,
                            table,
                            name,
                            description,
                            column["type_sql"],
                            category,
                            sensitivity,
                            run_id,
                        )
                    else:
                        governance_connection.execute(
                            "UPDATE data_dictionary SET description = ?, type_sql = ?, "
                            "categorie = ?, sensibilite = ?, derniere_maj = CURRENT_TIMESTAMP, "
                            "run_id = ? WHERE id = ?",
                            (
                                description,
                                column["type_sql"],
                                category,
                                sensitivity,
                                run_id,
                                existing["id"],
                            ),
                        )
        finally:
            governance_connection.close()

        return {
            "resume": f"{len(columns)} entrée(s) documentée(s) ou actualisée(s).",
            "nombre_entrees": len(columns),
            "entrees": columns,
            "source_descriptions": (
                "gabarits_locaux"
                if not gemini_enabled or gemini_descriptions == 0
                else (
                    "gemini"
                    if gemini_descriptions == len(columns)
                    else "gemini_avec_repli_local"
                )
            ),
            **({"gemini_erreur": gemini_error} if gemini_error else {}),
        }

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
        """Valide et cite un identifiant issu des métadonnées SQLite."""
        if table not in tables_autorisees:
            raise ValueError(f"Nom de table non autorisé : {table}")
        return '"' + table.replace('"', '""') + '"'

    @classmethod
    def _lister_colonnes(
        cls,
        connection: sqlite3.Connection,
        table: str,
        tables_autorisees: set[str],
    ) -> list[dict[str, str]]:
        """Lit le nom et le type SQL des colonnes validées par PRAGMA."""
        table_sql = cls._verifier_table(table, tables_autorisees)
        rows = connection.execute(f"PRAGMA table_info({table_sql})").fetchall()
        return [
            {"table_name": table, "column_name": str(row["name"]), "type_sql": str(row["type"] or "")}
            for row in rows
        ]
