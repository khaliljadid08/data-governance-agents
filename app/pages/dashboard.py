"""Tableau de bord des indicateurs de la dernière analyse."""

from __future__ import annotations

import logging

import pandas as pd
import streamlit as st

from app import data_access
from ui.components import render_agent_card, render_distribution_card, render_page_header


logger = logging.getLogger(__name__)
_PENALITES = {"faible": 1, "moyenne": 3, "elevee": 6, "haute": 6, "critique": 10}
_AGENTS = (
    ("qualite", "Q", "Quality", "blue", "/anomalies", "Voir les anomalies"),
    ("classification", "C", "Classification", "teal", "/gouvernance", "Voir les résultats"),
    ("securisation", "S", "Security", "orange", "/gouvernance", "Voir les alertes"),
    ("lignage", "L", "Lineage", "green", "/gouvernance", "Voir le lignage"),
    ("documentation", "D", "Documentation", "purple", "/gouvernance", "Voir la documentation"),
)


def _choisir_run(pairs: list[dict]) -> dict | None:
    """Retourne le run sélectionné parmi les plus récents."""
    ordered = sorted(pairs, key=lambda pair: int(pair["run"]["id"]), reverse=True)
    if not ordered:
        return None
    run_ids = [pair["run"]["id"] for pair in ordered]
    current = st.session_state.get("run_id_courant")
    default = run_ids.index(current) if current in run_ids else 0
    selected_id = st.selectbox(
        "Analyse affichée",
        run_ids,
        index=default,
        format_func=lambda value: f"Run {value} · itération "
        f"{next(p['run']['numero_iteration'] for p in ordered if p['run']['id'] == value)}",
    )
    return next(pair for pair in ordered if pair["run"]["id"] == selected_id)


def _render_agent_grid(results: list[dict]) -> None:
    """Affiche les résultats connus des cinq agents en cartes."""
    by_agent = {str(result["agent"]): result for result in results}
    for offset in range(0, len(_AGENTS), 3):
        columns = st.columns(3)
        for column, definition in zip(columns, _AGENTS[offset : offset + 3]):
            agent_id, letter, name, color, href, link = definition
            result = by_agent.get(agent_id)
            status = "SUCCESS" if result and result["statut"] == "succes" else "FAILED"
            summary = (
                str(result.get("resume") or "Aucun résumé disponible.")
                if result
                else "Cet agent n'a pas été exécuté pour cette analyse."
            )
            with column:
                render_agent_card(letter, name, status, summary, href, link, color)


def _repartition(
    values: list[str], normalize_severity: bool = False
) -> list[tuple[str, int, str]]:
    """Calcule les comptes à afficher et leur couleur."""
    counts = pd.Series(values, dtype="string").value_counts()
    result = []
    for label, count in counts.items():
        name = str(label)
        tone = "blue"
        if normalize_severity:
            if name.casefold() in ("moyenne", "medium"):
                name, tone = "MEDIUM", "orange"
            elif name.casefold() in ("haute", "elevee", "high"):
                name, tone = "HIGH", "red"
            elif name.casefold() in ("critique", "critical"):
                name, tone = "CRITICAL", "red"
            else:
                name = name.upper()
        else:
            name = name.replace("_", " ").upper()
        result.append((name, int(count), tone))
    return result


def render() -> None:
    """Affiche les agents et répartitions associés à un run."""
    try:
        pairs = data_access.lister_demandes_et_runs(str(data_access.GOVERNANCE_DB))
    except Exception as erreur:
        logger.exception("Impossible de charger le dashboard.")
        st.error(f"Impossible de charger le dashboard : {erreur}")
        return
    if not pairs:
        render_page_header(
            "VUE D'ENSEMBLE",
            "Dashboard",
            "Aucune analyse lancée. Commencez par importer un fichier.",
        )
        return

    selected = _choisir_run(pairs)
    if selected is None:
        st.info("Aucune analyse lancée. Commencez par importer un fichier.")
        return
    run = selected["run"]
    run_id = int(run["id"])
    header, action = st.columns([4, 1.4], vertical_alignment="center")
    with header:
        render_page_header(
            "VUE D'ENSEMBLE",
            "Dashboard",
            f"Run {run_id} · itération {run['numero_iteration']}",
            str(run["statut"]).replace("_", " ").title(),
        )
    with action:
        validation_page = st.session_state.get("_governia_pages", {}).get("Validation")
        if validation_page is not None:
            st.page_link(
                validation_page,
                label="Valider l'analyse →",
                width="stretch",
            )

    try:
        issues = data_access.lire_anomalies(str(data_access.GOVERNANCE_DB), run_id)
        findings = data_access.lire_constats_securite(
            str(data_access.GOVERNANCE_DB), run_id
        )
        classifications = data_access.lire_classifications(
            str(data_access.GOVERNANCE_DB), run_id
        )
        agent_results = data_access.lire_resultats_agents(
            str(data_access.GOVERNANCE_DB), run_id
        )
    except Exception as erreur:
        logger.exception("Impossible de lire les résultats du run %s.", run_id)
        st.error(f"Impossible de lire les résultats : {erreur}")
        return

    severity_penalty = sum(
        _PENALITES.get(str(issue["severite"]).casefold(), 3) for issue in issues
    )
    quality_score = max(0, 100 - severity_penalty)
    non_compliant = sum(not bool(item["conforme_regle_acces"]) for item in findings)
    table_count = len(
        [
            item.strip()
            for item in str((selected.get("request") or {}).get("perimetre", "")).split(",")
            if item.strip()
        ]
    )
    metrics = st.columns(4)
    metrics[0].metric("Score qualité indicatif", f"{quality_score}/100")
    metrics[1].metric("Anomalies", len(issues))
    metrics[2].metric("Colonnes sensibles", f"{len(findings)} · {non_compliant} non conformes")
    metrics[3].metric("Tables analysées", table_count)

    st.markdown(
        '<div class="ui-section-heading"><div class="ui-eyebrow">'
        "TRAITEMENT MULTI-AGENTS</div><h2>Agents</h2></div>",
        unsafe_allow_html=True,
    )
    _render_agent_grid(agent_results)

    st.markdown(
        '<div class="ui-section-heading"><div class="ui-eyebrow">'
        "ANALYSE QUANTITATIVE</div><h2>Répartition des résultats</h2></div>",
        unsafe_allow_html=True,
    )
    type_rows = _repartition([str(issue["type_anomalie"]) for issue in issues])
    severity_rows = _repartition(
        [str(issue["severite"]) for issue in issues],
        normalize_severity=True,
    )
    class_rows = _repartition(
        [str(item["categorie"]) for item in classifications]
    )
    distribution_columns = st.columns(3)
    with distribution_columns[0]:
        render_distribution_card("Anomalies par type", type_rows)
    with distribution_columns[1]:
        render_distribution_card("Anomalies par gravité", severity_rows)
    with distribution_columns[2]:
        render_distribution_card("Classifications", class_rows)

    st.caption(
        "Le score qualité est un indicateur pondéré, et les totaux affichés "
        "correspondent aux constats enregistrés pour ce run."
    )
