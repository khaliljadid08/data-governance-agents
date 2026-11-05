"""Page de création d'une analyse à partir de CSV ou du jeu de démonstration."""

from __future__ import annotations

import logging
from pathlib import Path

import streamlit as st

from agents.supervisor import ConsigneIncompleteError, Supervisor
from app import data_access
from app.components import hero, section_title
from app.csv_import import CsvImportError, create_database


logger = logging.getLogger(__name__)
_AGENTS = ["qualite", "classification", "securisation", "lignage"]


def _creer_superviseur(db_path: Path) -> Supervisor:
    """Construit le superviseur lié à la base métier de cette analyse."""
    return Supervisor(
        data_access.GOVERNANCE_DB,
        db_path,
        gemini_assistant=st.session_state.get("gemini_assistant"),
    )


def _run_analysis(
    operateur: str,
    consigne: str,
    db_path: Path,
    table_names: list[str],
) -> None:
    """Appelle le superviseur et conserve les références utiles à l'interface."""
    supervisor = _creer_superviseur(db_path)
    st.session_state["supervisor"] = supervisor
    try:
        request_id = supervisor.recevoir_consigne(
            operateur,
            consigne,
            table_names,
            _AGENTS,
        )
    except ConsigneIncompleteError as erreur:
        st.error(f"Précision demandée : {erreur}")
        return
    except Exception as erreur:
        logger.exception("Impossible de créer la demande d'analyse.")
        st.error(f"La demande n'a pas pu être créée : {erreur}")
        return

    st.session_state["request_id_courant"] = request_id
    source_by_request = st.session_state.setdefault("db_path_par_demande", {})
    source_by_request[str(request_id)] = str(db_path)
    temporary_paths = set(st.session_state.get("bases_temporaires", []))
    with st.status("Analyse des tables en cours", expanded=True) as status:
        try:
            report = supervisor.coordonner(request_id)
            supervisor.soumettre_a_validation(report["run_id"])
        except Exception as erreur:
            logger.exception(
                "La coordination de la demande %s a échoué.", request_id
            )
            status.update(label="L'analyse a échoué", state="error")
            st.error(f"L'analyse n'a pas pu aboutir : {erreur}")
            data_access.invalider_cache()
            return

        results = report.get("agents_execution", [])
        for result in results:
            st.write(f"**{result['agent']}** — {result['resume']}")
        status.update(
            label="Analyse terminée",
            state="complete"
            if all(result["statut"] == "succes" for result in results)
            else "error",
        )

    st.session_state["run_id_courant"] = report["run_id"]
    st.session_state["rapport_courant"] = report
    st.session_state["source_analyse"] = (
        "Données CSV temporaires" if str(db_path) in temporary_paths else "Démo"
    )
    data_access.invalider_cache()
    st.success(
        f"Analyse terminée · run {report['run_id']} "
        f"(itération {report['numero_iteration']})."
    )
    st.info("Consultez le Dashboard, les Anomalies ou la page Gouvernance.")


def render() -> None:
    """Affiche le formulaire d'import et lance l'analyse sélectionnée."""
    hero()
    section_title(
        "Lancer une analyse",
        "COMMENCER",
        "Importez une ou plusieurs tables CSV ou utilisez le jeu de démonstration.",
    )

    uploaded_files = st.file_uploader(
        "Déposez vos fichiers CSV ici",
        type=["csv"],
        accept_multiple_files=True,
        max_upload_size=16,
        help="Chaque fichier devient une table analysée.",
    )
    st.caption("CSV uniquement · jusqu'à 16 Mo par fichier")
    st.markdown(
        '<div class="governia-alert">Ne téléversez pas de données confidentielles '
        "réelles.</div>",
        unsafe_allow_html=True,
    )

    demo_col, source_col = st.columns([1, 2])
    with demo_col:
        if st.button("Utiliser les données de démonstration", width="stretch"):
            st.session_state["active_db_path"] = str(data_access.DEMO_DB)
            st.session_state["active_db_label"] = "Données de démonstration"
            st.success("Le jeu de démonstration est prêt à être analysé.")
    with source_col:
        active_label = st.session_state.get("active_db_label")
        if active_label:
            st.caption(f"Source sélectionnée : {active_label}")
        else:
            st.caption("Choisissez une source avant de lancer une analyse.")

    with st.form("governia_new_analysis"):
        operator = st.text_input("Nom de l'opérateur", placeholder="Ex. : Camille Martin")
        instructions = st.text_area(
            "Consigne",
            placeholder="Décrivez les contrôles ou éléments à analyser.",
            height=110,
        )
        submit = st.form_submit_button(
            "Lancer l'analyse →",
            type="primary",
            width="stretch",
        )

    if not submit:
        return
    if not operator.strip():
        st.error("Veuillez préciser le nom de l'opérateur.")
        return
    if not instructions.strip():
        st.error("Veuillez préciser les objectifs de l'analyse.")
        return

    try:
        if uploaded_files:
            imported = create_database(uploaded_files)
            db_path = imported.db_path
            table_names = list(imported.table_names)
            paths = set(st.session_state.get("bases_temporaires", []))
            paths.add(str(db_path))
            st.session_state["bases_temporaires"] = sorted(paths)
            st.session_state["active_db_path"] = str(db_path)
            st.session_state["active_db_label"] = (
                f"CSV · {', '.join(table_names)}"
            )
        else:
            selected_path = st.session_state.get("active_db_path")
            if not selected_path:
                st.error(
                    "Sélectionnez un CSV ou choisissez les données de démonstration."
                )
                return
            db_path = Path(selected_path)
            table_names = data_access.lister_tables_demo(str(db_path))
        if not table_names:
            st.error("La source ne contient aucune table à analyser.")
            return
    except CsvImportError as erreur:
        st.error(str(erreur))
        return
    except Exception as erreur:
        logger.exception("Impossible de préparer la source de données.")
        st.error(f"Impossible de préparer les données : {erreur}")
        return

    _run_analysis(operator.strip(), instructions.strip(), db_path, table_names)
