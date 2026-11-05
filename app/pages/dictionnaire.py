"""Consultation, recherche et export du dictionnaire de données."""

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


def render() -> None:
    """Affiche les entrées documentées avec recherche, filtre et export CSV."""
    st.title("Dictionnaire de données")
    try:
        entries = data_access.lire_dictionnaire(str(data_access.GOVERNANCE_DB))
    except Exception as erreur:
        logger.exception("Impossible de lire le dictionnaire.")
        st.error(f"Impossible de charger le dictionnaire : {erreur}")
        return

    if not entries:
        st.info("Le dictionnaire est vide. Lancez une analyse pour le générer.")
        return

    dataframe = pd.DataFrame(entries)
    sensitivities = sorted(
        {
            str(value)
            for value in dataframe["sensibilite"].dropna().tolist()
            if str(value).strip()
        }
    )
    search_col, sensitivity_col = st.columns([2, 1])
    with search_col:
        search = st.text_input(
            "Rechercher une table, une colonne ou une description"
        ).casefold()
    with sensitivity_col:
        sensitivity = st.selectbox(
            "Sensibilité", ["Toutes", *sensitivities]
        )

    visible = dataframe
    if search:
        searchable_columns = [
            column
            for column in ("table_name", "column_name", "description", "categorie")
            if column in visible.columns
        ]
        mask = visible[searchable_columns].fillna("").astype(str).apply(
            lambda column: column.str.casefold().str.contains(search, regex=False)
        )
        visible = visible[mask.any(axis=1)]
    if sensitivity != "Toutes":
        visible = visible[visible["sensibilite"] == sensitivity]

    st.caption(f"{len(visible)} entrée(s) affichée(s) sur {len(dataframe)}.")
    afficher_tableau(visible, "Aucune entrée ne correspond à ces filtres.")
    st.download_button(
        "Télécharger le résultat au format CSV",
        data=visible.to_csv(index=False).encode("utf-8-sig"),
        file_name="dictionnaire_donnees.csv",
        mime="text/csv",
        disabled=visible.empty,
    )
