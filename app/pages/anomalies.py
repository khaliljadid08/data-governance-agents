"""Exploration filtrable des constats de qualité."""

from __future__ import annotations

import logging

import streamlit as st

from app import data_access
from app.components import badge, section_title


logger = logging.getLogger(__name__)
_SEVERITES = {
    "faible": "Faible",
    "moyenne": "Moyenne",
    "elevee": "Élevée",
    "haute": "Haute",
    "critique": "Critique",
}


def _selected_run(pairs: list[dict]) -> dict | None:
    """Affiche le choix de run et retourne la sélection."""
    ordered = sorted(pairs, key=lambda pair: pair["run"]["id"], reverse=True)
    if not ordered:
        return None
    ids = [pair["run"]["id"] for pair in ordered]
    current = st.session_state.get("run_id_courant")
    index = ids.index(current) if current in ids else 0
    selected_id = st.selectbox("Analyse", ids, index=index, key="anomalies_run")
    return next(pair for pair in ordered if pair["run"]["id"] == selected_id)


def render() -> None:
    """Filtre et présente les anomalies du run sélectionné."""
    section_title(
        "Anomalies",
        "QUALITÉ DES DONNÉES",
        "Filtrez les constats par sévérité, table et type d'anomalie.",
    )
    try:
        pairs = data_access.lister_demandes_et_runs(
            str(data_access.GOVERNANCE_DB)
        )
    except Exception as erreur:
        logger.exception("Impossible de charger les runs pour les anomalies.")
        st.error(f"Impossible de charger les analyses : {erreur}")
        return
    if not pairs:
        st.info("Aucune analyse lancée. Commencez par importer un fichier.")
        return
    pair = _selected_run(pairs)
    if pair is None:
        st.info("Aucune anomalie à afficher.")
        return

    run_id = int(pair["run"]["id"])
    try:
        issues = data_access.lire_anomalies(
            str(data_access.GOVERNANCE_DB), run_id
        )
    except Exception as erreur:
        logger.exception("Impossible de lire les anomalies du run %s.", run_id)
        st.error(f"Impossible de lire les anomalies : {erreur}")
        return
    if not issues:
        st.info("Aucune anomalie de qualité n'a été détectée pour ce run.")
        return

    filter_columns = st.columns(3)
    with filter_columns[0]:
        severity = st.selectbox(
            "Sévérité",
            ["Toutes", *sorted({str(row["severite"]) for row in issues})],
            format_func=lambda value: (
                "Toutes" if value == "Toutes" else _SEVERITES.get(value, value.title())
            ),
        )
    with filter_columns[1]:
        table_name = st.selectbox(
            "Table",
            ["Toutes", *sorted({str(row["table_name"]) for row in issues})],
        )
    with filter_columns[2]:
        issue_type = st.selectbox(
            "Type d'anomalie",
            ["Tous", *sorted({str(row["type_anomalie"]) for row in issues})],
            format_func=lambda value: value.replace("_", " ").title(),
        )

    filtered = [
        row
        for row in issues
        if (severity == "Toutes" or row["severite"] == severity)
        and (table_name == "Toutes" or row["table_name"] == table_name)
        and (issue_type == "Tous" or row["type_anomalie"] == issue_type)
    ]
    st.caption(f"{len(filtered)} constat(s) correspondant aux filtres.")
    if not filtered:
        st.info("Aucune anomalie ne correspond à ces filtres.")
        return

    header = st.columns([1.2, 1.2, 1.3, 1.3, 1.2])
    for column, title in zip(
        header, ["Sévérité", "Table", "Colonne", "Type", "Lignes concernées"]
    ):
        column.markdown(f"**{title}**")
    st.divider()
    for issue in filtered:
        cells = st.columns([1.2, 1.2, 1.3, 1.3, 1.2])
        with cells[0]:
            badge(str(issue["severite"]), _SEVERITES.get(str(issue["severite"]), "Inconnue"))
        cells[1].write(issue["table_name"])
        cells[2].write(issue["column_name"] or "—")
        cells[3].write(str(issue["type_anomalie"]).replace("_", " ").title())
        cells[4].write(int(issue["nb_lignes"]))
        st.divider()
