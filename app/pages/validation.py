"""Page de validation des runs par un Data Steward ou Data Owner."""

from __future__ import annotations

import logging

import streamlit as st

if __package__ == "app.pages":
    from .. import data_access
    from ..components import afficher_tableau
else:
    import data_access
    from components import afficher_tableau


logger = logging.getLogger(__name__)


def render() -> None:
    """Affiche les runs à valider et les options de re-coordination."""
    st.title("Validation")
    flash_message = st.session_state.pop("flash_validation", None)
    if flash_message:
        st.success(flash_message)
    try:
        pending = data_access.lister_runs_a_valider(
            str(data_access.GOVERNANCE_DB)
        )
        pairs = data_access.lister_demandes_et_runs(
            str(data_access.GOVERNANCE_DB)
        )
    except Exception as erreur:
        logger.exception("Impossible de lire la file de validation.")
        st.error(f"Impossible de charger la file de validation : {erreur}")
        return

    supervisor = st.session_state["supervisor"]
    role_session = st.session_state.get("role", "Data Steward")
    reviewer_role = (
        "data_owner" if role_session == "Data Owner" else "data_steward"
    )
    if pending:
        labels = {
            run["run_id"]: (
                f"Run {run['run_id']} · demande {run['request_id']} · "
                f"itération {run['numero_iteration']} — {run['operateur']}"
            )
            for run in pending
        }
        selected_id = st.selectbox(
            "Run à examiner",
            [run["run_id"] for run in pending],
            format_func=labels.get,
        )
        selected = next(run for run in pending if run["run_id"] == selected_id)
        st.markdown(f"**Consigne :** {selected['consigne']}")
        st.markdown(f"**Périmètre :** {selected['perimetre']}")

        report_key = f"rapport_validation_{selected_id}"
        if report_key not in st.session_state:
            try:
                st.session_state[report_key] = supervisor.consolider(selected_id)
                data_access.invalider_cache()
            except Exception as erreur:
                logger.exception("Impossible de consolider le run %s.", selected_id)
                st.error(f"La synthèse du run est indisponible : {erreur}")
        report = st.session_state.get(report_key)

        if report is not None:
            st.subheader("Synthèse consolidée")
            st.write("**Résultats par agent**")
            afficher_tableau(
                [
                    {"Agent": agent, "Nombre de résultats": count}
                    for agent, count in report["compteurs_par_agent"].items()
                ],
                "Aucun résultat d'agent disponible.",
            )
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
                    st.caption(
                        "Cet avis n'est pas une décision de validation ; "
                        "le reviewer reste seul décisionnaire."
                    )
                elif synthesis.get("statut") == "echec":
                    st.warning(
                        "Synthèse Gemini indisponible : "
                        f"{synthesis.get('erreur', 'erreur inconnue')}"
                    )
                else:
                    st.caption(
                        "Gemini est désactivé ; la synthèse locale reste disponible."
                    )

        with st.form(f"form_validation_{selected_id}"):
            reviewer = st.text_input("Nom du reviewer")
            st.text_input(
                "Rôle du reviewer",
                value=role_session,
                disabled=True,
                help="Le rôle provient du sélecteur de simulation dans la barre latérale.",
            )
            commentaire = st.text_area("Commentaire")
            valider = st.form_submit_button("Valider", type="primary")
            rejeter = st.form_submit_button("Rejeter")

        if valider or rejeter:
            decision = "valide" if valider else "rejete"
            if not reviewer.strip():
                st.error("Veuillez saisir le nom du reviewer.")
            elif decision == "rejete" and not commentaire.strip():
                st.error("Un commentaire est obligatoire pour rejeter un run.")
            else:
                try:
                    supervisor.traiter_decision(
                        selected_id,
                        reviewer.strip(),
                        reviewer_role,
                        decision,
                        commentaire.strip() or None,
                    )
                    data_access.invalider_cache()
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
        if pair["run"]["statut"] == "rejete" and pair["request"] is not None
    ]
    if rejected:
        st.divider()
        st.subheader("Re-coordination après un rejet")
        rejected_by_request: dict[int, dict[str, object]] = {}
        for pair in rejected:
            request_id = int(pair["run"]["request_id"])
            previous = rejected_by_request.get(request_id)
            if (
                previous is None
                or pair["run"]["numero_iteration"]
                > previous["run"]["numero_iteration"]
            ):
                rejected_by_request[request_id] = pair
        request_ids = sorted(rejected_by_request, reverse=True)

        def format_request(request_id: int) -> str:
            pair = rejected_by_request[request_id]
            return (
                f"Demande {request_id} · dernier run rejeté "
                f"{pair['run']['id']} — {pair['request']['operateur']}"
            )

        request_id = st.selectbox(
            "Demande à relancer",
            request_ids,
            format_func=format_request,
        )
        if st.button("Relancer la coordination", type="primary"):
            try:
                with st.spinner("Nouvelle coordination en cours…"):
                    report = supervisor.re_coordonner(request_id)
                data_access.invalider_cache()
                st.session_state["request_id_courant"] = request_id
                st.session_state["run_id_courant"] = report["run_id"]
                st.session_state["rapport_courant"] = report
                st.session_state["flash_validation"] = (
                    f"Nouveau run {report['run_id']} créé "
                    f"(itération {report['numero_iteration']})."
                )
                st.rerun()
            except Exception as erreur:
                logger.exception(
                    "Impossible de relancer la demande %s.", request_id
                )
                st.error(f"La re-coordination a échoué : {erreur}")
