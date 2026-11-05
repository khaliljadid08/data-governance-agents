"""Exploration filtrable et paginée des constats de qualité."""

from __future__ import annotations

import logging

import streamlit as st

from app import data_access
from ui.components import render_card, render_page_header, render_table


logger = logging.getLogger(__name__)
_PAGE_SIZE = 25
_SEVERITES = {
    "faible": "LOW",
    "moyenne": "MEDIUM",
    "elevee": "HIGH",
    "haute": "HIGH",
    "critique": "CRITICAL",
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


def _reset_filters(run_id: int) -> None:
    """Réinitialise les filtres et la pagination."""
    for key in (
        f"anomalies_filter_type_{run_id}",
        f"anomalies_filter_severity_{run_id}",
        f"anomalies_filter_column_{run_id}",
    ):
        st.session_state.pop(key, None)
    st.session_state[f"anomalies_applied_filters_{run_id}"] = {
        "type": "Tous",
        "severity": "Toutes",
        "column": "",
    }
    st.session_state[f"anomalies_page_{run_id}"] = 0


def render() -> None:
    """Filtre et présente les anomalies par pages de 25 constats."""
    try:
        pairs = data_access.lister_demandes_et_runs(str(data_access.GOVERNANCE_DB))
    except Exception as erreur:
        logger.exception("Impossible de charger les runs pour les anomalies.")
        st.error(f"Impossible de charger les analyses : {erreur}")
        return
    if not pairs:
        render_page_header(
            "QUALITÉ DES DONNÉES",
            "Anomalies détectées : 0",
            "Aucune analyse lancée. Commencez par importer un fichier.",
        )
        return
    pair = _selected_run(pairs)
    if pair is None:
        st.info("Aucune anomalie à afficher.")
        return

    run_id = int(pair["run"]["id"])
    try:
        issues = data_access.lire_anomalies(str(data_access.GOVERNANCE_DB), run_id)
    except Exception as erreur:
        logger.exception("Impossible de lire les anomalies du run %s.", run_id)
        st.error(f"Impossible de lire les anomalies : {erreur}")
        return

    perimeter = str((pair.get("request") or {}).get("perimetre", ""))
    header, action = st.columns([4, 1.4], vertical_alignment="center")
    with header:
        render_page_header(
            "QUALITÉ DES DONNÉES",
            f"Anomalies détectées : {len(issues)}",
            f"{len(issues)} constat(s) enregistré(s) · {perimeter or 'Source inconnue'}",
        )
    with action:
        dashboard_page = st.session_state.get("_governia_pages", {}).get("Dashboard")
        if dashboard_page is not None:
            st.page_link(dashboard_page, label="← Retour au dashboard")

    if not issues:
        st.info("Aucune anomalie de qualité n'a été détectée pour ce run.")
        return

    types = sorted({str(row["type_anomalie"]) for row in issues})
    severities = sorted({str(row["severite"]) for row in issues})
    with render_card(f"anomalies-filters-{run_id}"):
        with st.form(f"anomalies_filters_{run_id}"):
            fields = st.columns(3)
            with fields[0]:
                issue_type = st.selectbox(
                    "Type",
                    ["Tous", *types],
                    format_func=lambda value: value.replace("_", " ").upper()
                    if value != "Tous"
                    else value,
                    key=f"anomalies_filter_type_{run_id}",
                )
            with fields[1]:
                severity = st.selectbox(
                    "Gravité",
                    ["Toutes", *severities],
                    format_func=lambda value: (
                        "Toutes"
                        if value == "Toutes"
                        else _SEVERITES.get(value, value.upper())
                    ),
                    key=f"anomalies_filter_severity_{run_id}",
                )
            with fields[2]:
                column_query = st.text_input(
                    "Colonne",
                    placeholder="Rechercher une colonne",
                    key=f"anomalies_filter_column_{run_id}",
                )
            filter_button, _ = st.columns([1, 5])
            with filter_button:
                submitted = st.form_submit_button("Filtrer", type="primary")
        reset_button, _ = st.columns([1, 5])
        with reset_button:
            st.button(
                "Réinitialiser",
                on_click=_reset_filters,
                args=(run_id,),
            )

    applied_key = f"anomalies_applied_filters_{run_id}"
    if applied_key not in st.session_state:
        st.session_state[applied_key] = {
            "type": issue_type,
            "severity": severity,
            "column": column_query,
        }
    elif submitted:
        st.session_state[applied_key] = {
            "type": issue_type,
            "severity": severity,
            "column": column_query,
        }
        st.session_state[f"anomalies_page_{run_id}"] = 0

    filters = st.session_state[applied_key]
    filtered = [
        row
        for row in issues
        if (filters["type"] == "Tous" or row["type_anomalie"] == filters["type"])
        and (
            filters["severity"] == "Toutes"
            or row["severite"] == filters["severity"]
        )
        and filters["column"].casefold()
        in str(row.get("column_name") or "").casefold()
    ]
    page_count = max(1, (len(filtered) + _PAGE_SIZE - 1) // _PAGE_SIZE)
    page_key = f"anomalies_page_{run_id}"
    page = min(int(st.session_state.get(page_key, 0)), page_count - 1)
    st.session_state[page_key] = page
    first = page * _PAGE_SIZE
    page_rows = filtered[first : first + _PAGE_SIZE]
    st.markdown(
        f'<p class="ui-page-detail">{len(filtered)} résultat(s) affiché(s) '
        f"sur cette page de filtres · page {page + 1}/{page_count}</p>",
        unsafe_allow_html=True,
    )
    rows = [
        (
            row["table_name"],
            row.get("column_name") or "—",
            str(row["type_anomalie"]).replace("_", " ").upper(),
            int(row["nb_lignes"]),
            _SEVERITES.get(str(row["severite"]), str(row["severite"]).upper()),
        )
        for row in page_rows
    ]
    with render_card(f"anomalies-table-{run_id}"):
        render_table(
            ["Table", "Colonne", "Type d'anomalie", "Lignes concernées", "Gravité"],
            rows,
            badge_columns={4: "severity"},
            empty_message="Aucune anomalie ne correspond à ces filtres.",
        )

    if page_count > 1:
        previous, page_label, next_page = st.columns([1, 2, 1])
        with previous:
            st.button(
                "← Précédent",
                disabled=page == 0,
                on_click=lambda: st.session_state.update({page_key: max(0, page - 1)}),
            )
        with page_label:
            st.caption(f"Page {page + 1} sur {page_count}")
        with next_page:
            st.button(
                "Suivant →",
                disabled=page + 1 >= page_count,
                on_click=lambda: st.session_state.update(
                    {page_key: min(page_count - 1, page + 1)}
                ),
            )
