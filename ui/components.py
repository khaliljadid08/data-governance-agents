"""Composants HTML réutilisables pour les pages Govern IA."""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from contextlib import contextmanager
from html import escape
from typing import Any, Iterator

import streamlit as st


_BADGE_COLORS = {
    "success": "green",
    "succes": "green",
    "validated": "green",
    "valide": "green",
    "pending": "gray",
    "a_valider": "gray",
    "medium": "orange",
    "moyenne": "orange",
    "high": "red",
    "haute": "red",
    "elevee": "red",
    "critical": "red",
    "critique": "red",
    "failed": "red",
    "echec": "red",
    "conforme": "green",
    "non conforme": "red",
}


def render_badge(value: str, label: str | None = None) -> str:
    """Construit un badge avec texte échappé et couleur déterministe."""
    color = _BADGE_COLORS.get(value.casefold(), "slate")
    text = label if label is not None else value.replace("_", " ")
    return (
        f'<span class="ui-badge ui-badge--{color}">'
        f"{escape(text.upper() if value.casefold() in ('success', 'medium', 'high') else text)}"
        "</span>"
    )


@contextmanager
def render_card(key: str) -> Iterator[None]:
    """Affiche le contenu suivant dans une carte blanche Streamlit."""
    with st.container(key=f"ui-card-{key}"):
        yield


def render_page_header(
    kicker: str,
    title: str,
    detail: str = "",
    badge: str | None = None,
) -> None:
    """Affiche un en-tête de page avec surtitre, titre et badge facultatif."""
    left, right = st.columns([5, 1.5], vertical_alignment="center")
    with left:
        st.markdown(
            '<div class="ui-eyebrow">'
            f"{escape(kicker.upper())}</div>"
            f'<h1 class="ui-page-title">{escape(title)}</h1>'
            + (f'<p class="ui-page-detail">{escape(detail)}</p>' if detail else ""),
            unsafe_allow_html=True,
        )
    if badge:
        with right:
            st.markdown(
                f'<div class="ui-header-badge">{escape(badge)}</div>',
                unsafe_allow_html=True,
            )


def render_table(
    headers: Sequence[str],
    rows: Sequence[Sequence[Any]],
    badge_columns: Mapping[int, str] | None = None,
    empty_message: str = "Aucun résultat à afficher.",
) -> None:
    """Affiche un tableau HTML accessible et échappé."""
    if not rows:
        st.info(empty_message)
        return
    badge_columns = badge_columns or {}
    header_html = "".join(f"<th>{escape(header)}</th>" for header in headers)
    body = []
    for row in rows:
        cells = []
        for index, value in enumerate(row):
            rendered = (
                render_badge(str(value))
                if index in badge_columns and value not in (None, "")
                else escape("—" if value is None or value == "" else str(value))
            )
            cells.append(f"<td>{rendered}</td>")
        body.append(f"<tr>{''.join(cells)}</tr>")
    st.markdown(
        '<div class="ui-table-wrap"><table class="ui-table">'
        f"<thead><tr>{header_html}</tr></thead>"
        f"<tbody>{''.join(body)}</tbody></table></div>",
        unsafe_allow_html=True,
    )


def render_agent_card(
    letter: str,
    name: str,
    status: str,
    summary: str,
    href: str,
    link_label: str,
    color: str,
) -> None:
    """Affiche une carte d'agent avec son statut et un lien de navigation."""
    status_color = "green" if status.casefold() in ("success", "succes") else "red"
    st.markdown(
        '<article class="ui-agent-card">'
        '<div class="ui-agent-card__top">'
        f'<span class="ui-agent-icon ui-agent-icon--{escape(color)}">'
        f"{escape(letter)}</span>"
        f'<span class="ui-badge ui-badge--{status_color}">'
        f"{escape(status.upper())}</span></div>"
        f'<h3 class="ui-agent-card__title">{escape(name)}</h3>'
        f'<p class="ui-agent-card__summary">{escape(summary)}</p>'
        f'<a class="ui-agent-card__link" href="{escape(href, quote=True)}">'
        f"{escape(link_label)} →</a></article>",
        unsafe_allow_html=True,
    )


def render_distribution_card(
    title: str,
    values: Sequence[tuple[str, int, str]],
) -> None:
    """Affiche une carte de répartition avec des barres horizontales."""
    maximum = max((value for _, value, _ in values), default=0)
    rows = []
    for label, value, tone in values:
        width = round(value / maximum * 100) if maximum else 0
        safe_tone = tone if tone in ("blue", "orange", "red") else "blue"
        label_html = (
            render_badge(label)
            if safe_tone in ("orange", "red")
            else f"<span>{escape(label)}</span>"
        )
        rows.append(
            '<div class="ui-bar-row">'
            f'<div class="ui-bar-label">{label_html}</div>'
            '<div class="ui-bar-track">'
            f'<span class="ui-bar-fill ui-bar-fill--{safe_tone}" '
            f'style="width:{width}%"></span></div>'
            f'<strong class="ui-bar-value">{value}</strong></div>'
        )
    content = "".join(rows)
    if not content:
        content = '<p class="ui-page-detail">Aucun résultat.</p>'
    st.markdown(
        '<section class="ui-distribution-card">'
        f'<div class="ui-distribution-title">{escape(title)}</div>'
        f"{content}"
        "</section>",
        unsafe_allow_html=True,
    )


def render_timeline_item(title: str, description: str, timestamp: str = "") -> None:
    """Affiche un jalon de lignage sans inventer de métadonnées manquantes."""
    st.markdown(
        '<div class="ui-timeline-item"><span class="ui-timeline-dot"></span>'
        '<div class="ui-timeline-copy">'
        f'<strong>{escape(title.upper())}</strong>'
        f"<p>{escape(description)}</p></div>"
        f'<time>{escape(timestamp or "Date non enregistrée")}</time></div>',
        unsafe_allow_html=True,
    )
