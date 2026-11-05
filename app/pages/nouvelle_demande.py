"""Page opérateur pour soumettre et lancer une nouvelle analyse."""

from __future__ import annotations

import logging

import streamlit as st

from agents.supervisor import ConsigneIncompleteError

if __package__ == "app.pages":
    from .. import data_access
    from ..components import afficher_badge
else:
    import data_access
    from components import afficher_badge


logger = logging.getLogger(__name__)

_AGENTS = {
    "qualite": "Qualité des données",
    "classification": "Classification",
    "securisation": "Sécurisation",
    "lignage": "Lignage",
}


def render() -> None:
    """Affiche le formulaire, exécute la coordination et son suivi."""
    st.title("Nouvelle demande")
    st.caption("Soumettez une consigne d'analyse au système de gouvernance.")

    try:
        tables = data_access.lister_tables_demo(str(data_access.DEMO_DB))
    except Exception as erreur:
        logger.exception("Impossible de lire les tables métier.")
        st.error(f"Impossible de charger le périmètre métier : {erreur}")
        return
    if not tables:
        st.info("Aucune table métier n'est disponible dans demo_data.db.")
        return

    with st.form("formulaire_nouvelle_demande"):
        operateur = st.text_input(
            "Nom de l'opérateur",
            value=st.session_state.get("nom_operateur", ""),
            placeholder="Ex. : Camille Martin",
        )
        consigne = st.text_area(
            "Consigne",
            value=st.session_state.get("consigne_en_cours", ""),
            placeholder="Décrivez les contrôles ou éléments à analyser.",
            height=130,
        )
        perimetre = st.multiselect(
            "Tables à analyser",
            options=tables,
            default=[
                table
                for table in st.session_state.get(
                    "perimetre_en_cours", ["clients", "commandes", "produits"]
                )
                if table in tables
            ],
        )
        st.markdown("**Agents à activer**")
        choix_agents = {
            agent_id: st.checkbox(
                nom,
                value=st.session_state.get("agents_en_cours", {}).get(agent_id, True),
                key=f"agent_{agent_id}",
            )
            for agent_id, nom in _AGENTS.items()
        }
        st.caption(
            "L'agent de documentation s'exécute ensuite automatiquement pour compléter "
            "le dictionnaire."
        )
        submitted = st.form_submit_button(
            "Lancer l'analyse", type="primary", width="stretch"
        )

    if not submitted:
        return

    st.session_state["nom_operateur"] = operateur
    st.session_state["consigne_en_cours"] = consigne
    st.session_state["perimetre_en_cours"] = perimetre
    st.session_state["agents_en_cours"] = choix_agents
    agents_actifs = [
        agent_id for agent_id, actif in choix_agents.items() if actif
    ]
    if not agents_actifs:
        st.error("Activez au moins un agent pour lancer l'analyse.")
        return

    supervisor = st.session_state["supervisor"]
    try:
        request_id = supervisor.recevoir_consigne(
            operateur, consigne, perimetre, agents_actifs
        )
    except ConsigneIncompleteError as erreur:
        st.error(f"Précision demandée : {erreur}")
        st.info("Corrigez les champs du formulaire puis soumettez à nouveau.")
        return
    except Exception as erreur:
        logger.exception("Impossible de créer la demande.")
        st.error(f"La demande n'a pas pu être créée : {erreur}")
        return

    st.session_state["request_id_courant"] = request_id
    barre = st.progress(0, text="Coordination des agents en cours…")
    with st.status("Analyse en cours", expanded=True) as status:
        try:
            report = supervisor.coordonner(request_id)
        except Exception as erreur:
            logger.exception("Échec de la coordination de la demande %s.", request_id)
            status.update(label="La coordination a échoué", state="error")
            barre.empty()
            st.error(f"L'analyse n'a pas pu aboutir : {erreur}")
            data_access.invalider_cache()
            return

        results = report.get("agents_execution", [])
        total = max(len(results), 1)
        for index, result in enumerate(results, start=1):
            st.write(f"**{result['agent']}** — {result['resume']}")
            afficher_badge(result["statut"])
            barre.progress(index / total, text=f"Résultats reçus : {index}/{total}")
        status.update(
            label="Analyse terminée",
            state="complete"
            if all(result["statut"] == "succes" for result in results)
            else "error",
        )

    data_access.invalider_cache()
    st.session_state["run_id_courant"] = report["run_id"]
    st.session_state["rapport_courant"] = report
    st.success(
        f"Demande {request_id} traitée. Run {report['run_id']} — "
        f"itération {report['numero_iteration']}."
    )
    st.info("Consultez la page Résultats ou soumettez le run à validation.")
