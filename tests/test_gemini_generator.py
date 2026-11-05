"""Tests locaux de l'intégration Gemini sans appel réseau."""

from contextlib import closing
import json
from pathlib import Path
import re
from typing import Any

import pytest

from agents.documentation_agent import GeminiDescriptionGenerator
from agents.gemini_metadata import GeminiMetadataAssistant
from agents.supervisor import Supervisor
from storage import db
from storage.seed_demo_data import create_demo_data


class _FakeInteractions:
    """Fournit une réponse factice compatible avec le client Gemini."""

    def __init__(self, output_text: str) -> None:
        self.output_text = output_text
        self.request: dict[str, Any] | None = None

    def create(self, **request: Any) -> Any:
        """Enregistre le prompt et renvoie une réponse de test."""
        self.request = request

        class Response:
            output_text = self.output_text

        return Response()


class _FakeClient:
    """Expose l'interface d'interactions attendue par le générateur."""

    def __init__(self, output_text: str) -> None:
        self.interactions = _FakeInteractions(output_text)


def test_gemini_genere_avec_metadonnees_sans_valeurs_de_lignes(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Vérifie le prompt, le modèle et la description renvoyée."""
    fake_client = _FakeClient("Adresse de contact électronique du client.")
    monkeypatch.setattr(
        "agents.gemini_metadata.genai.Client",
        lambda api_key: fake_client,
    )
    generator = GeminiDescriptionGenerator("cle-factice", "gemini-test")

    result = generator.generer(
        "clients",
        "email",
        {
            "type_sql": "TEXT",
            "categorie": "personnel",
            "sensibilite": "confidentiel",
            "valeur_exemple": "ne-pas-transmettre@example.test",
        },
    )

    assert result == "Adresse de contact électronique du client."
    assert fake_client.interactions.request is not None
    request = fake_client.interactions.request
    assert request["model"] == "gemini-test"
    assert "clients" in request["input"]
    assert "email" in request["input"]
    assert "confidentiel" in request["input"]
    assert "ne-pas-transmettre@example.test" not in request["input"]


def test_gemini_refuse_une_reponse_vide(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Signale explicitement une réponse vide du fournisseur."""
    fake_client = _FakeClient(" ")
    monkeypatch.setattr(
        "agents.gemini_metadata.genai.Client",
        lambda api_key: fake_client,
    )
    generator = GeminiDescriptionGenerator("cle-factice")

    with pytest.raises(ValueError, match="aucune description"):
        generator.generer("clients", "email", {})


def test_gemini_refuse_une_cle_vide() -> None:
    """Empêche la création d'un client Gemini sans clé API."""
    with pytest.raises(ValueError, match="GEMINI_API_KEY"):
        GeminiDescriptionGenerator(" ")


def test_gemini_refuse_un_champ_de_donnees_metier(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Empêche les champs hors contrat d'être envoyés au fournisseur."""
    fake_client = _FakeClient("Avis.")
    monkeypatch.setattr(
        "agents.gemini_metadata.genai.Client",
        lambda api_key: fake_client,
    )
    assistant = GeminiMetadataAssistant("cle-factice")

    with pytest.raises(ValueError, match="non autorisé"):
        assistant.generer(
            "Résumer",
            {"valeur_client": "valeur confidentielle"},
        )

    assert fake_client.interactions.request is None


class _RecordingAssistant:
    """Enregistre les métadonnées envoyées sans appeler le fournisseur."""

    def __init__(self) -> None:
        self.calls: list[tuple[str, dict[str, Any]]] = []

    def generer(self, objectif: str, metadonnees: dict[str, Any]) -> str:
        self.calls.append((objectif, metadonnees))
        return "Conseil consultatif de test."


class _FailingAssistant:
    """Simule une panne d'API Gemini."""

    def generer(self, objectif: str, metadonnees: dict[str, Any]) -> str:
        raise RuntimeError("API indisponible")


def test_gemini_est_injecte_dans_les_agents_et_la_synthese_sans_valeurs(
    tmp_path: Path,
) -> None:
    """Vérifie les avis de tous les agents sans transmission de données métier."""
    governance_path = tmp_path / "governance.db"
    demo_path = tmp_path / "demo_data.db"
    db.init_db(governance_path)
    create_demo_data(demo_path)
    assistant = _RecordingAssistant()
    supervisor = Supervisor(
        governance_path,
        demo_path,
        gemini_assistant=assistant,
    )
    request_id = supervisor.recevoir_consigne(
        "Opérateur",
        "Analyser la qualité, la classification, la sécurité et le lignage",
        ["clients", "commandes", "produits"],
    )

    report = supervisor.coordonner(request_id)

    with closing(db.get_connection(governance_path)) as connection:
        saved_results = db.list_agent_results(connection)
    details_by_agent = {
        row["agent"]: json.loads(row["details_json"])
        for row in saved_results
        if row["run_id"] == report["run_id"]
    }
    for agent_id in ("qualite", "classification", "securisation", "lignage"):
        assert details_by_agent[agent_id]["avis_gemini"]["statut"] == "succes"
    assert details_by_agent["documentation"]["source_descriptions"] == "gemini"
    assert report["synthese_gemini"]["statut"] == "succes"
    assert len(assistant.calls) > 5
    for _, metadata in assistant.calls:
        GeminiMetadataAssistant._valider_metadonnees(metadata)

    serialized_metadata = json.dumps(
        [metadata for _, metadata in assistant.calls],
        ensure_ascii=False,
    )
    assert "exemple" not in serialized_metadata.casefold()
    assert not re.search(r"[\w.+-]+@[\w.-]+\.[A-Za-z]{2,}", serialized_metadata)
    assert "Analyser la qualité" not in serialized_metadata


def test_panne_gemini_est_signalee_sans_bloquer_les_agents(
    tmp_path: Path,
) -> None:
    """Vérifie que les analyses locales continuent lors d'une panne Gemini."""
    governance_path = tmp_path / "governance.db"
    demo_path = tmp_path / "demo_data.db"
    db.init_db(governance_path)
    create_demo_data(demo_path)
    supervisor = Supervisor(
        governance_path,
        demo_path,
        gemini_assistant=_FailingAssistant(),
    )
    request_id = supervisor.recevoir_consigne(
        "Opérateur",
        "Analyser la qualité, la classification, la sécurité et le lignage",
        ["clients", "commandes", "produits"],
    )

    report = supervisor.coordonner(request_id)

    statuses = {
        result["agent"]: result["statut"]
        for result in report["agents_execution"]
    }
    assert statuses["qualite"] == "succes"
    assert statuses["classification"] == "succes"
    assert statuses["securisation"] == "succes"
    assert statuses["lignage"] == "succes"
    assert statuses["documentation"] == "succes"
    assert report["synthese_gemini"]["statut"] == "echec"
    documentation_result = next(
        result
        for result in report["agents_execution"]
        if result["agent"] == "documentation"
    )
    assert documentation_result["details"]["gemini_erreur"] == "API indisponible"
    assert (
        documentation_result["details"]["source_descriptions"]
        == "gabarits_locaux"
    )
    quality_result = next(
        result
        for result in report["agents_execution"]
        if result["agent"] == "qualite"
    )
    assert quality_result["details"]["avis_gemini"]["statut"] == "echec"
