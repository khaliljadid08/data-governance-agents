"""Accès SQLite à la base de métadonnées de gouvernance."""

from pathlib import Path
import sqlite3
from typing import Any


_DEFAULT_DB_PATH = Path(__file__).with_name("governance.db")
_SCHEMA_PATH = Path(__file__).with_name("schema.sql")


def get_connection(db_path: str | Path | None = None) -> sqlite3.Connection:
    """Ouvre la base avec les clés étrangères activées et des lignes nommées."""
    path = Path(db_path) if db_path is not None else _DEFAULT_DB_PATH
    path.parent.mkdir(parents=True, exist_ok=True)
    connection = sqlite3.connect(path)
    connection.row_factory = sqlite3.Row
    connection.execute("PRAGMA foreign_keys = ON")
    return connection


def init_db(db_path: str | Path | None = None) -> None:
    """Crée les tables et les index définis dans schema.sql."""
    schema = _SCHEMA_PATH.read_text(encoding="utf-8")
    connection = get_connection(db_path)
    try:
        connection.executescript(schema)
    finally:
        connection.close()


def _insert(connection: sqlite3.Connection, sql: str, values: tuple[Any, ...]) -> int:
    """Exécute une insertion paramétrée et renvoie l'identifiant créé."""
    cursor = connection.execute(sql, values)
    return int(cursor.lastrowid)


def _get(
    connection: sqlite3.Connection, sql: str, values: tuple[Any, ...]
) -> sqlite3.Row | None:
    """Renvoie une ligne ou None à partir d'une requête paramétrée."""
    return connection.execute(sql, values).fetchone()


def _list(connection: sqlite3.Connection, sql: str) -> list[sqlite3.Row]:
    """Renvoie toutes les lignes d'une table dans un ordre stable."""
    return list(connection.execute(sql).fetchall())


def insert_request(
    connection: sqlite3.Connection,
    operateur: str,
    consigne: str,
    perimetre: str,
    statut: str = "en_attente",
) -> int:
    """Enregistre une demande de gouvernance et renvoie son identifiant."""
    return _insert(
        connection,
        "INSERT INTO requests (operateur, consigne, perimetre, statut) VALUES (?, ?, ?, ?)",
        (operateur, consigne, perimetre, statut),
    )


def get_request(connection: sqlite3.Connection, request_id: int) -> sqlite3.Row | None:
    """Récupère une demande par son identifiant."""
    return _get(connection, "SELECT * FROM requests WHERE id = ?", (request_id,))


def list_requests(connection: sqlite3.Connection) -> list[sqlite3.Row]:
    """Liste les demandes par ordre de création."""
    return _list(connection, "SELECT * FROM requests ORDER BY id")


def insert_run(
    connection: sqlite3.Connection,
    request_id: int,
    numero_iteration: int,
    statut: str = "en_cours",
    finished_at: str | None = None,
) -> int:
    """Crée une itération de traitement pour une demande."""
    return _insert(
        connection,
        "INSERT INTO runs (request_id, numero_iteration, statut, finished_at) "
        "VALUES (?, ?, ?, ?)",
        (request_id, numero_iteration, statut, finished_at),
    )


def get_run(connection: sqlite3.Connection, run_id: int) -> sqlite3.Row | None:
    """Récupère une itération par son identifiant."""
    return _get(connection, "SELECT * FROM runs WHERE id = ?", (run_id,))


def list_runs(connection: sqlite3.Connection) -> list[sqlite3.Row]:
    """Liste les itérations par identifiant."""
    return _list(connection, "SELECT * FROM runs ORDER BY id")


def insert_agent_result(
    connection: sqlite3.Connection,
    run_id: int,
    agent: str,
    statut: str,
    resume: str | None = None,
    details_json: str | None = None,
) -> int:
    """Enregistre le résultat d'un agent pour une itération."""
    return _insert(
        connection,
        "INSERT INTO agent_results (run_id, agent, statut, resume, details_json) "
        "VALUES (?, ?, ?, ?, ?)",
        (run_id, agent, statut, resume, details_json),
    )


def get_agent_result(
    connection: sqlite3.Connection, result_id: int
) -> sqlite3.Row | None:
    """Récupère un résultat d'agent par son identifiant."""
    return _get(connection, "SELECT * FROM agent_results WHERE id = ?", (result_id,))


def list_agent_results(connection: sqlite3.Connection) -> list[sqlite3.Row]:
    """Liste les résultats d'agents par identifiant."""
    return _list(connection, "SELECT * FROM agent_results ORDER BY id")


def insert_quality_issue(
    connection: sqlite3.Connection,
    run_id: int,
    table_name: str,
    column_name: str | None,
    type_anomalie: str,
    severite: str,
    nb_lignes: int = 0,
    exemple: str | None = None,
) -> int:
    """Enregistre une anomalie détectée lors d'une analyse de qualité."""
    return _insert(
        connection,
        "INSERT INTO quality_issues "
        "(run_id, table_name, column_name, type_anomalie, severite, nb_lignes, exemple) "
        "VALUES (?, ?, ?, ?, ?, ?, ?)",
        (run_id, table_name, column_name, type_anomalie, severite, nb_lignes, exemple),
    )


def get_quality_issue(
    connection: sqlite3.Connection, issue_id: int
) -> sqlite3.Row | None:
    """Récupère une anomalie par son identifiant."""
    return _get(connection, "SELECT * FROM quality_issues WHERE id = ?", (issue_id,))


def list_quality_issues(connection: sqlite3.Connection) -> list[sqlite3.Row]:
    """Liste les anomalies par identifiant."""
    return _list(connection, "SELECT * FROM quality_issues ORDER BY id")


def insert_classification(
    connection: sqlite3.Connection,
    run_id: int,
    table_name: str,
    column_name: str,
    categorie: str,
    confiance: float | None = None,
) -> int:
    """Enregistre la classification d'une colonne."""
    return _insert(
        connection,
        "INSERT INTO classifications "
        "(run_id, table_name, column_name, categorie, confiance) "
        "VALUES (?, ?, ?, ?, ?)",
        (run_id, table_name, column_name, categorie, confiance),
    )


def get_classification(
    connection: sqlite3.Connection, classification_id: int
) -> sqlite3.Row | None:
    """Récupère une classification par son identifiant."""
    return _get(
        connection, "SELECT * FROM classifications WHERE id = ?", (classification_id,)
    )


def list_classifications(connection: sqlite3.Connection) -> list[sqlite3.Row]:
    """Liste les classifications par identifiant."""
    return _list(connection, "SELECT * FROM classifications ORDER BY id")


def insert_security_finding(
    connection: sqlite3.Connection,
    run_id: int,
    table_name: str,
    column_name: str,
    niveau_sensibilite: str,
    type_donnee: str,
    conforme_regle_acces: bool,
    recommandation: str | None = None,
) -> int:
    """Enregistre un constat de sécurité sur une colonne."""
    return _insert(
        connection,
        "INSERT INTO security_findings "
        "(run_id, table_name, column_name, niveau_sensibilite, type_donnee, "
        "conforme_regle_acces, recommandation) VALUES (?, ?, ?, ?, ?, ?, ?)",
        (
            run_id,
            table_name,
            column_name,
            niveau_sensibilite,
            type_donnee,
            conforme_regle_acces,
            recommandation,
        ),
    )


def get_security_finding(
    connection: sqlite3.Connection, finding_id: int
) -> sqlite3.Row | None:
    """Récupère un constat de sécurité par son identifiant."""
    return _get(
        connection, "SELECT * FROM security_findings WHERE id = ?", (finding_id,)
    )


def list_security_findings(connection: sqlite3.Connection) -> list[sqlite3.Row]:
    """Liste les constats de sécurité par identifiant."""
    return _list(connection, "SELECT * FROM security_findings ORDER BY id")


def insert_lineage_edge(
    connection: sqlite3.Connection,
    run_id: int,
    source_table: str,
    source_column: str | None,
    target_table: str,
    target_column: str | None,
    type_relation: str,
) -> int:
    """Enregistre une relation de lignage entre deux champs."""
    return _insert(
        connection,
        "INSERT INTO lineage_edges "
        "(run_id, source_table, source_column, target_table, target_column, type_relation) "
        "VALUES (?, ?, ?, ?, ?, ?)",
        (
            run_id,
            source_table,
            source_column,
            target_table,
            target_column,
            type_relation,
        ),
    )


def get_lineage_edge(
    connection: sqlite3.Connection, edge_id: int
) -> sqlite3.Row | None:
    """Récupère une relation de lignage par son identifiant."""
    return _get(connection, "SELECT * FROM lineage_edges WHERE id = ?", (edge_id,))


def list_lineage_edges(connection: sqlite3.Connection) -> list[sqlite3.Row]:
    """Liste les relations de lignage par identifiant."""
    return _list(connection, "SELECT * FROM lineage_edges ORDER BY id")


def insert_data_dictionary_entry(
    connection: sqlite3.Connection,
    table_name: str,
    column_name: str,
    description: str | None = None,
    type_sql: str | None = None,
    categorie: str | None = None,
    sensibilite: str | None = None,
    run_id: int | None = None,
) -> int:
    """Ajoute une entrée au dictionnaire de données."""
    return _insert(
        connection,
        "INSERT INTO data_dictionary "
        "(table_name, column_name, description, type_sql, categorie, sensibilite, run_id) "
        "VALUES (?, ?, ?, ?, ?, ?, ?)",
        (table_name, column_name, description, type_sql, categorie, sensibilite, run_id),
    )


def get_data_dictionary_entry(
    connection: sqlite3.Connection, entry_id: int
) -> sqlite3.Row | None:
    """Récupère une entrée du dictionnaire par son identifiant."""
    return _get(
        connection, "SELECT * FROM data_dictionary WHERE id = ?", (entry_id,)
    )


def list_data_dictionary_entries(
    connection: sqlite3.Connection,
) -> list[sqlite3.Row]:
    """Liste les entrées du dictionnaire par nom de table et de colonne."""
    return _list(
        connection,
        "SELECT * FROM data_dictionary ORDER BY table_name, column_name",
    )


def insert_validation(
    connection: sqlite3.Connection,
    run_id: int,
    reviewer: str,
    role: str,
    decision: str,
    commentaire: str | None = None,
) -> int:
    """Enregistre une décision de validation pour une itération."""
    return _insert(
        connection,
        "INSERT INTO validations (run_id, reviewer, role, decision, commentaire) "
        "VALUES (?, ?, ?, ?, ?)",
        (run_id, reviewer, role, decision, commentaire),
    )


def get_validation(
    connection: sqlite3.Connection, validation_id: int
) -> sqlite3.Row | None:
    """Récupère une validation par son identifiant."""
    return _get(connection, "SELECT * FROM validations WHERE id = ?", (validation_id,))


def list_validations(connection: sqlite3.Connection) -> list[sqlite3.Row]:
    """Liste les validations par identifiant."""
    return _list(connection, "SELECT * FROM validations ORDER BY id")


def insert_audit_log(
    connection: sqlite3.Connection,
    acteur: str,
    action: str,
    entite: str,
    entite_id: int | None = None,
) -> int:
    """Ajoute une action à la piste d'audit."""
    return _insert(
        connection,
        "INSERT INTO audit_log (acteur, action, entite, entite_id) VALUES (?, ?, ?, ?)",
        (acteur, action, entite, entite_id),
    )


def get_audit_log_entry(
    connection: sqlite3.Connection, entry_id: int
) -> sqlite3.Row | None:
    """Récupère une entrée d'audit par son identifiant."""
    return _get(connection, "SELECT * FROM audit_log WHERE id = ?", (entry_id,))


def list_audit_log(connection: sqlite3.Connection) -> list[sqlite3.Row]:
    """Liste les entrées d'audit par identifiant."""
    return _list(connection, "SELECT * FROM audit_log ORDER BY id")


def submit_for_validation(
    run_id: int, db_path: str | Path | None = None
) -> None:
    """Soumet une itération et sa demande à la validation humaine."""
    connection = get_connection(db_path)
    try:
        with connection:
            run = connection.execute(
                "SELECT request_id, statut FROM runs WHERE id = ?", (run_id,)
            ).fetchone()
            if run is None:
                raise LookupError(f"L'itération {run_id} n'existe pas.")
            if run["statut"] != "en_cours":
                raise ValueError("Seule une itération en cours peut être soumise.")

            connection.execute(
                "UPDATE runs SET statut = 'a_valider', finished_at = CURRENT_TIMESTAMP "
                "WHERE id = ?",
                (run_id,),
            )
            connection.execute(
                "UPDATE requests SET statut = 'a_valider' WHERE id = ?",
                (run["request_id"],),
            )
            insert_audit_log(connection, "systeme", "soumission_validation", "run", run_id)
    finally:
        connection.close()


def validate_run(
    run_id: int,
    reviewer: str,
    decision: str,
    comment: str | None,
    db_path: str | Path | None = None,
    role: str = "data_steward",
) -> int:
    """Enregistre la décision et met à jour le statut de l'itération et de la demande."""
    if decision not in ("valide", "rejete"):
        raise ValueError("La décision doit être 'valide' ou 'rejete'.")
    if role not in ("data_steward", "data_owner"):
        raise ValueError("Le rôle doit être 'data_steward' ou 'data_owner'.")

    connection = get_connection(db_path)
    try:
        with connection:
            run = connection.execute(
                "SELECT request_id, statut FROM runs WHERE id = ?", (run_id,)
            ).fetchone()
            if run is None:
                raise LookupError(f"L'itération {run_id} n'existe pas.")
            if run["statut"] != "a_valider":
                raise ValueError("L'itération doit être soumise avant sa validation.")

            validation_id = insert_validation(
                connection, run_id, reviewer, role, decision, comment
            )
            connection.execute(
                "UPDATE runs SET statut = ? WHERE id = ?", (decision, run_id)
            )
            connection.execute(
                "UPDATE requests SET statut = ? WHERE id = ?",
                (decision, run["request_id"]),
            )
            insert_audit_log(
                connection, reviewer, f"validation_{decision}", "run", run_id
            )
            return validation_id
    finally:
        connection.close()
