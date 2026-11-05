"""Consultation des classifications, alertes, lignage et dictionnaire."""

from __future__ import annotations

import logging

import pandas as pd
import streamlit as st

from app import data_access
from ui.components import (
    render_card,
    render_page_header,
    render_table,
    render_timeline_item,
)


logger = logging.getLogger(__name__)


def _selected_run(pairs: list[dict]) -> dict | None:
    """Affiche le choix de run et retourne la sélection."""
    ordered = sorted(pairs, key=lambda pair: pair["run"]["id"], reverse=True)
    if not ordered:
        return None
    ids = [pair["run"]["id"] for pair in ordered]
    current = st.session_state.get("run_id_courant")
    index = ids.index(current) if current in ids else 0
    selected_id = st.selectbox("Analyse", ids, index=index, key="governance_run")
    return next(pair for pair in ordered if pair["run"]["id"] == selected_id)


def _section_header(kicker: str, title: str, count: int, unit: str) -> None:
    """Affiche le titre numéroté et le compteur d'une carte de gouvernance."""
    left, right = st.columns([4, 1], vertical_alignment="center")
    with left:
        st.markdown(
            f'<div class="ui-eyebrow">{kicker}</div>'
            f'<h2 class="ui-section-card-title">{title}</h2>',
            unsafe_allow_html=True,
        )
    with right:
        st.markdown(
            f'<div class="ui-header-badge">{count} {unit}</div>',
            unsafe_allow_html=True,
        )


def render() -> None:
    """Affiche les trois sections de gouvernance et le dictionnaire associé."""
    try:
        pairs = data_access.lister_demandes_et_runs(str(data_access.GOVERNANCE_DB))
    except Exception as erreur:
        logger.exception("Impossible de charger les analyses de gouvernance.")
        st.error(f"Impossible de charger les analyses : {erreur}")
        return
    if not pairs:
        render_page_header(
            "MÉTADONNÉES",
            "Gouvernance",
            "Aucune analyse lancée. Commencez par importer un fichier.",
        )
        return
    pair = _selected_run(pairs)
    if pair is None:
        st.info("Aucun résultat de gouvernance n'est disponible.")
        return
    run_id = int(pair["run"]["id"])

    try:
        classifications = data_access.lire_classifications(
            str(data_access.GOVERNANCE_DB), run_id
        )
        findings = data_access.lire_constats_securite(
            str(data_access.GOVERNANCE_DB), run_id
        )
        edges = data_access.lire_lignage(str(data_access.GOVERNANCE_DB), run_id)
        agent_results = data_access.lire_resultats_agents(
            str(data_access.GOVERNANCE_DB), run_id
        )
        dictionary = data_access.lire_dictionnaire(str(data_access.GOVERNANCE_DB))
    except Exception as erreur:
        logger.exception("Impossible de lire la gouvernance du run %s.", run_id)
        st.error(f"Impossible de lire les résultats de gouvernance : {erreur}")
        return

    header, action = st.columns([4, 1.5], vertical_alignment="center")
    with header:
        render_page_header(
            "GOUVERNANCE DES DONNÉES",
            "Classification, sécurité et lignage",
            f"Résultats du run {run_id}",
        )
    with action:
        dashboard_page = st.session_state.get("_governia_pages", {}).get("Dashboard")
        if dashboard_page is not None:
            st.page_link(dashboard_page, label="← Retour au dashboard")

    with render_card(f"classification-{run_id}"):
        _section_header("01 · CLASSIFICATION", "Nature des colonnes", len(classifications), "colonnes")
        classification_rows = [
            (
                f"{item['table_name']}.{item['column_name']}",
                str(item["categorie"]).upper(),
                f"{float(item['confiance'] or 0) * 100:.0f} %",
            )
            for item in classifications
        ]
        render_table(
            ["Colonne", "Classification", "Confiance"],
            classification_rows,
            badge_columns={1: "category"},
            empty_message="Aucune classification n'est enregistrée pour ce run.",
        )

    with render_card(f"security-{run_id}"):
        _section_header("02 · SÉCURITÉ", "Alertes et recommandations", len(findings), "alertes")
        security_rows = [
            (
                f"{item['table_name']}.{item['column_name']}",
                str(item["type_donnee"]).upper(),
                item["recommandation"] or "—",
                "Conforme" if bool(item["conforme_regle_acces"]) else "Non conforme",
            )
            for item in findings
        ]
        render_table(
            ["Colonne", "Type d'alerte", "Recommandation", "Conformité"],
            security_rows,
            badge_columns={3: "compliance"},
            empty_message="Aucune alerte de sécurité n'est enregistrée pour ce run.",
        )

    with render_card(f"lineage-{run_id}"):
        _section_header("03 · LIGNAGE", "Relations détectées", len(edges), "relations")
        if not edges:
            st.info("Aucune relation de lignage n'est enregistrée pour ce run.")
        else:
            lineage_result = next(
                (item for item in agent_results if item["agent"] == "lignage"),
                {},
            )
            recorded_at = str(lineage_result.get("created_at") or "")
            for edge in edges:
                source_column = edge.get("source_column") or "*"
                target_column = edge.get("target_column") or "*"
                render_timeline_item(
                    str(edge["type_relation"]),
                    f"{edge['source_table']}.{source_column} → "
                    f"{edge['target_table']}.{target_column}",
                    recorded_at,
                )
            st.caption("Horodatage de l'enregistrement des résultats de l'agent.")

        perimeter = {
            table.strip()
            for table in str((pair.get("request") or {}).get("perimetre", "")).split(",")
            if table.strip()
        }
        entries = [item for item in dictionary if item["table_name"] in perimeter]
        with st.expander(f"Dictionnaire de données · {len(entries)} colonnes"):
            query = st.text_input(
                "Rechercher une table, une colonne ou une description",
                key=f"dictionary_query_{run_id}",
            ).casefold()
            sensitivities = sorted(
                {str(item.get("sensibilite") or "public") for item in entries}
            )
            sensitivity = st.selectbox(
                "Sensibilité",
                ["Toutes", *sensitivities],
                key=f"dictionary_sensitivity_{run_id}",
            )
            filtered = [
                item
                for item in entries
                if (
                    not query
                    or query
                    in " ".join(
                        str(item.get(key) or "")
                        for key in ("table_name", "column_name", "description")
                    ).casefold()
                )
                and (
                    sensitivity == "Toutes"
                    or item.get("sensibilite") == sensitivity
                )
            ]
            render_table(
                ["Table", "Colonne", "Description", "Type SQL", "Catégorie", "Sensibilité"],
                [
                    (
                        item["table_name"],
                        item["column_name"],
                        item.get("description"),
                        item.get("type_sql"),
                        item.get("categorie"),
                        item.get("sensibilite"),
                    )
                    for item in filtered
                ],
                empty_message="Aucune entrée ne correspond à la recherche.",
            )
            if filtered:
                dataframe = pd.DataFrame(filtered)
                st.download_button(
                    "Télécharger le dictionnaire CSV",
                    dataframe.to_csv(index=False).encode("utf-8-sig"),
                    file_name=f"dictionnaire_run_{run_id}.csv",
                    mime="text/csv",
                )
