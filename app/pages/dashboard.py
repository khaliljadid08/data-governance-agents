"""Tableau de bord des indicateurs de la dernière analyse."""

from __future__ import annotations

import logging
from html import escape

import pandas as pd
import streamlit as st

from app import data_access
from app.components import badge, kpi_card, section_title


logger = logging.getLogger(__name__)
_PENALITES = {"faible": 1, "moyenne": 3, "elevee": 6, "haute": 6, "critique": 10}
_COULEURS_SEVERITE = {
    "moyenne": "#f59e0b",
    "elevee": "#ef4444",
    "haute": "#ef4444",
    "critique": "#b91c1c",
}


def _afficher_barres(repartition: pd.Series, par_severite: bool = False) -> None:
    """Affiche une répartition sous forme de barres horizontales simples."""
    maximum = int(repartition.max())
    lignes = []
    for libelle, valeur in repartition.items():
        nom = str(libelle)
        nombre = int(valeur)
        largeur = round(nombre / maximum * 100)
        couleur = (
            _COULEURS_SEVERITE.get(nom.casefold(), "#2563eb")
            if par_severite
            else "#2563eb"
        )
        lignes.append(
            '<div class="governia-bar-row">'
            f'<div class="governia-bar-label"><span>{escape(nom)}</span>'
            f"<strong>{nombre}</strong></div>"
            '<div class="governia-bar-track">'
            f'<span class="governia-bar-fill" style="width:{largeur}%;'
            f"background:{couleur};\"></span></div></div>"
        )
    st.markdown("".join(lignes), unsafe_allow_html=True)


def _choisir_run(pairs: list[dict]) -> tuple[dict | None, list[dict]]:
    """Retourne le run sélectionné parmi les plus récents."""
    ordered = sorted(
        pairs,
        key=lambda pair: int(pair["run"]["id"]),
        reverse=True,
    )
    if not ordered:
        return None, ordered
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
    return next(pair for pair in ordered if pair["run"]["id"] == selected_id), ordered


def render() -> None:
    """Affiche les indicateurs et graphiques associés à un run."""
    section_title(
        "Dashboard",
        "VUE D'ENSEMBLE",
        "Un aperçu des résultats de gouvernance de votre dernière analyse.",
    )
    try:
        pairs = data_access.lister_demandes_et_runs(
            str(data_access.GOVERNANCE_DB)
        )
    except Exception as erreur:
        logger.exception("Impossible de charger le dashboard.")
        st.error(f"Impossible de charger le dashboard : {erreur}")
        return
    if not pairs:
        st.info("Aucune analyse lancée. Commencez par importer un fichier.")
        return

    selected, _ = _choisir_run(pairs)
    if selected is None:
        st.info("Aucune analyse lancée. Commencez par importer un fichier.")
        return
    run = selected["run"]
    run_id = int(run["id"])
    request = selected.get("request") or {}
    try:
        issues = data_access.lire_anomalies(
            str(data_access.GOVERNANCE_DB), run_id
        )
        findings = data_access.lire_constats_securite(
            str(data_access.GOVERNANCE_DB), run_id
        )
    except Exception as erreur:
        logger.exception("Impossible de lire les indicateurs du run %s.", run_id)
        st.error(f"Impossible de lire les résultats : {erreur}")
        return

    severity_penalty = sum(
        _PENALITES.get(str(issue["severite"]).casefold(), 3)
        for issue in issues
    )
    quality_score = max(0, 100 - severity_penalty)
    non_compliant = sum(not bool(item["conforme_regle_acces"]) for item in findings)
    table_count = len(
        [
            item.strip()
            for item in str(request.get("perimetre", "")).split(",")
            if item.strip()
        ]
    )

    columns = st.columns(5)
    with columns[0]:
        kpi_card("Score qualité indicatif", f"{quality_score}/100", "Pénalité pondérée par sévérité")
    with columns[1]:
        kpi_card("Anomalies", len(issues), "constats qualité")
    with columns[2]:
        kpi_card("Colonnes sensibles", len(findings), f"{non_compliant} non conforme(s)")
    with columns[3]:
        kpi_card("Tables analysées", table_count, str(request.get("perimetre", "—")))
    with columns[4]:
        kpi_card("Statut du run", str(run["statut"]).replace("_", " ").title())
        badge(str(run["statut"]))
    st.caption(
        "Le score est un indicateur visuel (100 moins les pénalités de sévérité) ; "
        "il ne remplace pas l'examen des constats."
    )

    st.divider()
    chart_columns = st.columns(2)
    by_type = pd.Series(
        [str(issue["type_anomalie"]).replace("_", " ").title() for issue in issues],
        dtype="string",
    ).value_counts().rename("Anomalies")
    by_severity = pd.Series(
        [str(issue["severite"]).replace("_", " ").title() for issue in issues],
        dtype="string",
    ).value_counts().rename("Constats")
    with chart_columns[0]:
        section_title("Anomalies par type")
        if by_type.empty:
            st.info("Aucune anomalie de qualité pour ce run.")
        else:
            _afficher_barres(by_type)
    with chart_columns[1]:
        section_title("Anomalies par sévérité")
        if by_severity.empty:
            st.info("Aucune anomalie de qualité pour ce run.")
        else:
            _afficher_barres(by_severity, par_severite=True)
