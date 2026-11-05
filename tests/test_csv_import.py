"""Tests de l'import temporaire des fichiers CSV."""

from contextlib import closing
from io import BytesIO
import json
from pathlib import Path
import sqlite3
from typing import Any

import pytest

from agents.supervisor import Supervisor
from app.csv_import import (
    TAILLE_MAX_OCTETS,
    CsvImportError,
    cleanup_database,
    create_database,
)
from storage import db


class UploadedFile(BytesIO):
    """Représente un fichier téléversé dans les tests sans dépendre de Streamlit."""

    def __init__(self, name: str, content: bytes) -> None:
        super().__init__(content)
        self.name = name


def test_importe_plusieurs_csv_et_normalise_les_identifiants() -> None:
    """Vérifie le séparateur, les accents et les colonnes normalisées uniques."""
    imported = create_database(
        [
            UploadedFile(
                "01 clients.csv",
                "client id;client_id;nom prénom\n1;2;Élodie\n".encode("latin-1"),
            ),
            UploadedFile(
                "commandes.csv",
                b"client_id,montant\n1,12\n",
            ),
        ]
    )
    try:
        assert imported.table_names == ("table_01_clients", "commandes")
        with closing(sqlite3.connect(imported.db_path)) as connection:
            columns = [
                row[1]
                for row in connection.execute(
                    'PRAGMA table_info("table_01_clients")'
                )
            ]
            assert columns == ["client_id", "client_id_2", "nom_prenom"]
            assert connection.execute(
                'SELECT "nom_prenom" FROM "table_01_clients"'
            ).fetchone() == ("Élodie",)
            assert connection.execute(
                'SELECT COUNT(*) FROM "commandes"'
            ).fetchone() == (1,)
    finally:
        cleanup_database(imported.db_path)
    assert not imported.db_path.exists()


def test_refuse_extension_invalide_et_fichier_superieur_a_16_mo() -> None:
    """Applique les contrôles de format et de taille avant de créer une base."""
    with pytest.raises(CsvImportError, match="doit être un CSV"):
        create_database([UploadedFile("clients.txt", b"id\n1\n")])
    with pytest.raises(CsvImportError, match="dépasse la limite de 16 Mo"):
        create_database(
            [UploadedFile("clients.csv", b"x" * (TAILLE_MAX_OCTETS + 1))]
        )


class MetadataRecorder:
    """Enregistre les métadonnées envoyées aux avis sans appeler Gemini."""

    def __init__(self) -> None:
        self.calls: list[dict[str, Any]] = []

    def generer(self, objectif: str, metadonnees: dict[str, Any]) -> str:
        self.calls.append(metadonnees)
        return "Conseil de démonstration."


def test_les_lignes_csv_ne_sont_jamais_transmises_a_gemini(
    tmp_path: Path,
) -> None:
    """Vérifie qu'aucune donnée de ligne importée n'entre dans les prompts."""
    private_email = "csv-only-private@example.test"
    imported = create_database(
        [
            UploadedFile(
                "clients.csv",
                f"id,email\n1,{private_email}\n".encode(),
            ),
            UploadedFile(
                "commandes.csv",
                b"client_id,montant\n1,-55\n",
            ),
        ]
    )
    governance_path = tmp_path / "governance.db"
    db.init_db(governance_path)
    assistant = MetadataRecorder()
    try:
        with closing(sqlite3.connect(imported.db_path)) as connection:
            assert connection.execute(
                'SELECT "email" FROM "clients"'
            ).fetchone() == (private_email,)
        supervisor = Supervisor(
            governance_path,
            imported.db_path,
            gemini_assistant=assistant,
        )
        request_id = supervisor.recevoir_consigne(
            "Opérateur",
            "Analyser la qualité, la classification, la sécurité et le lignage",
            list(imported.table_names),
        )
        supervisor.coordonner(request_id)
        serialized = json.dumps(assistant.calls, ensure_ascii=False)
        assert assistant.calls
        assert private_email not in serialized
        assert "nombre_anomalies" in serialized
    finally:
        cleanup_database(imported.db_path)
