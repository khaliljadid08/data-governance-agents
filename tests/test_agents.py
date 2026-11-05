"""Tests des agents de gouvernance et du cycle du superviseur."""

from contextlib import closing
from pathlib import Path
from typing import Any

import pytest

from agents.base_agent import BaseAgent
from agents.classification_agent import ClassificationAgent
from agents.documentation_agent import DocumentationAgent
from agents.lineage_agent import LineageAgent
from agents.quality_agent import QualityAgent
from agents.security_agent import SecurityAgent
from agents.supervisor import ConsigneIncompleteError, Supervisor
from storage import db
from storage.seed_demo_data import create_demo_data


_TABLES = ["clients", "commandes", "produits"]


@pytest.fixture
def databases(tmp_path: Path) -> tuple[Path, Path]:
    """Prépare deux bases temporaires isolées pour un test."""
    governance_path = tmp_path / "governance.db"
    demo_path = tmp_path / "demo_data.db"
    db.init_db(governance_path)
    create_demo_data(demo_path)
    return governance_path, demo_path


def _create_run(governance_path: Path) -> tuple[int, int]:
    """Crée une demande et un run de test validés par les clés étrangères."""
    with closing(db.get_connection(governance_path)) as connection:
        with connection:
            request_id = db.insert_request(
                connection, "Testeur", "Analyse des données", ", ".join(_TABLES)
            )
            run_id = db.insert_run(connection, request_id, 1)
    return request_id, run_id


def test_quality_agent_detecte_anomalies(databases: tuple[Path, Path]) -> None:
    """Vérifie la détection des doublons et des commandes orphelines."""
    governance_path, demo_path = databases
    _, run_id = _create_run(governance_path)
    result = QualityAgent(governance_path, demo_path).executer(run_id, _TABLES)

    assert result["statut"] == "succes"
    assert result["details"]["par_type"]["doublon"] >= 1
    with closing(db.get_connection(governance_path)) as connection:
        issues = db.list_quality_issues(connection)
    assert any(
        issue["table_name"] == "commandes"
        and issue["column_name"] == "client_id"
        and issue["severite"] == "critique"
        for issue in issues
    )
    assert any(issue["type_anomalie"] == "valeur_manquante" for issue in issues)


def test_classification_agent_classe_et_persiste(
    databases: tuple[Path, Path],
) -> None:
    """Vérifie les catégories et l'intervalle des scores de confiance."""
    governance_path, demo_path = databases
    _, run_id = _create_run(governance_path)
    result = ClassificationAgent(governance_path, demo_path).executer(run_id, _TABLES)

    assert result["statut"] == "succes"
    with closing(db.get_connection(governance_path)) as connection:
        classifications = db.list_classifications(connection)
    by_column = {
        (row["table_name"], row["column_name"]): row for row in classifications
    }
    assert by_column[("clients", "email")]["categorie"] == "personnel"
    assert by_column[("clients", "iban")]["categorie"] == "financier"
    assert by_column[("commandes", "montant")]["categorie"] == "financier"
    assert all(0 <= row["confiance"] <= 1 for row in classifications)


def test_security_agent_signale_iban_en_clair(
    databases: tuple[Path, Path],
) -> None:
    """Vérifie la classification de sensibilité et la règle de masquage IBAN."""
    governance_path, demo_path = databases
    _, run_id = _create_run(governance_path)
    result = SecurityAgent(governance_path, demo_path).executer(run_id, ["clients"])

    assert result["statut"] == "succes"
    with closing(db.get_connection(governance_path)) as connection:
        findings = db.list_security_findings(connection)
    iban = next(finding for finding in findings if finding["column_name"] == "iban")
    assert iban["niveau_sensibilite"] == "confidentiel"
    assert iban["conforme_regle_acces"] == 0
    assert "Masquer" in iban["recommandation"]


def test_lineage_agent_deduit_les_relations(
    databases: tuple[Path, Path],
) -> None:
    """Vérifie la découverte par nom des clés client et produit."""
    governance_path, demo_path = databases
    _, run_id = _create_run(governance_path)
    result = LineageAgent(governance_path, demo_path).executer(run_id, _TABLES)

    assert result["statut"] == "succes"
    relations = result["details"]["relations"]
    assert any(
        edge["source_column"] == "client_id"
        and edge["target_table"] == "clients"
        and edge["type_relation"] == "derive"
        for edge in relations
    )
    assert any(
        edge["source_column"] == "produit_id"
        and edge["target_table"] == "produits"
        for edge in relations
    )


def test_documentation_agent_genere_et_actualise_le_dictionnaire(
    databases: tuple[Path, Path],
) -> None:
    """Vérifie les gabarits et l'actualisation sans doublonner les colonnes."""
    governance_path, demo_path = databases
    _, run_id = _create_run(governance_path)
    ClassificationAgent(governance_path, demo_path).executer(run_id, _TABLES)
    SecurityAgent(governance_path, demo_path).executer(run_id, _TABLES)
    agent = DocumentationAgent(governance_path, demo_path)

    first = agent.executer(run_id, _TABLES)
    second = agent.executer(run_id, _TABLES)

    assert first["statut"] == second["statut"] == "succes"
    with closing(db.get_connection(governance_path)) as connection:
        entries = db.list_data_dictionary_entries(connection)
    assert len(entries) == 16
    by_column = {(row["table_name"], row["column_name"]): row for row in entries}
    assert by_column[("clients", "iban")]["categorie"] == "financier"
    assert by_column[("clients", "iban")]["sensibilite"] == "confidentiel"
    assert by_column[("clients", "email")]["description"]


def test_supervisor_cycle_complet_valide(databases: tuple[Path, Path]) -> None:
    """Vérifie la coordination, la consolidation et la validation positive."""
    governance_path, demo_path = databases
    supervisor = Supervisor(governance_path, demo_path)
    request_id = supervisor.recevoir_consigne(
        "Opérateur",
        "Analyser la qualité, la classification, la sécurité et le lignage",
        _TABLES,
    )

    report = supervisor.coordonner(request_id)
    supervisor.soumettre_a_validation(report["run_id"])
    supervisor.traiter_decision(
        report["run_id"], "Data Owner", "data_owner", "valide", "Validation complète."
    )

    with closing(db.get_connection(governance_path)) as connection:
        run = db.get_run(connection, report["run_id"])
        request = db.get_request(connection, request_id)
    assert run["statut"] == "valide"
    assert request["statut"] == "valide"
    assert report["numero_iteration"] == 1
    assert report["compteurs_par_agent"]["documentation"] == 1
    assert len(report["anomalies_critiques"]) > 0
    assert len(report["colonnes_sensibles_non_conformes"]) > 0


def test_supervisor_cycle_rejet_et_recoordination(
    databases: tuple[Path, Path],
) -> None:
    """Vérifie le commentaire de rejet et l'incrément de la seconde itération."""
    governance_path, demo_path = databases
    supervisor = Supervisor(governance_path, demo_path)
    request_id = supervisor.recevoir_consigne(
        "Opérateur", "Analyser toutes les données", _TABLES
    )
    first_report = supervisor.coordonner(request_id)
    supervisor.soumettre_a_validation(first_report["run_id"])
    supervisor.traiter_decision(
        first_report["run_id"],
        "Data Steward",
        "data_steward",
        "rejete",
        "Compléter les descriptions sensibles.",
    )

    second_report = supervisor.re_coordonner(request_id)

    assert second_report["numero_iteration"] == 2
    with closing(db.get_connection(governance_path)) as connection:
        request = db.get_request(connection, request_id)
        run = db.get_run(connection, second_report["run_id"])
    assert "Compléter les descriptions sensibles." in request["consigne"]
    assert run["statut"] == "en_cours"


def test_echec_agent_n_empeche_pas_les_autres(
    databases: tuple[Path, Path],
) -> None:
    """Vérifie qu'un agent défaillant n'interrompt pas les agents parallèles."""
    governance_path, demo_path = databases

    class AgentEnEchec(BaseAgent):
        """Agent de test qui lève volontairement une exception."""

        def __init__(self) -> None:
            super().__init__("qualite", governance_path, demo_path)

        def analyser(self, run_id: int, perimetre: list[str]) -> dict[str, Any]:
            raise RuntimeError("Échec simulé.")

    supervisor = Supervisor(
        governance_path, demo_path, agents={"qualite": AgentEnEchec()}
    )
    request_id = supervisor.recevoir_consigne(
        "Opérateur", "Analyse complète", _TABLES
    )
    report = supervisor.coordonner(request_id)

    with closing(db.get_connection(governance_path)) as connection:
        results = connection.execute(
            "SELECT agent, statut FROM agent_results WHERE run_id = ?",
            (report["run_id"],),
        ).fetchall()
    statuses = {row["agent"]: row["statut"] for row in results}
    assert statuses["qualite"] == "echec"
    assert statuses["classification"] == "succes"
    assert statuses["securisation"] == "succes"
    assert statuses["lignage"] == "succes"
    assert statuses["documentation"] == "succes"


def test_supervisor_demande_clarification_si_perimetre_invalide(
    databases: tuple[Path, Path],
) -> None:
    """Vérifie que les tables absentes provoquent une demande de clarification."""
    governance_path, demo_path = databases
    supervisor = Supervisor(governance_path, demo_path)

    with pytest.raises(ConsigneIncompleteError, match="Tables introuvables"):
        supervisor.recevoir_consigne(
            "Opérateur", "Analyser les données", ["table_absente"]
        )
