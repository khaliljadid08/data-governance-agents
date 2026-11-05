"""Composants visuels partagés par les pages Streamlit."""

from __future__ import annotations

from collections.abc import Sequence
from html import escape
from typing import Any

import pandas as pd
import streamlit as st


_STATUTS = {
    "en_attente": ("En attente", "🟡"),
    "en_cours": ("En cours", "🔵"),
    "a_valider": ("À valider", "🟠"),
    "valide": ("Validé", "🟢"),
    "rejete": ("Rejeté", "🔴"),
    "succes": ("Succès", "🟢"),
    "echec": ("Échec", "🔴"),
}


def afficher_badge(statut: str) -> None:
    """Affiche un statut sous forme de badge coloré."""
    libelle, symbole = _STATUTS.get(statut, (statut.replace("_", " ").title(), "⚪"))
    couleur = {
        "🟡": "#8a6d00",
        "🔵": "#145a8d",
        "🟠": "#995500",
        "🟢": "#176b37",
        "🔴": "#a12622",
        "⚪": "#555555",
    }.get(symbole, "#555555")
    st.markdown(
        f'<span style="display:inline-block;padding:0.2rem 0.65rem;'
        f'border-radius:1rem;background:{couleur};color:white;font-weight:600">'
        f"{symbole} {escape(libelle)}</span>",
        unsafe_allow_html=True,
    )


def afficher_metriques(valeurs: Sequence[tuple[str, Any]]) -> None:
    """Présente des indicateurs dans des colonnes de largeur égale."""
    columns = st.columns(len(valeurs)) if valeurs else []
    for column, (label, value) in zip(columns, valeurs):
        column.metric(label, value)


def afficher_tableau(
    donnees: Sequence[dict[str, Any]] | pd.DataFrame,
    message_vide: str = "Aucune donnée à afficher.",
    hauteur: int | None = 420,
) -> None:
    """Affiche un tableau ou un message clair si aucun résultat n'est disponible."""
    dataframe = donnees if isinstance(donnees, pd.DataFrame) else pd.DataFrame(donnees)
    if dataframe.empty:
        st.info(message_vide)
        return
    st.dataframe(dataframe, width="stretch", hide_index=True, height=hauteur)
