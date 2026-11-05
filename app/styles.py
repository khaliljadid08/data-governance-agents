"""Styles centralisés de l'interface Govern IA."""

from __future__ import annotations

import streamlit as st


def inject_css() -> None:
    """Applique le thème clair, la navigation et les composants Govern IA."""
    st.markdown(
        """
        <style>
        @import url('https://fonts.googleapis.com/css2?family=Manrope:wght@400;500;600;700;800&display=swap');

        :root {
            --navy: #0F2547;
            --blue: #2563EB;
            --blue-light: #93C5FD;
            --page: #F1F5F9;
            --text: #0F172A;
            --muted: #64748B;
            --line: #E2E8F0;
        }
        html, body, [class*="css"], [data-testid="stAppViewContainer"] {
            font-family: 'Manrope', sans-serif;
        }
        [data-testid="stAppViewContainer"] {
            background: var(--page) !important;
            color: var(--text);
            color-scheme: light;
        }
        [data-testid="stHeader"], [data-testid="stToolbar"],
        #stSidebarNav, [data-testid="stSidebarNav"], #MainMenu, footer {
            display: none !important;
            height: 0;
        }
        [data-testid="stMain"] { color: var(--text) !important; }
        .block-container {
            max-width: 1440px;
            padding: 1.25rem 2rem 2.5rem;
        }
        #stMain h1, #stMain h2, #stMain h3, #stMain p, #stMain label {
            color: var(--text);
        }
        #stMain input, #stMain textarea {
            color: var(--text) !important;
            background: #FFFFFF !important;
        }
        #stMain input::placeholder, #stMain textarea::placeholder {
            color: var(--muted) !important;
            opacity: 1;
        }
        [data-testid="stMain"] [data-testid="stWidgetLabel"] p {
            color: #334155 !important;
            font-weight: 700;
        }
        [data-testid="stMain"] [data-testid="stMarkdownContainer"] p {
            color: #334155;
        }
        [data-testid="stSidebar"], [data-testid="stSidebar"] > div:first-child {
            background: var(--navy);
            border-right: 1px solid rgba(255,255,255,.06);
        }
        [data-testid="stSidebar"] [data-testid="stMarkdownContainer"] {
            color: #E2E8F0;
        }
        [data-testid="stSidebar"] [data-testid="stRadio"] label {
            color: #D7E2F0 !important;
            border-radius: 9px;
            padding: .55rem .7rem;
            margin: .12rem 0;
            transition: background .15s ease;
        }
        [data-testid="stSidebar"] [data-testid="stRadio"] label:hover {
            background: rgba(96,165,250,.12);
            color: white !important;
        }
        [data-testid="stSidebar"] [data-testid="stRadio"] label:has(input:checked) {
            background: rgba(37,99,235,.24);
            border-left: 3px solid var(--blue);
            color: white !important;
        }
        [data-testid="stSidebar"] [data-testid="stRadio"] div[role="radiogroup"] {
            gap: .1rem;
        }
        .governia-brand {
            display: flex;
            align-items: center;
            gap: 11px;
            margin: .1rem 0 2rem;
        }
        .governia-logo {
            display: grid;
            place-items: center;
            width: 38px;
            height: 38px;
            border-radius: 10px;
            background: var(--blue);
            color: white;
            font-size: 14px;
            font-weight: 800;
        }
        .governia-name {
            color: white;
            font-size: 19px;
            font-weight: 800;
            letter-spacing: -.5px;
        }
        .governia-name span { color: var(--blue-light); }
        .governia-nav-label {
            color: #94A3B8;
            font-size: 10px;
            font-weight: 800;
            letter-spacing: 1.45px;
            margin: .25rem 0 .45rem;
        }
        .governia-sidebar-footer {
            position: fixed;
            bottom: 1rem;
            left: 1rem;
            display: flex;
            align-items: center;
            gap: 8px;
            padding: .5rem .3rem;
            background: var(--navy);
            color: #CBD5E1;
            font-size: 11px;
        }
        .governia-dot {
            width: 8px;
            height: 8px;
            border-radius: 50%;
            display: inline-block;
            background: #34D399;
            box-shadow: 0 0 0 3px rgba(52,211,153,.12);
        }
        .ui-eyebrow, .governia-eyebrow {
            color: #64748B;
            font-size: 10px;
            font-weight: 800;
            letter-spacing: 1.45px;
            margin: 0 0 .35rem;
        }
        .ui-page-title {
            color: var(--text);
            font-size: clamp(1.7rem, 3vw, 2.25rem);
            font-weight: 800;
            letter-spacing: -.8px;
            line-height: 1.2;
            margin: 0;
        }
        .ui-page-detail {
            color: var(--muted) !important;
            font-size: .9rem;
            margin: .4rem 0 0;
        }
        .ui-header-badge {
            width: fit-content;
            margin-left: auto;
            border-radius: 999px;
            background: #E2E8F0;
            color: #334155;
            padding: .48rem .85rem;
            font-size: .8rem;
            font-weight: 800;
            white-space: nowrap;
        }
        .ui-section-heading { margin: 1.5rem 0 .8rem; }
        .ui-section-heading h2 {
            color: var(--text);
            font-size: 1.28rem;
            font-weight: 800;
            letter-spacing: -.35px;
            margin: 0;
        }
        .ui-section-card-title {
            color: var(--text);
            font-size: 1.1rem;
            font-weight: 800;
            margin: 0 0 .9rem;
        }
        [class*="st-key-ui-card-"] {
            background: #FFFFFF !important;
            border: 1px solid var(--line) !important;
            border-radius: 13px !important;
            box-shadow: 0 2px 8px rgba(15,37,71,.035);
            padding: 1rem 1.1rem;
        }
        .ui-agent-card {
            height: 100%;
            min-height: 195px;
            padding: 1.15rem;
            border: 1px solid var(--line);
            border-radius: 13px;
            background: #FFFFFF;
            box-shadow: 0 2px 8px rgba(15,37,71,.035);
        }
        .ui-agent-card__top {
            display: flex;
            align-items: center;
            justify-content: space-between;
            margin-bottom: .95rem;
        }
        .ui-agent-icon {
            width: 39px;
            height: 39px;
            display: grid;
            place-items: center;
            border-radius: 11px;
            font-size: 16px;
            font-weight: 800;
        }
        .ui-agent-icon--blue { background: #DBEAFE; color: #1D4ED8; }
        .ui-agent-icon--teal { background: #CCFBF1; color: #0F766E; }
        .ui-agent-icon--orange { background: #FFEDD5; color: #C2410C; }
        .ui-agent-icon--green { background: #DCFCE7; color: #15803D; }
        .ui-agent-icon--purple { background: #F3E8FF; color: #7E22CE; }
        .ui-agent-card__title {
            color: var(--text);
            font-size: 1rem;
            font-weight: 800;
            margin: 0 0 .4rem;
        }
        .ui-agent-card__summary {
            color: var(--muted) !important;
            min-height: 2.7rem;
            font-size: .82rem;
            line-height: 1.55;
            margin: 0 0 .75rem;
        }
        .ui-agent-card__link {
            color: var(--blue);
            font-size: .82rem;
            font-weight: 800;
            text-decoration: none;
        }
        .ui-agent-card__link:hover { text-decoration: underline; }
        .ui-badge {
            display: inline-flex;
            align-items: center;
            border-radius: 999px;
            padding: .27rem .62rem;
            font-size: 10px;
            font-weight: 800;
            line-height: 1.35;
            white-space: nowrap;
        }
        .ui-badge--green { color: #166534; background: #DCFCE7; }
        .ui-badge--orange { color: #9A3412; background: #FFEDD5; }
        .ui-badge--red { color: #991B1B; background: #FEE2E2; }
        .ui-badge--gray, .ui-badge--slate { color: #334155; background: #E2E8F0; }
        .governia-badge {
            display: inline-flex;
            align-items: center;
            border-radius: 999px;
            padding: .27rem .62rem;
            font-size: 10px;
            font-weight: 800;
            white-space: nowrap;
        }
        .governia-badge.blue { color: #1D4ED8; background: #DBEAFE; }
        .governia-badge.green { color: #166534; background: #DCFCE7; }
        .governia-badge.yellow { color: #9A3412; background: #FEF3C7; }
        .governia-badge.orange { color: #9A3412; background: #FFEDD5; }
        .governia-badge.red { color: #991B1B; background: #FEE2E2; }
        .governia-badge.gray { color: #334155; background: #E2E8F0; }
        .ui-distribution-card {
            height: 100%;
            padding: 1rem 1.1rem;
            border: 1px solid var(--line);
            border-radius: 13px;
            background: white;
        }
        .ui-distribution-title {
            color: var(--text);
            font-size: .98rem;
            font-weight: 800;
            margin-bottom: .9rem;
        }
        .ui-bar-row {
            display: grid;
            grid-template-columns: minmax(75px, 1fr) minmax(70px, 2fr) auto;
            align-items: center;
            gap: .7rem;
            margin: .75rem 0;
            color: #334155;
            font-size: .78rem;
        }
        .ui-bar-label { display: flex; align-items: center; gap: .35rem; }
        .ui-bar-value {
            color: var(--text);
            font-size: .82rem;
            font-weight: 800;
            font-variant-numeric: tabular-nums;
        }
        .ui-bar-track {
            height: 8px;
            overflow: hidden;
            border-radius: 99px;
            background: #E2E8F0;
        }
        .ui-bar-fill {
            display: block;
            height: 100%;
            border-radius: inherit;
        }
        .ui-bar-fill--blue { background: #2563EB; }
        .ui-bar-fill--orange { background: #F97316; }
        .ui-bar-fill--red { background: #DC2626; }
        .ui-table-wrap {
            overflow-x: auto;
            border: 1px solid var(--line);
            border-radius: 10px;
            background: white;
        }
        .ui-table {
            width: 100%;
            border-collapse: collapse;
            color: #334155;
            font-size: .82rem;
        }
        .ui-table th {
            padding: .75rem .85rem;
            background: #F8FAFC;
            color: #475569;
            text-align: left;
            font-size: .73rem;
            font-weight: 800;
            white-space: nowrap;
        }
        .ui-table td {
            padding: .7rem .85rem;
            border-top: 1px solid #E2E8F0;
            vertical-align: middle;
        }
        .ui-table td:first-child { color: var(--text); font-weight: 700; }
        .ui-timeline-item {
            display: grid;
            grid-template-columns: 20px 1fr auto;
            align-items: start;
            gap: .85rem;
            padding: .9rem 0;
            border-bottom: 1px solid #E2E8F0;
        }
        .ui-timeline-item:last-child { border-bottom: 0; }
        .ui-timeline-dot {
            width: 13px;
            height: 13px;
            margin-top: 3px;
            border: 2px solid #2563EB;
            border-radius: 50%;
            background: white;
        }
        .ui-timeline-copy strong {
            color: var(--text);
            font-size: .78rem;
            letter-spacing: .3px;
        }
        .ui-timeline-copy p {
            color: var(--muted) !important;
            font-size: .8rem;
            margin: .22rem 0 0;
        }
        .ui-timeline-item time {
            color: var(--muted);
            font-size: .72rem;
            white-space: nowrap;
        }
        [data-testid="stFileUploader"] section {
            border: 1.5px dashed #94A3B8;
            border-radius: 12px;
            background: #F8FAFC;
        }
        [data-testid="stFileUploader"] button {
            background: white !important;
            color: #1E293B !important;
            border: 1px solid var(--line) !important;
        }
        .stButton > button, .stDownloadButton > button,
        [data-testid="stFormSubmitButton"] > button {
            border-radius: 9px;
            font-weight: 800;
        }
        .stButton > button[kind^="primary"],
        [data-testid="stFormSubmitButton"] > button[kind^="primary"] {
            background: var(--blue) !important;
            color: white !important;
            border-color: var(--blue) !important;
        }
        .st-key-validation_accept [data-testid="stFormSubmitButton"] > button {
            background: #16A34A !important;
            border-color: #16A34A !important;
            color: white !important;
        }
        .st-key-validation_reject [data-testid="stFormSubmitButton"] > button {
            background: #DC2626 !important;
            border-color: #DC2626 !important;
            color: white !important;
        }
        [data-testid="stPageLink"] a {
            border: 0;
            border-radius: 9px;
            background: #E2E8F0;
            color: #0F2547;
            font-weight: 800;
        }
        [data-testid="stTextInput"] input,
        [data-testid="stTextArea"] textarea,
        [data-testid="stSelectbox"] [data-baseweb="select"] > div {
            border-radius: 9px;
            border-color: var(--line) !important;
            background: white !important;
            color: var(--text) !important;
        }
        [data-testid="stMetric"] {
            border: 1px solid var(--line);
            border-radius: 12px;
            padding: 1rem 1.1rem;
            background: white;
            box-shadow: 0 2px 8px rgba(15,37,71,.035);
        }
        .governia-section { margin: 1rem 0 .75rem; }
        .governia-section-title {
            color: var(--text);
            font-size: 1.35rem;
            font-weight: 800;
            margin: 0 0 .25rem;
        }
        .governia-section-subtitle {
            color: var(--muted);
            font-size: .88rem;
            margin: 0;
        }
        .governia-hero {
            position: relative;
            overflow: hidden;
            min-height: 240px;
            margin: .1rem 0 1.7rem;
            padding: 2.25rem 2.5rem;
            border-radius: 16px;
            background: linear-gradient(115deg, #0F2547 0%, #1E3A68 100%);
            color: white;
            box-shadow: 0 8px 22px rgba(15,37,71,.12);
        }
        .governia-hero-copy { position: relative; z-index: 2; max-width: 650px; }
        .governia-hero-tag {
            display: inline-block;
            padding: .3rem .7rem;
            border: 1px solid rgba(74,222,128,.25);
            border-radius: 20px;
            background: rgba(34,197,94,.14);
            color: #BBF7D0;
            font-size: 10px;
            font-weight: 800;
            letter-spacing: 1px;
        }
        .governia-hero h1 {
            margin: .75rem 0 .1rem;
            color: white !important;
            font-size: clamp(2.1rem, 5vw, 3rem);
            font-weight: 800;
        }
        .governia-hero h3 {
            margin: .4rem 0 .6rem;
            color: #DBEAFE !important;
            font-size: 1rem;
        }
        .governia-hero p { color: #CBD5E1 !important; line-height: 1.6; }
        .governia-orbit {
            position: absolute;
            top: 50%;
            right: 7%;
            width: 230px;
            height: 230px;
            transform: translateY(-50%);
            border: 1px solid rgba(147,197,253,.2);
            border-radius: 50%;
        }
        .governia-orbit:before, .governia-orbit:after {
            position: absolute;
            inset: 24px;
            border: 1px solid rgba(147,197,253,.18);
            border-radius: 50%;
            content: '';
        }
        .governia-orbit:after { inset: 55px; }
        .governia-orbit-center, .governia-orbit-node {
            position: absolute;
            display: grid;
            place-items: center;
            border-radius: 50%;
            color: white;
        }
        .governia-orbit-center {
            inset: 84px;
            background: rgba(37,99,235,.4);
            font-size: 12px;
            font-weight: 800;
        }
        .governia-orbit-node {
            width: 32px;
            height: 32px;
            background: #1D4E89;
            font-size: 11px;
            font-weight: 800;
        }
        .governia-orbit-node.q { top: 8px; left: 98px; }
        .governia-orbit-node.c { right: 4px; bottom: 47px; }
        .governia-orbit-node.s { left: 11px; bottom: 40px; }
        .governia-alert {
            padding: .65rem .85rem;
            border: 1px solid #F4D28B;
            border-radius: 9px;
            background: #FFF9E8;
            color: #8A5A08;
            font-size: 12px;
        }
        @media (max-width: 900px) {
            .block-container { padding: 1rem 1rem 2rem; }
            .governia-orbit { opacity: .25; right: -85px; }
            .governia-hero { padding: 1.6rem; }
        }
        </style>
        """,
        unsafe_allow_html=True,
    )
