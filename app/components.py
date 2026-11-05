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

_COULEURS = {
    "en_attente": "yellow",
    "en_cours": "blue",
    "a_valider": "orange",
    "valide": "green",
    "rejete": "red",
    "succes": "green",
    "echec": "red",
    "faible": "blue",
    "moyenne": "yellow",
    "elevee": "orange",
    "haute": "orange",
    "critique": "red",
    "public": "green",
    "interne": "blue",
    "confidentiel": "orange",
    "sensible": "red",
    "conforme": "green",
    "non conforme": "red",
}


def afficher_badge(statut: str) -> None:
    """Affiche un statut sous forme de badge coloré."""
    badge(statut)


def badge(valeur: str, libelle: str | None = None) -> None:
    """Affiche un badge coloré pour un statut, une sévérité ou une catégorie."""
    key = valeur.casefold()
    couleur = _COULEURS.get(key, "gray")
    text = libelle or _STATUTS.get(valeur, (valeur.replace("_", " ").title(), ""))[0]
    st.markdown(
        f'<span class="governia-badge {couleur}">{escape(text)}</span>',
        unsafe_allow_html=True,
    )


def kpi_card(label: str, value: str | int | float, detail: str = "") -> None:
    """Présente un indicateur clé sous forme de carte SaaS."""
    safe_detail = f'<div class="governia-kpi-label">{escape(detail)}</div>' if detail else ""
    st.markdown(
        '<div class="governia-card">'
        f'<div class="governia-kpi-label">{escape(label)}</div>'
        f'<div class="governia-kpi-value">{escape(str(value))}</div>'
        f"{safe_detail}</div>",
        unsafe_allow_html=True,
    )


def section_title(
    title: str, kicker: str = "", subtitle: str = ""
) -> None:
    """Affiche un titre de section et son contexte."""
    eyebrow = (
        f'<div class="governia-eyebrow">{escape(kicker)}</div>' if kicker else ""
    )
    description = (
        f'<p class="governia-section-subtitle">{escape(subtitle)}</p>'
        if subtitle
        else ""
    )
    st.markdown(
        '<div class="governia-section">'
        f"{eyebrow}<h2 class=\"governia-section-title\">{escape(title)}</h2>"
        f"{description}</div>",
        unsafe_allow_html=True,
    )


def hero() -> None:
    """Affiche la bannière d'accueil et son motif circulaire décoratif."""
    st.markdown(
        """
        <section class="governia-hero">
          <div class="governia-hero-copy">
            <span class="governia-hero-tag">PLATEFORME DATA &amp; AI</span>
            <h1>Govern IA</h1>
            <h3>Gouvernance intelligente et automatisée des données</h3>
            <p>Qualité, classification, sécurité et lignage réunis dans un espace
            unique pour mieux comprendre et gouverner vos données.</p>
          </div>
          <div class="governia-orbit" aria-hidden="true">
            <span class="governia-orbit-center">DATA</span>
            <span class="governia-orbit-node q">Q</span>
            <span class="governia-orbit-node c">C</span>
            <span class="governia-orbit-node s">S</span>
          </div>
        </section>
        """,
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
