"""Consultation des résultats produits par les agents."""

from __future__ import annotations

import json
import logging

import pandas as pd
import streamlit as st

if __package__ == "app.pages":
    from .. import data_access
    from ..components import afficher_badge, afficher_tableau
else:
    import data_access
    from components import afficher_badge, afficher_tableau


logger = logging.getLogger(__name__)

_AGENT_IDS_PAR_ONGLET = {
    "qualite": "qualite",
    "classification": "classification",
    "securite": "securisation",
    "lignage": "lignage",
}


def _echapper_graphviz(value: object) -> str:
    """Échappe les caractères spéciaux d'un libellé Graphviz."""
    return str(value or "").replace("\\", "\\\\").replace('"', '\\"').replace("\n", " ")


def _afficher_avis_gemini(
    agents: list[dict[str, object]], agent_id: str
) -> None:
    """Affiche séparément l'avis consultatif d'un agent."""
    agent_result = next(
        (agent for agent in agents if agent["agent"] == agent_id), None
    )
    if agent_result is None:
        return
    try:
        details = json.loads(str(agent_result["details_json"]))
    except (KeyError, TypeError, json.JSONDecodeError):
        logger.exception("Les détails de l'agent %s ne sont pas lisibles.", agent_id)
        st.warning("Les détails consultatifs de cet agent sont illisibles.")
        return

    advice = details.get("avis_gemini")
    if not isinstance(advice, dict):
        return
    status = advice.get("statut")
    with st.expander("Avis consultatif Gemini", expanded=False):
        if status == "succes":
            st.info(str(advice.get("avis", "Aucun avis retourné.")))
        elif status == "echec":
            st.warning(f"Avis Gemini indisponible : {advice.get('erreur', 'erreur inconnue')}")
        elif status == "desactive":
            st.caption("Gemini est désactivé ; les règles locales restent actives.")


def _afficher_synthese_gemini(report: dict[str, object]) -> None:
    """Affiche l'avis du superviseur en le distinguant des décisions locales."""
    synthesis = report.get("synthese_gemini")
    if not isinstance(synthesis, dict):
        return
    with st.expander("Synthèse consultative Gemini", expanded=False):
        if synthesis.get("statut") == "succes":
            st.info(str(synthesis.get("avis", "Aucun avis retourné.")))
            st.caption(
                "Cet avis n'altère pas les résultats déterministes des agents."
            )
        elif synthesis.get("statut") == "echec":
            st.warning(
                "Synthèse Gemini indisponible : "
                f"{synthesis.get('erreur', 'erreur inconnue')}"
            )
        else:
            st.caption("Gemini est désactivé ; la synthèse locale reste disponible.")


def render() -> None:
    """Affiche les résultats d'un run dans des onglets spécialisés."""
    st.title("Résultats")
    try:
        pairs = data_access.lister_demandes_et_runs(str(data_access.GOVERNANCE_DB))
    except Exception as erreur:
        logger.exception("Impossible de charger les demandes et les runs.")
        st.error(f"Impossible de charger les résultats : {erreur}")
        return

    if not pairs:
        st.info("Aucun run n'est disponible. Lancez d'abord une nouvelle demande.")
        return

    def format_run(run_id: int) -> str:
        item = next(pair for pair in pairs if pair["run"]["id"] == run_id)
        request = item["request"] or {}
        return (
            f"Run {run_id} · demande {request.get('id', '?')} · "
            f"itération {item['run']['numero_iteration']} · {item['run']['statut']}"
        )

    available_ids = [pair["run"]["id"] for pair in pairs]
    current_run_id = st.session_state.get("run_id_courant")
    default_index = (
        available_ids.index(current_run_id)
        if current_run_id in available_ids
        else 0
    )
    run_id = st.selectbox(
        "Choisir un run",
        options=available_ids,
        index=default_index,
        format_func=format_run,
    )
    selected_pair = next(pair for pair in pairs if pair["run"]["id"] == run_id)
    run = selected_pair["run"]
    request = selected_pair["request"] or {}
    left, right = st.columns(2)
    with left:
        st.write(f"**Opérateur :** {request.get('operateur', '—')}")
        st.write(f"**Périmètre :** {request.get('perimetre', '—')}")
    with right:
        st.write(f"**Consigne :** {request.get('consigne', '—')}")
        afficher_badge(run["statut"])

    report_key = f"rapport_consolide_{run_id}"
    current_report = st.session_state.get(report_key)
    if current_report is None:
        recent_report = st.session_state.get("rapport_courant")
        if (
            isinstance(recent_report, dict)
            and recent_report.get("run_id") == run_id
        ):
            current_report = recent_report
        else:
            try:
                current_report = st.session_state["supervisor"].consolider(run_id)
            except Exception as erreur:
                logger.exception("Impossible de consolider le run %s.", run_id)
                st.error(f"La synthèse est indisponible : {erreur}")
                current_report = None
        if current_report is not None:
            st.session_state[report_key] = current_report
    if isinstance(current_report, dict):
        _afficher_synthese_gemini(current_report)

    try:
        agents = data_access.lire_resultats_agents(
            str(data_access.GOVERNANCE_DB), run_id
        )
        issues = data_access.lire_anomalies(str(data_access.GOVERNANCE_DB), run_id)
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
    except Exception as erreur:
        logger.exception("Impossible de charger les détails du run %s.", run_id)
        st.error(f"Impossible de lire les résultats du run : {erreur}")
        return

    with st.expander("État des agents", expanded=False):
        if not agents:
            st.info("Aucun résultat d'agent n'est enregistré pour ce run.")
        for agent in agents:
            col_name, col_status, col_summary = st.columns([1, 1, 4])
            col_name.write(agent["agent"])
            with col_status:
                afficher_badge(agent["statut"])
            col_summary.write(agent["resume"] or "—")

    quality_tab, classification_tab, security_tab, lineage_tab, docs_tab = st.tabs(
        ["Qualité", "Classification", "Sécurité", "Lignage", "Documentation"]
    )

    with quality_tab:
        st.subheader("Anomalies de qualité")
        _afficher_avis_gemini(agents, _AGENT_IDS_PAR_ONGLET["qualite"])
        if not issues:
            st.info("Aucune anomalie n'est enregistrée pour ce run.")
        else:
            severities = sorted({issue["severite"] for issue in issues})
            selected_severity = st.selectbox(
                "Filtrer par sévérité",
                ["Toutes", *severities],
                key=f"quality_severity_{run_id}",
            )
            filtered_issues = [
                issue
                for issue in issues
                if selected_severity == "Toutes"
                or issue["severite"] == selected_severity
            ]
            afficher_tableau(filtered_issues)
            chart_data = (
                pd.DataFrame(issues)
                .groupby("type_anomalie")
                .size()
                .rename("Nombre d'anomalies")
                .to_frame()
            )
            st.caption("Nombre d'anomalies par type")
            st.bar_chart(chart_data)

    with classification_tab:
        st.subheader("Classification des colonnes")
        _afficher_avis_gemini(agents, _AGENT_IDS_PAR_ONGLET["classification"])
        afficher_tableau(classifications, "Aucune classification enregistrée.")

    with security_tab:
        st.subheader("Sécurité et sensibilité")
        _afficher_avis_gemini(agents, _AGENT_IDS_PAR_ONGLET["securite"])
        if not findings:
            st.info("Aucun constat de sécurité n'est enregistré pour ce run.")
        else:
            non_conformes = [
                finding for finding in findings if not finding["conforme_regle_acces"]
            ]
            conformes = len(findings) - len(non_conformes)
            metric_columns = st.columns(3)
            metric_columns[0].metric("Colonnes sensibles", len(findings))
            metric_columns[1].metric("Conformes", conformes)
            metric_columns[2].metric("Non conformes", len(non_conformes))
            dataframe = pd.DataFrame(findings)
            dataframe["conforme_regle_acces"] = dataframe[
                "conforme_regle_acces"
            ].map({1: "Oui", 0: "Non", True: "Oui", False: "Non"})
            if non_conformes:
                st.dataframe(
                    dataframe.style.map(
                        lambda value: (
                            "background-color: #ffe0e0; color: #8b0000"
                            if value == "Non"
                            else ""
                        ),
                        subset=["conforme_regle_acces"],
                    ),
                    width="stretch",
                    hide_index=True,
                )
            else:
                afficher_tableau(dataframe)

    with lineage_tab:
        st.subheader("Relations de lignage")
        _afficher_avis_gemini(agents, _AGENT_IDS_PAR_ONGLET["lignage"])
        if not edges:
            st.info("Aucune relation de lignage n'est enregistrée pour ce run.")
        else:
            nodes = sorted(
                {
                    node
                    for edge in edges
                    for node in (edge["source_table"], edge["target_table"])
                }
            )
            node_ids = {name: f"table_{index}" for index, name in enumerate(nodes)}
            lines = ["digraph lignage {", "rankdir=LR;", "node [shape=box];"]
            for name in nodes:
                lines.append(
                    f'{node_ids[name]} [label="{_echapper_graphviz(name)}"];'
                )
            for edge in edges:
                label = (
                    f"{edge['source_column'] or '*'} → "
                    f"{edge['target_column'] or '*'} ({edge['type_relation']})"
                )
                lines.append(
                    f'{node_ids[edge["source_table"]]} -> '
                    f'{node_ids[edge["target_table"]]} '
                    f'[label="{_echapper_graphviz(label)}"];'
                )
            lines.append("}")
            st.graphviz_chart("\n".join(lines), width="stretch")
            afficher_tableau(edges)

    with docs_tab:
        st.subheader("Dictionnaire généré pour le périmètre")
        documentation_result = next(
            (agent for agent in agents if agent["agent"] == "documentation"), None
        )
        if documentation_result is not None:
            try:
                details = json.loads(str(documentation_result["details_json"]))
                source = details.get("source_descriptions")
            except (KeyError, TypeError, json.JSONDecodeError):
                logger.exception("Les détails de documentation sont illisibles.")
                source = None
            if source == "gemini":
                st.caption("Descriptions générées par Gemini à partir des métadonnées.")
            elif source == "gemini_avec_repli_local":
                st.warning(
                    "Gemini est indisponible ; les descriptions restantes ont été "
                    "générées localement à partir de gabarits. "
                    f"Détail : {details.get('gemini_erreur', 'erreur inconnue')}"
                )
            elif source == "gabarits_locaux":
                st.caption("Descriptions générées localement à partir de gabarits.")
        perimeter = {
            table.strip()
            for table in str(request.get("perimetre", "")).split(",")
            if table.strip()
        }
        run_entries = [
            entry
            for entry in dictionary
            if entry["table_name"] in perimeter
        ]
        st.caption(
            "Le dictionnaire conserve la version la plus récente de chaque colonne."
        )
        afficher_tableau(run_entries, "Aucune documentation n'est disponible.")
