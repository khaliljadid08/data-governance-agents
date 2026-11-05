"""Agent de détection des anomalies de qualité des données."""

from __future__ import annotations

from collections import Counter
from contextlib import closing
from datetime import date
from pathlib import Path
import re
import sqlite3
from typing import Any

from storage import db

from agents.base_agent import BaseAgent
from agents.gemini_metadata import MetadataAssistant


_EMAIL_PATTERN = re.compile(r"^[A-Za-z0-9.!#$%&'*+/=?^_`{|}~-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}$")
_DUPLICATE_KEYS = {"clients": ("email", "nom")}


class QualityAgent(BaseAgent):
    """Repère les valeurs manquantes et incohérences courantes des données."""

    def __init__(
        self,
        db_path_governance: str | Path,
        db_path_demo: str | Path,
        gemini_assistant: MetadataAssistant | None = None,
    ) -> None:
        """Initialise l'agent qualité avec les chemins des bases."""
        super().__init__(
            "qualite", db_path_governance, db_path_demo, gemini_assistant
        )

    def analyser(self, run_id: int, perimetre: list[str]) -> dict[str, Any]:
        """Analyse les tables du périmètre et persiste les anomalies détectées."""
        with closing(sqlite3.connect(self.db_path_demo)) as demo_connection:
            demo_connection.row_factory = sqlite3.Row
            tables = self._lister_tables(demo_connection)
            if not perimetre:
                raise ValueError("Le périmètre d'analyse ne contient aucune table.")
            if any(table not in tables for table in perimetre):
                raise ValueError("Le périmètre contient une table absente de la base métier.")

            issues: list[dict[str, Any]] = []
            loaded_rows: dict[str, list[sqlite3.Row]] = {}
            columns_by_table: dict[str, list[str]] = {}

            for table in perimetre:
                columns = self._lister_colonnes(demo_connection, table, tables)
                columns_by_table[table] = columns
                rows = self._lire_lignes(demo_connection, table, tables)
                loaded_rows[table] = rows
                issues.extend(self._detecter_valeurs_manquantes(table, columns, rows))
                issues.extend(self._detecter_doublons(table, columns, rows))
                issues.extend(self._detecter_emails_invalides(table, columns, rows))
                issues.extend(self._detecter_montants_negatifs(table, columns, rows))
                issues.extend(self._detecter_dates_incoherentes(table, columns, rows))

            if "commandes" in loaded_rows and "clients" in loaded_rows:
                issues.extend(
                    self._detecter_commandes_orphelines(
                        loaded_rows["commandes"],
                        columns_by_table["commandes"],
                        loaded_rows["clients"],
                        columns_by_table["clients"],
                    )
                )
                issues.extend(
                    self._detecter_dates_commande_avant_naissance(
                        loaded_rows["commandes"],
                        columns_by_table["commandes"],
                        loaded_rows["clients"],
                        columns_by_table["clients"],
                    )
                )

        governance_connection = db.get_connection(self.db_path_governance)
        try:
            with governance_connection:
                for issue in issues:
                    db.insert_quality_issue(
                        governance_connection,
                        run_id,
                        issue["table_name"],
                        issue["column_name"],
                        issue["type_anomalie"],
                        issue["severite"],
                        issue["nb_lignes"],
                        issue["exemple"],
                    )
        finally:
            governance_connection.close()

        counts = Counter(issue["type_anomalie"] for issue in issues)
        gemini_advice = self._avis_gemini(
            "Expliquer les catégories d'anomalies observées et suggérer des pistes "
            "de remédiation générales, sans changer leur sévérité.",
            {
                "nombre_anomalies": len(issues),
                "par_type": dict(counts),
                "anomalies": [
                    {
                        "table": issue["table_name"],
                        "colonne": issue["column_name"],
                        "type": issue["type_anomalie"],
                        "severite": issue["severite"],
                        "nombre_lignes": issue["nb_lignes"],
                    }
                    for issue in issues
                ],
            },
        )
        return {
            "resume": f"{len(issues)} type(s) d'anomalie détecté(s).",
            "nombre_anomalies": len(issues),
            "par_type": dict(counts),
            "anomalies": issues,
            "avis_gemini": gemini_advice,
        }

    @staticmethod
    def _lister_tables(connection: sqlite3.Connection) -> set[str]:
        """Récupère les tables présentes et exclut les tables internes SQLite."""
        rows = connection.execute(
            "SELECT name FROM sqlite_master WHERE type = 'table' "
            "AND name NOT LIKE 'sqlite_%'"
        ).fetchall()
        return {str(row["name"]) for row in rows}

    @staticmethod
    def _verifier_table(table: str, tables_autorisees: set[str]) -> str:
        """Valide puis cite un identifiant issu des métadonnées SQLite."""
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
        """Récupère les colonnes d'une table dont le nom a été validé."""
        table_quotidienne = cls._verifier_table(table, tables_autorisees)
        rows = connection.execute(f"PRAGMA table_info({table_quotidienne})").fetchall()
        return [str(row["name"]) for row in rows]

    @classmethod
    def _lire_lignes(
        cls,
        connection: sqlite3.Connection,
        table: str,
        tables_autorisees: set[str],
    ) -> list[sqlite3.Row]:
        """Lit les lignes d'une table après validation de son identifiant."""
        table_quotidienne = cls._verifier_table(table, tables_autorisees)
        return connection.execute(f"SELECT * FROM {table_quotidienne}").fetchall()

    @staticmethod
    def _exemple_ids(rows: list[sqlite3.Row], indices: list[int]) -> str:
        """Construit un exemple sans recopier de valeur potentiellement sensible."""
        ids = [str(rows[index]["id"]) for index in indices[:3] if "id" in rows[index].keys()]
        return ", ".join(f"id={identifier}" for identifier in ids) or "Lignes concernées"

    def _creer_issue(
        self,
        table: str,
        colonne: str | None,
        anomalie: str,
        severite: str,
        indices: list[int],
        rows: list[sqlite3.Row],
    ) -> dict[str, Any]:
        """Formate un constat prêt à être persisté avec l'API du stockage."""
        return {
            "table_name": table,
            "column_name": colonne,
            "type_anomalie": anomalie,
            "severite": severite,
            "nb_lignes": len(indices),
            "exemple": self._exemple_ids(rows, indices),
        }

    def _detecter_valeurs_manquantes(
        self, table: str, columns: list[str], rows: list[sqlite3.Row]
    ) -> list[dict[str, Any]]:
        """Détecte les valeurs NULL ou chaînes vides pour chaque colonne."""
        issues = []
        for column in columns:
            missing = [
                index
                for index, row in enumerate(rows)
                if row[column] is None
                or (isinstance(row[column], str) and not row[column].strip())
            ]
            if missing:
                issues.append(
                    self._creer_issue(
                        table, column, "valeur_manquante", "moyenne", missing, rows
                    )
                )
        return issues

    def _detecter_doublons(
        self, table: str, columns: list[str], rows: list[sqlite3.Row]
    ) -> list[dict[str, Any]]:
        """Détecte les lignes dupliquées selon les clés métier configurées."""
        key_columns = _DUPLICATE_KEYS.get(table, ())
        if not key_columns or any(column not in columns for column in key_columns):
            return []

        groups: dict[tuple[str, ...], list[int]] = {}
        for index, row in enumerate(rows):
            values = tuple(
                str(row[column]).strip().casefold() if row[column] is not None else ""
                for column in key_columns
            )
            if all(values):
                groups.setdefault(values, []).append(index)

        duplicate_indices = [
            index
            for group in groups.values()
            if len(group) > 1
            for index in group[1:]
        ]
        if not duplicate_indices:
            return []

        example = self._exemple_ids(rows, duplicate_indices)
        return [
            {
                "table_name": table,
                "column_name": ",".join(key_columns),
                "type_anomalie": "doublon",
                "severite": "elevee",
                "nb_lignes": len(duplicate_indices),
                "exemple": example,
            }
        ]

    def _detecter_emails_invalides(
        self, table: str, columns: list[str], rows: list[sqlite3.Row]
    ) -> list[dict[str, Any]]:
        """Repère les colonnes d'email et leurs valeurs non conformes."""
        issues = []
        for column in columns:
            if not any(keyword in column.casefold() for keyword in ("email", "courriel")):
                continue
            invalid = [
                index
                for index, row in enumerate(rows)
                if row[column] is not None
                and str(row[column]).strip()
                and not _EMAIL_PATTERN.fullmatch(str(row[column]).strip())
            ]
            if invalid:
                issue = self._creer_issue(
                    table, column, "incoherence", "moyenne", invalid, rows
                )
                issue["exemple"] = (
                    f"{self._exemple_ids(rows, invalid)} (valeurs masquées)"
                )
                issues.append(issue)
        return issues

    def _detecter_montants_negatifs(
        self, table: str, columns: list[str], rows: list[sqlite3.Row]
    ) -> list[dict[str, Any]]:
        """Signale les valeurs négatives dans les colonnes de montant."""
        issues = []
        for column in columns:
            if not any(keyword in column.casefold() for keyword in ("montant", "amount")):
                continue
            negative = [
                index
                for index, row in enumerate(rows)
                if self._est_numerique(row[column]) and float(row[column]) < 0
            ]
            if negative:
                issues.append(
                    self._creer_issue(
                        table, column, "regle_metier", "elevee", negative, rows
                    )
                )
        return issues

    def _detecter_dates_incoherentes(
        self, table: str, columns: list[str], rows: list[sqlite3.Row]
    ) -> list[dict[str, Any]]:
        """Détecte les dates invalides ou futures dans les colonnes de date."""
        issues = []
        today = date.today()
        for column in columns:
            if "date" not in column.casefold():
                continue
            invalid: list[int] = []
            for index, row in enumerate(rows):
                value = row[column]
                if value is None or not str(value).strip():
                    continue
                try:
                    parsed_date = date.fromisoformat(str(value).strip())
                except ValueError:
                    invalid.append(index)
                    continue
                if parsed_date > today:
                    invalid.append(index)
            if invalid:
                issues.append(
                    self._creer_issue(
                        table, column, "incoherence", "elevee", invalid, rows
                    )
                )
        return issues

    def _detecter_commandes_orphelines(
        self,
        orders: list[sqlite3.Row],
        order_columns: list[str],
        clients: list[sqlite3.Row],
        client_columns: list[str],
    ) -> list[dict[str, Any]]:
        """Repère les commandes dont le client référencé n'existe pas."""
        required_orders = {"client_id"}
        required_clients = {"id"}
        if not required_orders.issubset(order_columns) or not required_clients.issubset(
            client_columns
        ):
            return []
        client_ids = {row["id"] for row in clients if row["id"] is not None}
        orphans = [
            index
            for index, order in enumerate(orders)
            if order["client_id"] not in client_ids
        ]
        if not orphans:
            return []
        return [
            self._creer_issue(
                "commandes", "client_id", "regle_metier", "critique", orphans, orders
            )
        ]

    def _detecter_dates_commande_avant_naissance(
        self,
        orders: list[sqlite3.Row],
        order_columns: list[str],
        clients: list[sqlite3.Row],
        client_columns: list[str],
    ) -> list[dict[str, Any]]:
        """Repère les commandes datées avant la naissance du client concerné."""
        if not {"client_id", "date_commande"}.issubset(order_columns):
            return []
        if not {"id", "date_naissance"}.issubset(client_columns):
            return []

        birth_dates: dict[Any, date] = {}
        for client in clients:
            value = client["date_naissance"]
            if value is None:
                continue
            try:
                birth_dates[client["id"]] = date.fromisoformat(str(value).strip())
            except ValueError:
                continue

        incoherent = []
        for index, order in enumerate(orders):
            birth_date = birth_dates.get(order["client_id"])
            if birth_date is None or order["date_commande"] is None:
                continue
            try:
                order_date = date.fromisoformat(str(order["date_commande"]).strip())
            except ValueError:
                continue
            if order_date < birth_date:
                incoherent.append(index)
        if not incoherent:
            return []
        return [
            self._creer_issue(
                "commandes",
                "date_commande",
                "incoherence",
                "critique",
                incoherent,
                orders,
            )
        ]

    @staticmethod
    def _est_numerique(value: Any) -> bool:
        """Indique si une valeur peut être interprétée comme un nombre."""
        if value is None:
            return False
        try:
            float(value)
        except (TypeError, ValueError):
            return False
        return True
