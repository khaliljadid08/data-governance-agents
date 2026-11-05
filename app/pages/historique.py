"""Consultation des journaux d'audit et des validations humaines."""

from __future__ import annotations

import logging

import pandas as pd
import streamlit as st

if __package__ == "app.pages":
    from .. import data_access
    from ..components import afficher_tableau
else:
    import data_access
    from components import afficher_tableau


logger = logging.getLogger(__name__)


def _options(dataframe: pd.DataFrame, column: str) -> list[str]:
    """Construit les filtres à partir des valeurs non vides d'une colonne."""
    if dataframe.empty or column not in dataframe:
        return []
    return sorted(
        {
            str(value)
            for value in dataframe[column].dropna().tolist()
            if str(value).strip()
        }
    )


def render() -> None:
    """Affiche les événements d'audit et décisions avec des filtres simples."""
    st.title("Historique et audit")
    try:
        audit = pd.DataFrame(
            data_access.lire_journal_audit(str(data_access.GOVERNANCE_DB))
        )
        validations = pd.DataFrame(
            data_access.lire_validations(str(data_access.GOVERNANCE_DB))
        )
    except Exception as erreur:
        logger.exception("Impossible de charger l'historique.")
        st.error(f"Impossible de charger l'historique : {erreur}")
        return

    audit_tab, validations_tab = st.tabs(["Journal d'audit", "Validations"])
    with audit_tab:
        st.subheader("Actions du système")
        if audit.empty:
            st.info("Aucune action n'est enregistrée dans le journal d'audit.")
        else:
            actor_col, action_col, entity_col = st.columns(3)
            with actor_col:
                actor = st.selectbox(
                    "Acteur", ["Tous", *_options(audit, "acteur")]
                )
            with action_col:
                action = st.selectbox(
                    "Action", ["Toutes", *_options(audit, "action")]
                )
            with entity_col:
                entity = st.selectbox(
                    "Entité", ["Toutes", *_options(audit, "entite")]
                )

            visible_audit = audit
            if actor != "Tous":
                visible_audit = visible_audit[visible_audit["acteur"] == actor]
            if action != "Toutes":
                visible_audit = visible_audit[visible_audit["action"] == action]
            if entity != "Toutes":
                visible_audit = visible_audit[visible_audit["entite"] == entity]
            afficher_tableau(visible_audit)

    with validations_tab:
        st.subheader("Décisions des reviewers")
        if validations.empty:
            st.info("Aucune décision de validation n'est enregistrée.")
        else:
            role_col, decision_col, reviewer_col = st.columns(3)
            with role_col:
                role = st.selectbox(
                    "Rôle", ["Tous", *_options(validations, "role")]
                )
            with decision_col:
                decision = st.selectbox(
                    "Décision", ["Toutes", *_options(validations, "decision")]
                )
            with reviewer_col:
                reviewer = st.selectbox(
                    "Reviewer", ["Tous", *_options(validations, "reviewer")]
                )

            visible_validations = validations
            if role != "Tous":
                visible_validations = visible_validations[
                    visible_validations["role"] == role
                ]
            if decision != "Toutes":
                visible_validations = visible_validations[
                    visible_validations["decision"] == decision
                ]
            if reviewer != "Tous":
                visible_validations = visible_validations[
                    visible_validations["reviewer"] == reviewer
                ]
            afficher_tableau(visible_validations)
