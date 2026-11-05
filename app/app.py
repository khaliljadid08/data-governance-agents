"""Point d'entrée de l'interface Streamlit de gouvernance."""

from __future__ import annotations

import hashlib
import logging
import os

import streamlit as st
from streamlit.errors import StreamlitSecretNotFoundError

from agents.gemini_metadata import GeminiMetadataAssistant
from agents.supervisor import Supervisor
from storage import db
from storage.seed_demo_data import create_demo_data

if __package__:
    from . import data_access
    from .pages import (
        dictionnaire,
        historique,
        nouvelle_demande,
        resultats,
        validation,
    )
else:
    import data_access
    from pages import dictionnaire, historique, nouvelle_demande, resultats, validation


logger = logging.getLogger(__name__)

st.set_page_config(
    page_title="Gouvernance des données",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="expanded",
)

st.title("Gouvernance des données")


def _lire_configuration(nom: str, defaut: str = "") -> str:
    """Lit une valeur depuis les secrets Streamlit ou les variables d'environnement."""
    try:
        valeur_secret = st.secrets.get(nom)
    except StreamlitSecretNotFoundError:
        valeur_secret = None
    if valeur_secret is not None:
        return str(valeur_secret).strip()
    return os.environ.get(nom, defaut).strip()


try:
    db.init_db(data_access.GOVERNANCE_DB)
    if not data_access.DEMO_DB.exists():
        create_demo_data(data_access.DEMO_DB)
except Exception as erreur:
    logger.exception("Impossible d'initialiser les bases de l'application.")
    st.error(f"Initialisation impossible : {erreur}")
    st.stop()

if "role" not in st.session_state:
    st.session_state["role"] = "Opérateur"

with st.sidebar:
    st.header("Espace de travail")
    role = st.selectbox(
        "Rôle simulé",
        ["Opérateur", "Data Steward", "Data Owner"],
        key="role",
        help="Cette simulation de rôle ne remplace pas une authentification.",
    )
    st.caption("Aucune authentification réelle n'est configurée.")

gemini_api_key = _lire_configuration("GEMINI_API_KEY")
gemini_model = _lire_configuration("GEMINI_MODEL", "gemini-3.8-flash")
gemini_enabled = _lire_configuration("GEMINI_ENABLED").casefold() == "true"
gemini_ready = gemini_enabled and bool(gemini_api_key)
with st.sidebar:
    st.divider()
    st.subheader("Assistance Gemini")
    if gemini_ready:
        st.success(f"Activées · modèle {gemini_model}")
        st.caption(
            "Les agents et la synthèse peuvent demander des avis consultatifs. Seuls "
            "les noms de tables/colonnes, types, catégories, sensibilités et compteurs "
            "agrégés sont transmis. Aucune valeur de ligne ni consigne opérateur "
            "n'est envoyée. Les décisions locales restent déterminantes."
        )
    elif gemini_enabled:
        st.warning("Ajoutez GEMINI_API_KEY aux secrets pour activer Gemini.")
    else:
        st.info("Désactivée : analyses déterministes locales uniquement.")

supervisor_key = (
    str(data_access.GOVERNANCE_DB),
    str(data_access.DEMO_DB),
    hashlib.sha256(gemini_api_key.encode("utf-8")).hexdigest(),
    gemini_model,
    gemini_ready,
)
if st.session_state.get("supervisor_key") != supervisor_key:
    gemini_assistant = (
        GeminiMetadataAssistant(gemini_api_key, gemini_model)
        if gemini_ready
        else None
    )
    st.session_state["supervisor"] = Supervisor(
        data_access.GOVERNANCE_DB,
        data_access.DEMO_DB,
        gemini_assistant=gemini_assistant,
    )
    st.session_state["supervisor_key"] = supervisor_key

available_pages = [
    st.Page(
        nouvelle_demande.render,
        title="Nouvelle demande",
        icon="📝",
        url_path="nouvelle-demande",
        default=role == "Opérateur",
    ),
    st.Page(
        resultats.render,
        title="Résultats",
        icon="📈",
        url_path="resultats",
        default=role != "Opérateur",
    ),
    st.Page(
        dictionnaire.render,
        title="Dictionnaire de données",
        icon="📚",
        url_path="dictionnaire",
    ),
]
if role in ("Data Steward", "Data Owner"):
    available_pages.extend(
        [
            st.Page(
                validation.render,
                title="Validation",
                icon="✅",
                url_path="validation",
            ),
            st.Page(
                historique.render,
                title="Historique et audit",
                icon="🧾",
                url_path="historique",
            ),
        ]
    )

navigation = st.navigation(available_pages, position="sidebar")
navigation.run()
