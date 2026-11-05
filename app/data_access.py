"""Lectures de l'interface via les fonctions partagées de storage.db."""

from __future__ import annotations

from pathlib import Path
import sqlite3
from typing import Any

import streamlit as st

from storage import db


_PROJECT_ROOT = Path(__file__).resolve().parent.parent
GOVERNANCE_DB = _PROJECT_ROOT / "storage" / "governance.db"
DEMO_DB = _PROJECT_ROOT / "storage" / "demo_data.db"


def _convertir_lignes(rows: list[sqlite3.Row]) -> list[dict[str, Any]]:
    """Convertit les lignes SQLite en objets simples utilisables par Streamlit."""
    return [dict(row) for row in rows]


@st.cache_data(ttl=15)
def lister_tables_demo(db_path: str) -> list[str]:
    """Liste les tables métier disponibles dans la base de démonstration."""
    connection = db.get_connection(db_path)
    try:
        rows = connection.execute(
            "SELECT name FROM sqlite_master WHERE type = ? "
            "AND name NOT LIKE ? ORDER BY name",
            ("table", "sqlite_%"),
        ).fetchall()
        return [str(row["name"]) for row in rows]
    finally:
        connection.close()


@st.cache_data(ttl=10)
def lister_demandes_et_runs(db_path: str) -> list[dict[str, Any]]:
    """Retourne les runs avec leur demande parente."""
    connection = db.get_connection(db_path)
    try:
        requests = {row["id"]: dict(row) for row in db.list_requests(connection)}
        runs = _convertir_lignes(db.list_runs(connection))
        return [
            {"request": requests.get(run["request_id"]), "run": run}
            for run in runs
        ]
    finally:
        connection.close()


@st.cache_data(ttl=10)
def lister_runs_a_valider(db_path: str) -> list[dict[str, Any]]:
    """Retourne les runs en attente d'un avis humain avec leur consigne."""
    connection = db.get_connection(db_path)
    try:
        rows = connection.execute(
            "SELECT runs.id AS run_id, runs.request_id, runs.numero_iteration, "
            "runs.statut, runs.started_at, requests.operateur, requests.consigne, "
            "requests.perimetre FROM runs "
            "JOIN requests ON requests.id = runs.request_id "
            "WHERE runs.statut = ? ORDER BY runs.started_at DESC, runs.id DESC",
            ("a_valider",),
        ).fetchall()
        return _convertir_lignes(rows)
    finally:
        connection.close()


@st.cache_data(ttl=10)
def lire_resultats_agents(db_path: str, run_id: int) -> list[dict[str, Any]]:
    """Récupère les résultats des agents associés à un run."""
    connection = db.get_connection(db_path)
    try:
        return [
            dict(row)
            for row in db.list_agent_results(connection)
            if row["run_id"] == run_id
        ]
    finally:
        connection.close()


@st.cache_data(ttl=10)
def lire_anomalies(db_path: str, run_id: int) -> list[dict[str, Any]]:
    """Récupère les anomalies qualité associées à un run."""
    connection = db.get_connection(db_path)
    try:
        return [
            dict(row)
            for row in db.list_quality_issues(connection)
            if row["run_id"] == run_id
        ]
    finally:
        connection.close()


@st.cache_data(ttl=10)
def lire_classifications(db_path: str, run_id: int) -> list[dict[str, Any]]:
    """Récupère les classifications associées à un run."""
    connection = db.get_connection(db_path)
    try:
        return [
            dict(row)
            for row in db.list_classifications(connection)
            if row["run_id"] == run_id
        ]
    finally:
        connection.close()


@st.cache_data(ttl=10)
def lire_constats_securite(db_path: str, run_id: int) -> list[dict[str, Any]]:
    """Récupère les constats de sécurité associés à un run."""
    connection = db.get_connection(db_path)
    try:
        return [
            dict(row)
            for row in db.list_security_findings(connection)
            if row["run_id"] == run_id
        ]
    finally:
        connection.close()


@st.cache_data(ttl=10)
def lire_lignage(db_path: str, run_id: int) -> list[dict[str, Any]]:
    """Récupère les liens de lignage associés à un run."""
    connection = db.get_connection(db_path)
    try:
        return [
            dict(row)
            for row in db.list_lineage_edges(connection)
            if row["run_id"] == run_id
        ]
    finally:
        connection.close()


@st.cache_data(ttl=15)
def lire_dictionnaire(db_path: str) -> list[dict[str, Any]]:
    """Récupère le dictionnaire de données complet."""
    connection = db.get_connection(db_path)
    try:
        return _convertir_lignes(db.list_data_dictionary_entries(connection))
    finally:
        connection.close()


@st.cache_data(ttl=15)
def lire_journal_audit(db_path: str) -> list[dict[str, Any]]:
    """Récupère le journal d'audit complet."""
    connection = db.get_connection(db_path)
    try:
        return _convertir_lignes(db.list_audit_log(connection))
    finally:
        connection.close()


@st.cache_data(ttl=15)
def lire_validations(db_path: str) -> list[dict[str, Any]]:
    """Récupère l'historique des décisions humaines."""
    connection = db.get_connection(db_path)
    try:
        return _convertir_lignes(db.list_validations(connection))
    finally:
        connection.close()


def invalider_cache() -> None:
    """Invalide les lectures mises en cache après une action d'écriture."""
    for fonction in (
        lister_tables_demo,
        lister_demandes_et_runs,
        lister_runs_a_valider,
        lire_resultats_agents,
        lire_anomalies,
        lire_classifications,
        lire_constats_securite,
        lire_lignage,
        lire_dictionnaire,
        lire_journal_audit,
        lire_validations,
    ):
        fonction.clear()
