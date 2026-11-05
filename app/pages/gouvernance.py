"""Consultation des classifications, constats de sécurité, lignage et dictionnaire."""

from __future__ import annotations

import json
import logging

import pandas as pd
import streamlit as st

from app import data_access
from app.components import afficher_tableau, badge, section_title


logger = logging.getLogger(__name__)


def _echapper_graphviz(value: object) -> str:
    """Échappe les caractères spéciaux utilisés par Graphviz."""
    return (
        str(value or "")
        .replace("\\", "\\\\")
        .replace('"', '\\"')
        .replace("\n", " ")
    )


def _avis_agent(results: list[dict], agent_id: str) -> None:
    """Présente l'avis consultatif sauvegardé par un agent."""
    result = next((item for item in results if item["agent"] == agent_id), None)
    if result is None:
        return
    try:
        details = json.loads(result.get("details_json") or "{}")
    except (TypeError, json.JSONDecodeError):
        logger.exception("Les détails de l'agent %s sont illisibles.", agent_id)
        st.warning("Les détails de l'analyse sont illisibles.")
        return
    advice = details.get("avis_gemini")
    if not isinstance(advice, dict):
        return
    with st.expander("Avis consultatif Gemini", expanded=False):
        if advice.get("statut") == "succes":
            st.info(advice.get("avis", "Aucun avis retourné."))
        elif advice.get("statut") == "echec":
            st.warning(f"Avis Gemini indisponible : {advice.get('erreur', 'erreur inconnue')}")
        else:
            st.caption("Gemini est désactivé ; les règles locales restent actives.")


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


def render() -> None:
    """Affiche les quatre volets de gouvernance d'un run."""
    section_title(
        "Gouvernance",
        "MÉTADONNÉES",
        "Explorez les classifications, contrôles de sécurité, relations et descriptions.",
    )
    try:
        pairs = data_access.lister_demandes_et_runs(
            str(data_access.GOVERNANCE_DB)
        )
    except Exception as erreur:
        logger.exception("Impossible de charger les analyses de gouvernance.")
        st.error(f"Impossible de charger les analyses : {erreur}")
        return
    if not pairs:
        st.info("Aucune analyse lancée. Commencez par importer un fichier.")
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
        dictionary = data_access.lire_dictionnaire(
            str(data_access.GOVERNANCE_DB)
        )
        agent_results = data_access.lire_resultats_agents(
            str(data_access.GOVERNANCE_DB), run_id
        )
    except Exception as erreur:
        logger.exception("Impossible de lire la gouvernance du run %s.", run_id)
        st.error(f"Impossible de lire les résultats de gouvernance : {erreur}")
        return

    classification_tab, security_tab, lineage_tab, dictionary_tab = st.tabs(
        ["Classification", "Sécurité", "Lignage", "Dictionnaire de données"]
    )
    with classification_tab:
        _avis_agent(agent_results, "classification")
        afficher_tableau(
            classifications,
            "Aucune classification n'est enregistrée pour ce run.",
        )

    with security_tab:
        _avis_agent(agent_results, "securisation")
        non_compliant = [
            item for item in findings if not bool(item["conforme_regle_acces"])
        ]
        left, right = st.columns(2)
        left.metric("Colonnes sensibles", len(findings))
        right.metric("Non conformes", len(non_compliant))
        if not findings:
            st.info("Aucun constat de sécurité n'est enregistré pour ce run.")
        else:
            for item in findings:
                columns = st.columns([1.5, 1.5, 1.4, 1.3, 3.3])
                columns[0].write(f"**{item['table_name']}**")
                columns[1].write(item["column_name"])
                columns[2].write(item["type_donnee"])
                with columns[3]:
                    badge(
                        "conforme" if bool(item["conforme_regle_acces"]) else "non conforme",
                        "Conforme" if bool(item["conforme_regle_acces"]) else "Non conforme",
                    )
                columns[4].write(item["recommandation"] or "—")

    with lineage_tab:
        _avis_agent(agent_results, "lignage")
        if not edges:
            st.info("Aucune relation de lignage n'est enregistrée pour ce run.")
        else:
            tables = sorted(
                {
                    str(node)
                    for edge in edges
                    for node in (edge["source_table"], edge["target_table"])
                }
            )
            node_ids = {name: f"table_{index}" for index, name in enumerate(tables)}
            graph = ["digraph lignage {", "rankdir=LR;", "node [shape=box];"]
            for name in tables:
                graph.append(
                    f'{node_ids[name]} [label="{_echapper_graphviz(name)}"];'
                )
            for edge in edges:
                label = (
                    f"{edge['source_column'] or '*'} → "
                    f"{edge['target_column'] or '*'} ({edge['type_relation']})"
                )
                graph.append(
                    f'{node_ids[edge["source_table"]]} -> '
                    f'{node_ids[edge["target_table"]]} '
                    f'[label="{_echapper_graphviz(label)}"];'
                )
            graph.append("}")
            st.graphviz_chart("\n".join(graph), width="stretch")
            afficher_tableau(edges)

    with dictionary_tab:
        perimeter = {
            table.strip()
            for table in str((pair.get("request") or {}).get("perimetre", "")).split(",")
            if table.strip()
        }
        entries = [
            item
            for item in dictionary
            if item["table_name"] in perimeter
        ]
        filter_columns = st.columns([2, 1])
        with filter_columns[0]:
            query = st.text_input(
                "Rechercher une table, une colonne ou une description",
                key=f"dictionary_query_{run_id}",
            ).casefold()
        with filter_columns[1]:
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
        afficher_tableau(filtered, "Aucune entrée de dictionnaire ne correspond.")
        if filtered:
            csv_data = pd.DataFrame(filtered).to_csv(
                index=False,
                encoding="utf-8-sig",
            )
            st.download_button(
                "Exporter le dictionnaire en CSV",
                csv_data,
                file_name=f"govern-ia-dictionnaire-run-{run_id}.csv",
                mime="text/csv",
            )
