"""Point d'entrée de l'interface Streamlit Govern IA."""

from __future__ import annotations

import hashlib
import logging
import os
from pathlib import Path
import sys

import streamlit as st
from streamlit.errors import StreamlitSecretNotFoundError

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from agents.gemini_metadata import GeminiMetadataAssistant
from agents.supervisor import Supervisor
from app import data_access
from app.pages import anomalies, dashboard, gouvernance, nouvelle_analyse, validation
from app.styles import inject_css as inject_visual_styles
from storage import db
from storage.seed_demo_data import create_demo_data


logger = logging.getLogger(__name__)

st.set_page_config(
    page_title="Govern IA",
    page_icon="G",
    layout="wide",
    initial_sidebar_state="expanded",
)
inject_visual_styles()


def _lire_configuration(nom: str, defaut: str = "") -> str:
    """Lit une valeur des secrets Streamlit ou de l'environnement."""
    try:
        value = st.secrets.get(nom)
    except StreamlitSecretNotFoundError:
        value = None
    if value is not None:
        return str(value).strip()
    return os.environ.get(nom, defaut).strip()


try:
    db.init_db(data_access.GOVERNANCE_DB)
    if not data_access.DEMO_DB.exists():
        create_demo_data(data_access.DEMO_DB)
except Exception as erreur:
    logger.exception("Impossible d'initialiser les bases de gouvernance.")
    st.error(f"Initialisation impossible : {erreur}")
    st.stop()

gemini_api_key = _lire_configuration("GEMINI_API_KEY")
gemini_model = _lire_configuration("GEMINI_MODEL", "gemini-3.8-flash")
gemini_enabled = _lire_configuration("GEMINI_ENABLED", "false").casefold() == "true"
gemini_key = (
    hashlib.sha256(gemini_api_key.encode("utf-8")).hexdigest(),
    gemini_model,
    gemini_enabled,
)
if st.session_state.get("_gemini_key") != gemini_key:
    assistant = (
        GeminiMetadataAssistant(gemini_api_key, gemini_model)
        if gemini_enabled and gemini_api_key
        else None
    )
    st.session_state["gemini_assistant"] = assistant
    st.session_state["_gemini_key"] = gemini_key

if "active_db_path" not in st.session_state:
    st.session_state["active_db_path"] = None
    st.session_state["active_db_label"] = None
if "page_courante" not in st.session_state:
    st.session_state["page_courante"] = "Nouvelle analyse"

page_labels = {
    "Nouvelle analyse": "📝  Nouvelle analyse",
    "Dashboard": "▦  Dashboard",
    "Anomalies": "⚠️  Anomalies",
    "Gouvernance": "◇  Gouvernance",
    "Validation": "✓  Validation",
}
pages_by_title = {
    "Nouvelle analyse": st.Page(
        nouvelle_analyse.render,
        title="Nouvelle analyse",
        url_path="nouvelle-analyse",
        icon="📝",
        default=True,
    ),
    "Dashboard": st.Page(
        dashboard.render,
        title="Dashboard",
        url_path="dashboard",
        icon="📊",
    ),
    "Anomalies": st.Page(
        anomalies.render,
        title="Anomalies",
        url_path="anomalies",
        icon="⚠️",
    ),
    "Gouvernance": st.Page(
        gouvernance.render,
        title="Gouvernance",
        url_path="gouvernance",
        icon="🔐",
    ),
    "Validation": st.Page(
        validation.render,
        title="Validation",
        url_path="validation",
        icon="✅",
    ),
}
navigation_page = st.navigation(
    list(pages_by_title.values()),
    position="hidden",
)
st.session_state["_governia_pages"] = pages_by_title
st.session_state["page_courante"] = navigation_page.title
if "navigation_governia" not in st.session_state:
    st.session_state["navigation_governia"] = page_labels[navigation_page.title]


def _naviguer_vers_page() -> None:
    """Suit le choix du menu latéral avec la navigation Streamlit masquée."""
    selected_label = st.session_state["navigation_governia"]
    selected_title = next(
        title for title, label in page_labels.items() if label == selected_label
    )
    st.session_state["page_courante"] = selected_title
    st.switch_page(pages_by_title[selected_title])


source_path = Path(
    st.session_state.get("active_db_path") or data_access.DEMO_DB
)
supervisor_key = (
    str(data_access.GOVERNANCE_DB),
    str(source_path),
    gemini_key,
)
if st.session_state.get("_supervisor_key") != supervisor_key:
    st.session_state["supervisor"] = Supervisor(
        data_access.GOVERNANCE_DB,
        source_path,
        gemini_assistant=st.session_state.get("gemini_assistant"),
    )
    st.session_state["_supervisor_key"] = supervisor_key

with st.sidebar:
    st.markdown(
        '<div class="governia-brand"><div class="governia-logo">GI</div>'
        '<div class="governia-name">Govern <span>IA</span></div></div>',
        unsafe_allow_html=True,
    )
    st.markdown(
        '<div class="governia-nav-label">ESPACE DE TRAVAIL</div>',
        unsafe_allow_html=True,
    )
    selected_page = st.radio(
        "Navigation principale",
        list(page_labels.values()),
        index=list(page_labels.values()).index(
            page_labels[navigation_page.title]
        ),
        label_visibility="collapsed",
        key="navigation_governia",
        on_change=_naviguer_vers_page,
    )
    st.markdown(
        '<div class="governia-sidebar-footer"><span class="governia-dot"></span>'
        "Pipeline Python · SQLite</div>",
        unsafe_allow_html=True,
    )

if gemini_enabled and not gemini_api_key:
    st.sidebar.warning("Gemini est activé mais GEMINI_API_KEY n'est pas configurée.")
elif st.session_state.get("gemini_assistant") is None:
    st.sidebar.caption("Gemini désactivé · analyses déterministes locales")

navigation_page.run()
