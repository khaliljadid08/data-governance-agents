"""Validation humaine des analyses et consultation de l'audit."""

from __future__ import annotations

import logging
from pathlib import Path

import streamlit as st

from agents.supervisor import Supervisor
from app import data_access
from app.components import afficher_tableau, badge, section_title
from app.csv_import import cleanup_database
from ui.components import render_card, render_page_header


logger = logging.getLogger(__name__)


def _creer_superviseur(db_path: Path) -> Supervisor:
    """Construit un superviseur pour la source de données de la demande."""
    return Supervisor(
        data_access.GOVERNANCE_DB,
        db_path,
        gemini_assistant=st.session_state.get("gemini_assistant"),
    )


def _source_demande(request_id: int) -> Path:
    """Retourne la source enregistrée en session pour une demande."""
    paths = st.session_state.get("db_path_par_demande", {})
    return Path(paths.get(str(request_id), data_access.DEMO_DB))


def _liberer_base_si_inutilisee(db_path: Path) -> None:
    """Supprime une base temporaire lorsqu'aucun run non résolu ne l'utilise."""
    temporary_paths = set(st.session_state.get("bases_temporaires", []))
    path_text = str(db_path)
    if path_text not in temporary_paths:
        return
    data_access.invalider_cache()
    pairs = data_access.lister_demandes_et_runs(str(data_access.GOVERNANCE_DB))
    source_by_request = st.session_state.get("db_path_par_demande", {})
    latest_by_request: dict[int, dict] = {}
    for pair in pairs:
        request_id = int(pair["run"]["request_id"])
        previous = latest_by_request.get(request_id)
        if (
            previous is None
            or pair["run"]["numero_iteration"]
            > previous["run"]["numero_iteration"]
        ):
            latest_by_request[request_id] = pair
    unresolved = any(
        source_by_request.get(str(request_id)) == path_text
        and pair["run"]["statut"] in ("a_valider", "rejete", "en_cours")
        for request_id, pair in latest_by_request.items()
    )
    if unresolved:
        return
    cleanup_database(db_path)
    temporary_paths.discard(path_text)
    st.session_state["bases_temporaires"] = sorted(temporary_paths)
    if st.session_state.get("active_db_path") == path_text:
        st.session_state["active_db_path"] = None
        st.session_state["active_db_label"] = None


def _afficher_synthese(run_id: int) -> dict | None:
    """Affiche les éléments locaux et l'avis consultatif du superviseur."""
    cache_key = f"validation_synthese_{run_id}"
    cached_report = st.session_state.get(cache_key)
    if isinstance(cached_report, dict):
        report = cached_report
    else:
        supervisor = st.session_state.get("supervisor")
        if supervisor is None:
            st.error("Le superviseur n'est pas initialisé.")
            return None
        try:
            report = supervisor.consolider(run_id)
        except Exception as erreur:
            logger.exception("Impossible de consolider le run %s.", run_id)
            st.error(f"La synthèse est indisponible : {erreur}")
            return None
        st.session_state[cache_key] = report

    section_title("Synthèse consolidée", "REVUE HUMAINE")
    columns = st.columns(3)
    columns[0].metric(
        "Agents exécutés",
        sum(report["compteurs_par_agent"].values()),
    )
    columns[1].metric(
        "Anomalies critiques",
        len(report["anomalies_critiques"]),
    )
    columns[2].metric(
        "Non-conformités sensibles",
        len(report["colonnes_sensibles_non_conformes"]),
    )
    with st.expander("Détails des constats", expanded=False):
        st.write("**Anomalies critiques**")
        afficher_tableau(
            report["anomalies_critiques"],
            "Aucune anomalie critique.",
        )
        st.write("**Colonnes sensibles non conformes**")
        afficher_tableau(
            report["colonnes_sensibles_non_conformes"],
            "Aucune non-conformité de sécurité.",
        )
    synthesis = report.get("synthese_gemini", {})
    with st.expander("Avis consultatif Gemini", expanded=False):
        if synthesis.get("statut") == "succes":
            st.info(synthesis.get("avis", "Aucun avis retourné."))
            st.caption("Cet avis n'est pas une décision ; le reviewer reste décisionnaire.")
        elif synthesis.get("statut") == "echec":
            st.warning(
                f"Synthèse Gemini indisponible : "
                f"{synthesis.get('erreur', 'erreur inconnue')}"
            )
        else:
            st.caption("Gemini est désactivé ; la synthèse locale reste disponible.")
    return report


def _afficher_file_validation(supervisor: Supervisor) -> None:
    """Traite les runs en attente et les demandes rejetées."""
    try:
        pending = data_access.lister_runs_a_valider(
            str(data_access.GOVERNANCE_DB)
        )
        pairs = data_access.lister_demandes_et_runs(
            str(data_access.GOVERNANCE_DB)
        )
    except Exception as erreur:
        logger.exception("Impossible de charger la file de validation.")
        st.error(f"Impossible de charger les validations : {erreur}")
        return

    if pending:
        labels = {
            int(item["run_id"]): (
                f"Run {item['run_id']} · demande {item['request_id']} · "
                f"itération {item['numero_iteration']} — {item['operateur']}"
            )
            for item in pending
        }
        selected_id = st.selectbox(
            "Run à examiner",
            list(labels),
            format_func=labels.get,
        )
        selected = next(item for item in pending if item["run_id"] == selected_id)
        st.caption(
            f"Consigne : {selected['consigne']} · "
            f"Périmètre : {selected['perimetre']}"
        )
        _afficher_synthese(int(selected_id))

        with st.form(f"form_validation_{selected_id}"):
            reviewer = st.text_input("Nom du reviewer")
            reviewer_role = st.selectbox(
                "Rôle",
                ["Data Steward", "Data Owner"],
            )
            comment = st.text_area("Commentaire")
            accept_column, reject_column = st.columns(2)
            with accept_column:
                with st.container(key="validation_accept"):
                    validate = st.form_submit_button(
                        "Valider l'analyse", type="primary", width="stretch"
                    )
            with reject_column:
                with st.container(key="validation_reject"):
                    reject = st.form_submit_button(
                        "Refuser les résultats", width="stretch"
                    )

        if validate or reject:
            decision = "valide" if validate else "rejete"
            if not reviewer.strip():
                st.error("Veuillez saisir le nom du reviewer.")
            elif decision == "rejete" and not comment.strip():
                st.error("Un commentaire est obligatoire pour rejeter le run.")
            else:
                try:
                    supervisor.traiter_decision(
                        int(selected_id),
                        reviewer.strip(),
                        "data_owner" if reviewer_role == "Data Owner" else "data_steward",
                        decision,
                        comment.strip() or None,
                    )
                    data_access.invalider_cache()
                    request_id = int(selected["request_id"])
                    if decision == "valide":
                        try:
                            _liberer_base_si_inutilisee(
                                _source_demande(request_id)
                            )
                        except Exception:
                            logger.exception(
                                "La base temporaire de la demande %s "
                                "n'a pas pu être libérée.",
                                request_id,
                            )
                            st.warning(
                                "La décision est enregistrée, mais la base "
                                "temporaire n'a pas pu être supprimée."
                            )
                    st.session_state["flash_validation"] = (
                        "Run validé." if decision == "valide" else "Run rejeté."
                    )
                    st.rerun()
                except Exception as erreur:
                    logger.exception(
                        "Impossible d'enregistrer la décision du run %s.",
                        selected_id,
                    )
                    st.error(f"La décision n'a pas été enregistrée : {erreur}")
    else:
        st.info("Aucun run n'est actuellement en attente de validation.")

    rejected = [
        pair
        for pair in pairs
        if pair["run"]["statut"] == "rejete" and pair.get("request") is not None
    ]
    if rejected:
        st.divider()
        section_title("Re-coordination", "APRÈS UN REJET")
        latest_rejected: dict[int, dict] = {}
        for pair in rejected:
            request_id = int(pair["run"]["request_id"])
            previous = latest_rejected.get(request_id)
            if (
                previous is None
                or pair["run"]["numero_iteration"]
                > previous["run"]["numero_iteration"]
            ):
                latest_rejected[request_id] = pair
        request_ids = sorted(latest_rejected, reverse=True)

        def format_request(request_id: int) -> str:
            pair = latest_rejected[request_id]
            return (
                f"Demande {request_id} · dernier run rejeté "
                f"{pair['run']['id']} — {pair['request']['operateur']}"
            )

        request_id = st.selectbox(
            "Demande à relancer",
            request_ids,
            format_func=format_request,
            key="recoordination_request",
        )
        if st.button("Relancer la coordination →", type="primary"):
            source = _source_demande(int(request_id))
            if not source.exists():
                st.error(
                    "La base temporaire associée à cette demande n'est plus disponible. "
                    "Relancez une analyse depuis les fichiers CSV."
                )
                return
            try:
                coordinator = _creer_superviseur(source)
                with st.spinner("Nouvelle coordination en cours…"):
                    report = coordinator.re_coordonner(int(request_id))
                    coordinator.soumettre_a_validation(report["run_id"])
                data_access.invalider_cache()
                st.session_state["supervisor"] = coordinator
                st.session_state["run_id_courant"] = report["run_id"]
                st.session_state["rapport_courant"] = report
                st.success(
                    f"Nouveau run {report['run_id']} créé "
                    f"(itération {report['numero_iteration']})."
                )
                st.rerun()
            except Exception as erreur:
                logger.exception(
                    "La re-coordination de la demande %s a échoué.", request_id
                )
                st.error(f"La re-coordination a échoué : {erreur}")


def _afficher_historique() -> None:
    """Affiche les décisions humaines et les entrées du journal d'audit."""
    st.divider()
    section_title(
        "Historique et audit",
        "TRAÇABILITÉ",
        "Décisions des reviewers et événements enregistrés par le système.",
    )
    try:
        validations = data_access.lire_validations(
            str(data_access.GOVERNANCE_DB)
        )
        audit = data_access.lire_journal_audit(
            str(data_access.GOVERNANCE_DB)
        )
    except Exception as erreur:
        logger.exception("Impossible de charger l'historique et l'audit.")
        st.error(f"Impossible de charger l'historique : {erreur}")
        return

    validation_tab, audit_tab = st.tabs(
        [f"Validations ({len(validations)})", f"Journal d'audit ({len(audit)})"]
    )
    with validation_tab:
        afficher_tableau(
            validations,
            "Aucune validation n'a encore été enregistrée.",
        )
    with audit_tab:
        afficher_tableau(audit, "Aucun événement d'audit n'est enregistré.")


def render() -> None:
    """Affiche la validation puis l'historique de gouvernance."""
    render_page_header(
        "DÉCISION HUMAINE",
        "Validation",
        "Un Data Steward ou Data Owner examine chaque analyse avant validation.",
    )
    message = st.session_state.pop("flash_validation", None)
    if message:
        st.success(message)
    supervisor = st.session_state.get("supervisor")
    if supervisor is None:
        st.error("Le superviseur n'est pas initialisé.")
        return
    with render_card("validation-review"):
        _afficher_file_validation(supervisor)
    with render_card("validation-history"):
        _afficher_historique()
