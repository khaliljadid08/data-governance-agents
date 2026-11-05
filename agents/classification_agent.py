"""Agent de classification déterministe des colonnes métier."""

from __future__ import annotations

from collections import Counter
from contextlib import closing
from pathlib import Path
import re
import sqlite3
from typing import Any

from storage import db

from agents.base_agent import BaseAgent
from agents.gemini_metadata import MetadataAssistant


_REGEXES_VALEURS: tuple[tuple[str, re.Pattern[str]], ...] = (
    ("financier", re.compile(r"^[A-Z]{2}\d{2}[A-Z0-9]{11,30}$", re.IGNORECASE)),
    ("personnel", re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")),
    ("personnel", re.compile(r"^\+?\d[\d\s().-]{6,}$")),
    ("personnel", re.compile(r"^\d{4}-\d{2}-\d{2}$")),
)

_MOTS_CLES: tuple[tuple[str, tuple[str, ...]], ...] = (
    (
        "financier",
        ("iban", "montant", "prix", "salaire", "solde", "paiement", "facture"),
    ),
    (
        "personnel",
        ("email", "courriel", "telephone", "téléphone", "naissance", "adresse"),
    ),
    ("produit", ("produit", "libelle", "libellé", "categorie", "catégorie")),
    ("client", ("client", "nom", "ville")),
)


class ClassificationAgent(BaseAgent):
    """Classe chaque colonne selon son nom et un échantillon de ses valeurs."""

    def __init__(
        self,
        db_path_governance: str | Path,
        db_path_demo: str | Path,
        gemini_assistant: MetadataAssistant | None = None,
    ) -> None:
        """Initialise l'agent de classification."""
        super().__init__(
            "classification", db_path_governance, db_path_demo, gemini_assistant
        )

    def analyser(self, run_id: int, perimetre: list[str]) -> dict[str, Any]:
        """Classe et persiste les colonnes des tables du périmètre."""
        with closing(sqlite3.connect(self.db_path_demo)) as demo_connection:
            demo_connection.row_factory = sqlite3.Row
            tables = self._lister_tables(demo_connection)
            self._valider_perimetre(perimetre, tables)

            classifications: list[dict[str, Any]] = []
            for table in perimetre:
                columns = self._lister_colonnes(demo_connection, table, tables)
                for column in columns:
                    values = self._echantillonner(
                        demo_connection, table, column, tables
                    )
                    categorie, confiance = self._classer(column, values)
                    classifications.append(
                        {
                            "table_name": table,
                            "column_name": column,
                            "categorie": categorie,
                            "confiance": confiance,
                        }
                    )

        governance_connection = db.get_connection(self.db_path_governance)
        try:
            with governance_connection:
                for classification in classifications:
                    db.insert_classification(
                        governance_connection,
                        run_id,
                        classification["table_name"],
                        classification["column_name"],
                        classification["categorie"],
                        classification["confiance"],
                    )
        finally:
            governance_connection.close()

        repartition = Counter(item["categorie"] for item in classifications)
        gemini_advice = self._avis_gemini(
            "Commenter ces classifications locales à partir des noms de colonnes, "
            "types SQL et catégories; signaler les catégories qui mériteraient "
            "une revue, sans remplacer les résultats locaux.",
            {
                "classifications": classifications,
                "repartition": dict(repartition),
            },
        )
        return {
            "resume": f"{len(classifications)} colonne(s) classifiée(s).",
            "nombre_colonnes": len(classifications),
            "par_categorie": dict(repartition),
            "classifications": classifications,
            "avis_gemini": gemini_advice,
        }

    @staticmethod
    def _lister_tables(connection: sqlite3.Connection) -> set[str]:
        """Retourne les tables métier disponibles dans la base."""
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
        """Lit les colonnes par les métadonnées SQLite après validation."""
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
        """Lit un échantillon limité de valeurs d'une colonne autorisée."""
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

    @staticmethod
    def _classer(colonne: str, valeurs: list[str]) -> tuple[str, float]:
        """Évalue les indices du nom et des données pour renvoyer une classe."""
        nom = colonne.casefold()
        for categorie, mots_cles in _MOTS_CLES:
            if any(mot in nom for mot in mots_cles):
                confiance = 0.95 if any(mot == nom for mot in mots_cles) else 0.88
                return categorie, confiance

        if nom == "id" or nom.endswith("_id"):
            return ("client", 0.78) if "client" in nom else ("technique", 0.9)

        votes: Counter[str] = Counter()
        for valeur in valeurs:
            for categorie, motif in _REGEXES_VALEURS:
                if motif.fullmatch(valeur):
                    votes[categorie] += 1
                    break

        if votes:
            categorie, nombre = votes.most_common(1)[0]
            confiance = min(0.95, 0.65 + 0.3 * nombre / max(len(valeurs), 1))
            return categorie, round(confiance, 2)

        return "technique", 0.55
