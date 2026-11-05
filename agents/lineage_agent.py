"""Agent de découverte des relations de lignage entre les tables."""

from __future__ import annotations

from contextlib import closing
from pathlib import Path
import sqlite3
from typing import Any

from agents.base_agent import BaseAgent
from agents.gemini_metadata import MetadataAssistant
from storage import db


class LineageAgent(BaseAgent):
    """Enregistre les clés étrangères déclarées et relations déduites."""

    def __init__(
        self,
        db_path_governance: str | Path,
        db_path_demo: str | Path,
        gemini_assistant: MetadataAssistant | None = None,
    ) -> None:
        """Initialise l'agent de lignage."""
        super().__init__(
            "lignage", db_path_governance, db_path_demo, gemini_assistant
        )

    def analyser(self, run_id: int, perimetre: list[str]) -> dict[str, Any]:
        """Découvre et persiste les relations présentes dans le périmètre."""
        with closing(sqlite3.connect(self.db_path_demo)) as demo_connection:
            demo_connection.row_factory = sqlite3.Row
            tables = self._lister_tables(demo_connection)
            self._valider_perimetre(perimetre, tables)
            edges: dict[tuple[str, str, str, str], dict[str, str | None]] = {}

            columns_by_table = {
                table: self._lister_colonnes(demo_connection, table, tables)
                for table in perimetre
            }
            for source_table in perimetre:
                for foreign_key in self._lister_cles_etrangeres(
                    demo_connection, source_table, tables
                ):
                    target_table = foreign_key["table"]
                    target_column = foreign_key["to"]
                    source_column = foreign_key["from"]
                    if (
                        target_table in tables
                        and source_column in columns_by_table[source_table]
                        and target_column in self._lister_colonnes(
                            demo_connection, target_table, tables
                        )
                    ):
                        key = (
                            source_table,
                            source_column,
                            target_table,
                            target_column,
                        )
                        edges[key] = {"type_relation": "fk"}

                for source_column in columns_by_table[source_table]:
                    target = self._deduire_cible(
                        source_column, tables
                    )
                    if target is None:
                        continue
                    target_table, target_column = target
                    key = (
                        source_table,
                        source_column,
                        target_table,
                        target_column,
                    )
                    edges.setdefault(key, {"type_relation": "derive"})

        governance_connection = db.get_connection(self.db_path_governance)
        try:
            with governance_connection:
                for (source_table, source_column, target_table, target_column), edge in (
                    edges.items()
                ):
                    db.insert_lineage_edge(
                        governance_connection,
                        run_id,
                        source_table,
                        source_column,
                        target_table,
                        target_column,
                        str(edge["type_relation"]),
                    )
        finally:
            governance_connection.close()

        serialized_edges = [
            {
                "source_table": source_table,
                "source_column": source_column,
                "target_table": target_table,
                "target_column": target_column,
                **edge,
            }
            for (
                source_table,
                source_column,
                target_table,
                target_column,
            ), edge in edges.items()
        ]
        gemini_advice = self._avis_gemini(
            "Résumer le lignage déduit et expliquer les relations les plus utiles "
            "à vérifier, sans présenter les relations déduites comme des clés "
            "étrangères déclarées.",
            {"nombre_relations": len(edges), "relations": serialized_edges},
        )
        return {
            "resume": f"{len(edges)} relation(s) de lignage identifiée(s).",
            "nombre_relations": len(edges),
            "relations": serialized_edges,
            "avis_gemini": gemini_advice,
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
        """Valide et cite un identifiant de table issu des métadonnées."""
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
        """Récupère les noms et types de colonnes via PRAGMA."""
        table_sql = cls._verifier_table(table, tables_autorisees)
        rows = connection.execute(f"PRAGMA table_info({table_sql})").fetchall()
        return [str(row["name"]) for row in rows]

    @classmethod
    def _lister_cles_etrangeres(
        cls,
        connection: sqlite3.Connection,
        table: str,
        tables_autorisees: set[str],
    ) -> list[sqlite3.Row]:
        """Récupère les clés étrangères après validation de la table source."""
        table_sql = cls._verifier_table(table, tables_autorisees)
        return connection.execute(
            f"PRAGMA foreign_key_list({table_sql})"
        ).fetchall()

    @classmethod
    def _deduire_cible(
        cls,
        colonne: str,
        tables_autorisees: set[str],
    ) -> tuple[str, str] | None:
        """Déduit une cible pour les colonnes du type nom_table_id."""
        if not colonne.casefold().endswith("_id"):
            return None
        prefix = colonne[:-3].casefold()
        candidates = (prefix, f"{prefix}s")
        for candidate in candidates:
            if candidate in tables_autorisees:
                return candidate, "id"
        return None
