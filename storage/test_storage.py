"""Tests de la couche SQLite de gouvernance."""

import sqlite3
from contextlib import closing

import pytest

from storage import db


def _create_run(
    connection: sqlite3.Connection, operateur: str = "Operateur demo"
) -> tuple[int, int]:
    request_id = db.insert_request(
        connection, operateur, "Analyser les données", "clients, commandes"
    )
    run_id = db.insert_run(connection, request_id, 1)
    return request_id, run_id


def test_initialisation_et_insertion(tmp_path) -> None:
    """Vérifie le schéma, les clés étrangères et quelques opérations CRUD."""
    db_path = tmp_path / "governance.db"
    db.init_db(db_path)

    connection = db.get_connection(db_path)
    try:
        assert connection.row_factory is sqlite3.Row
        assert connection.execute("PRAGMA foreign_keys").fetchone()[0] == 1

        request_id, run_id = _create_run(connection)
        result_id = db.insert_agent_result(
            connection,
            run_id,
            "qualite",
            "succes",
            "Analyse terminée",
            '{"anomalies": 2}',
        )

        assert db.get_request(connection, request_id)["statut"] == "en_attente"
        assert db.get_run(connection, run_id)["numero_iteration"] == 1
        assert db.get_agent_result(connection, result_id)["agent"] == "qualite"
        assert len(db.list_requests(connection)) == 1
        assert len(db.list_runs(connection)) == 1
        assert len(db.list_agent_results(connection)) == 1
        with pytest.raises(sqlite3.IntegrityError):
            db.insert_run(connection, 9999, 1)
    finally:
        connection.close()


def test_workflow_validation(tmp_path) -> None:
    """Vérifie la soumission et l'acceptation d'une itération."""
    db_path = tmp_path / "governance.db"
    db.init_db(db_path)
    connection = db.get_connection(db_path)
    try:
        request_id, run_id = _create_run(connection)
        connection.commit()
    finally:
        connection.close()

    db.submit_for_validation(run_id, db_path)
    with closing(db.get_connection(db_path)) as connection:
        assert db.get_run(connection, run_id)["statut"] == "a_valider"
        assert db.get_request(connection, request_id)["statut"] == "a_valider"

    validation_id = db.validate_run(
        run_id, "Amina", "valide", "Conforme.", db_path=db_path, role="data_owner"
    )
    with closing(db.get_connection(db_path)) as connection:
        validation = db.get_validation(connection, validation_id)
        assert validation["decision"] == "valide"
        assert validation["role"] == "data_owner"
        assert validation["commentaire"] == "Conforme."
        assert db.get_run(connection, run_id)["statut"] == "valide"
        assert db.get_request(connection, request_id)["statut"] == "valide"


def test_workflow_rejet_enregistre_le_commentaire(tmp_path) -> None:
    """Vérifie que le rejet est propagé et que son commentaire est conservé."""
    db_path = tmp_path / "governance.db"
    db.init_db(db_path)
    connection = db.get_connection(db_path)
    try:
        request_id, run_id = _create_run(connection, "Autre operateur")
        connection.commit()
    finally:
        connection.close()

    db.submit_for_validation(run_id, db_path)
    validation_id = db.validate_run(
        run_id, "Noah", "rejete", "Compléter les champs manquants.", db_path
    )
    with closing(db.get_connection(db_path)) as connection:
        validation = db.get_validation(connection, validation_id)
        assert validation["decision"] == "rejete"
        assert validation["commentaire"] == "Compléter les champs manquants."
        assert db.get_run(connection, run_id)["statut"] == "rejete"
        assert db.get_request(connection, request_id)["statut"] == "rejete"


def test_validation_impossible_avant_soumission(tmp_path) -> None:
    """Empêche la décision sur une itération qui n'a pas été soumise."""
    db_path = tmp_path / "governance.db"
    db.init_db(db_path)
    connection = db.get_connection(db_path)
    try:
        _, run_id = _create_run(connection)
        connection.commit()
    finally:
        connection.close()

    with pytest.raises(ValueError, match="soumise"):
        db.validate_run(run_id, "Amina", "valide", None, db_path)
