"""Styles centralisés de l'interface Govern IA."""

from __future__ import annotations

import streamlit as st


def inject_css() -> None:
    """Applique la charte visuelle sur l'ensemble de l'application."""
    st.markdown(
        """
        <style>
        @import url('https://fonts.googleapis.com/css2?family=DM+Sans:wght@400;500;600;700;800&display=swap');

        :root {
            --navy: #0f1f3d;
            --navy-hero: #0f2447;
            --blue: #2563eb;
            --blue-light: #60a5fa;
            --page: #f4f6fa;
            --muted: #64748b;
            --line: #e5eaf2;
            --text-color: #15233b;
            --background-color: #f4f6fa;
            --secondary-background-color: #ffffff;
            --primary-color: #2563eb;
        }

        html, body, [class*="css"], [data-testid="stAppViewContainer"] {
            font-family: 'DM Sans', sans-serif;
        }
        [data-testid="stAppViewContainer"] {
            background: var(--page) !important;
            color: #15233b;
            color-scheme: light;
        }
        [data-testid="stHeader"], [data-testid="stToolbar"],
        #stSidebarNav, [data-testid="stSidebarNav"], #MainMenu, footer {
            display: none !important;
            height: 0;
        }
        [data-testid="stMain"] {
            color: #15233b !important;
        }
        #stMain h1, #stMain h2, #stMain h3, #stMain p, #stMain label {
            color: #15233b !important;
        }
        #stMain .governia-hero h1 {
            color: white !important;
        }
        #stMain .governia-hero h3 {
            color: #d9e7fb !important;
        }
        #stMain .governia-hero p {
            color: #b7c8e1 !important;
        }
        #stMain .governia-hero-tag,
        #stMain .governia-orbit-node,
        #stMain .governia-orbit-center {
            color: white !important;
        }
        #stMain .governia-section-title {
            color: #15233b !important;
        }
        #stMain .governia-section-subtitle,
        #stMain .governia-eyebrow {
            color: #64748b !important;
        }
        #stMain input, #stMain textarea {
            background: white !important;
            color: #15233b !important;
        }
        #stMain input::placeholder, #stMain textarea::placeholder {
            color: #64748b !important;
            opacity: 1;
        }
        #stMain button[kind^="primary"] {
            background: #2563eb !important;
            color: white !important;
            border-color: #2563eb !important;
        }
        [data-testid="stMain"] [data-testid="stWidgetLabel"] p,
        [data-testid="stMain"] [data-testid="stMarkdownContainer"] p {
            color: #334155 !important;
        }
        [data-testid="stMain"] .governia-hero p {
            color: #b7c8e1 !important;
        }
        [data-testid="stMain"] .governia-section-title {
            color: #15233b !important;
        }
        [data-testid="stMain"] .governia-section-subtitle,
        [data-testid="stMain"] .governia-eyebrow {
            color: #64748b !important;
        }
        .block-container {
            max-width: 1440px;
            padding: 2rem 3rem 3rem;
        }
        [data-testid="stSidebar"] {
            background: var(--navy);
            border-right: 1px solid rgba(255,255,255,.06);
        }
        [data-testid="stSidebar"] > div:first-child {
            background: var(--navy);
        }
        [data-testid="stSidebar"] [data-testid="stMarkdownContainer"] {
            color: #e8eef9;
        }
        [data-testid="stSidebar"] [data-testid="stRadio"] label {
            color: #d3deef !important;
            border-radius: 9px;
            padding: .55rem .7rem;
            margin: .12rem 0;
            transition: background .15s ease;
        }
        [data-testid="stSidebar"] [data-testid="stRadio"] label:hover {
            background: rgba(96,165,250,.12);
            color: white !important;
        }
        [data-testid="stSidebar"] [data-testid="stRadio"] [data-testid="stMarkdownContainer"] p {
            color: inherit;
        }
        [data-testid="stSidebar"] [data-testid="stRadio"] input:checked + div {
            color: white;
        }
        [data-testid="stSidebar"] [data-testid="stRadio"] label:has(input:checked) {
            background: rgba(37,99,235,.22);
            border-left: 3px solid #60a5fa;
            color: white !important;
        }
        [data-testid="stSidebar"] [data-testid="stRadio"] div[role="radiogroup"] {
            gap: .1rem;
        }
        [data-testid="stFileUploader"] section {
            border: 1.5px dashed #9eb4d3;
            border-radius: 12px;
            background: #f8faff;
        }
        [data-testid="stFileUploader"] section:hover {
            border-color: var(--blue);
            background: #f0f5ff;
        }
        [data-testid="stFileUploader"] button {
            background: white !important;
            color: #1e293b !important;
            border: 1px solid #d7dfeb !important;
        }
        .stButton > button, .stDownloadButton > button,
        [data-testid="stFormSubmitButton"] > button {
            border-radius: 9px;
            font-weight: 700;
            transition: transform .12s ease, box-shadow .12s ease;
        }
        .stButton > button[kind^="primary"],
        [data-testid="stFormSubmitButton"] > button[kind^="primary"] {
            background: var(--blue) !important;
            color: white !important;
            border: 1px solid var(--blue) !important;
        }
        .stButton > button:hover, .stDownloadButton > button:hover {
            transform: translateY(-1px);
            box-shadow: 0 5px 14px rgba(37,99,235,.16);
        }
        [data-testid="stTextInput"] input,
        [data-testid="stTextArea"] textarea,
        [data-testid="stSelectbox"] [data-baseweb="select"] > div {
            border-radius: 9px;
            border-color: #d7dfeb !important;
            background: white !important;
            color: #15233b !important;
        }
        [data-testid="stTextInput"] input::placeholder,
        [data-testid="stTextArea"] textarea::placeholder {
            color: #64748b !important;
            opacity: 1;
        }
        [data-testid="stMetric"] {
            background: white;
            border: 1px solid var(--line);
            border-radius: 12px;
            padding: 1rem 1.1rem;
            box-shadow: 0 3px 12px rgba(20,40,75,.045);
        }
        [data-testid="stTabs"] button {
            font-weight: 600;
        }
        .governia-brand {
            display: flex;
            align-items: center;
            gap: 11px;
            margin: .2rem 0 2.2rem;
        }
        .governia-logo {
            display: grid;
            place-items: center;
            width: 42px;
            height: 42px;
            border-radius: 11px;
            background: #2563eb;
            color: white;
            font-size: 15px;
            font-weight: 800;
            letter-spacing: -.5px;
            box-shadow: 0 5px 14px rgba(37,99,235,.25);
        }
        .governia-name {
            color: white;
            font-size: 20px;
            font-weight: 800;
            letter-spacing: -.7px;
        }
        .governia-name span {
            color: #60a5fa;
        }
        .governia-nav-label {
            color: #8292ac;
            font-size: 10px;
            font-weight: 800;
            letter-spacing: 1.5px;
            margin: .25rem 0 .45rem;
        }
        .governia-sidebar-footer {
            position: fixed;
            bottom: 1.1rem;
            left: 1rem;
            color: #aab8cd;
            font-size: 12px;
            display: flex;
            align-items: center;
            gap: 8px;
            background: var(--navy);
            padding: .5rem .3rem;
        }
        .governia-dot {
            width: 8px;
            height: 8px;
            border-radius: 50%;
            display: inline-block;
            background: #34d399;
            box-shadow: 0 0 0 3px rgba(52,211,153,.12);
        }
        .governia-hero {
            position: relative;
            overflow: hidden;
            border-radius: 18px;
            padding: 2.4rem 2.7rem;
            min-height: 255px;
            background: linear-gradient(115deg, #0f2447 0%, #1a3a6b 100%);
            color: white;
            box-shadow: 0 12px 30px rgba(15,36,71,.16);
            margin: .25rem 0 2rem;
        }
        .governia-hero-copy {
            position: relative;
            z-index: 2;
            max-width: 650px;
        }
        .governia-hero-tag {
            display: inline-block;
            color: #bbf7d0;
            background: rgba(34,197,94,.16);
            border: 1px solid rgba(74,222,128,.27);
            border-radius: 20px;
            padding: .32rem .75rem;
            font-size: 10px;
            font-weight: 800;
            letter-spacing: 1.2px;
        }
        .governia-hero h1 {
            color: white !important;
            margin: .75rem 0 .1rem;
            font-size: clamp(2.2rem, 5vw, 3.25rem);
            letter-spacing: -2px;
            line-height: 1.05;
        }
        .governia-hero h3 {
            color: #d9e7fb !important;
            font-size: 1.08rem;
            font-weight: 500;
            margin: .45rem 0 .65rem;
        }
        .governia-hero p {
            color: #b7c8e1;
            max-width: 580px;
            line-height: 1.6;
            margin: 0;
        }
        .governia-orbit {
            position: absolute;
            width: 255px;
            height: 255px;
            right: 7%;
            top: 50%;
            transform: translateY(-50%);
            border: 1px solid rgba(147,197,253,.20);
            border-radius: 50%;
        }
        .governia-orbit:before, .governia-orbit:after {
            content: '';
            position: absolute;
            inset: 25px;
            border: 1px solid rgba(147,197,253,.18);
            border-radius: 50%;
        }
        .governia-orbit:after {
            inset: 57px;
            border-color: rgba(147,197,253,.24);
        }
        .governia-orbit-center {
            position: absolute;
            inset: 92px;
            display: grid;
            place-items: center;
            border-radius: 50%;
            background: rgba(37,99,235,.35);
            color: #dbeafe;
            font-size: 13px;
            font-weight: 800;
        }
        .governia-orbit-node {
            position: absolute;
            width: 34px;
            height: 34px;
            display: grid;
            place-items: center;
            border: 1px solid rgba(191,219,254,.35);
            border-radius: 50%;
            color: white;
            background: #1d4e89;
            font-size: 12px;
            font-weight: 800;
            box-shadow: 0 0 18px rgba(96,165,250,.2);
        }
        .governia-orbit-node.q { top: 10px; left: 108px; }
        .governia-orbit-node.c { right: 5px; bottom: 52px; }
        .governia-orbit-node.s { left: 13px; bottom: 44px; }
        .governia-section {
            margin: 1.35rem 0 1rem;
        }
        .governia-eyebrow {
            color: #64748b;
            font-size: 10px;
            font-weight: 800;
            letter-spacing: 1.5px;
            margin-bottom: .28rem;
        }
        .governia-section-title {
            color: #15233b;
            font-size: 1.45rem;
            font-weight: 800;
            letter-spacing: -.55px;
            margin: 0 0 .3rem;
        }
        .governia-section-subtitle {
            color: var(--muted);
            font-size: .92rem;
            margin: 0;
        }
        .governia-card {
            background: white;
            border: 1px solid var(--line);
            border-radius: 12px;
            padding: 1rem 1.1rem;
            box-shadow: 0 3px 12px rgba(20,40,75,.045);
        }
        .governia-kpi-label {
            color: #64748b;
            font-size: 12px;
            font-weight: 600;
        }
        .governia-kpi-value {
            color: #15233b;
            font-size: 1.8rem;
            font-weight: 800;
            letter-spacing: -.8px;
            line-height: 1.25;
            margin-top: .2rem;
        }
        .governia-bar-row {
            margin: .9rem 0 1.1rem;
        }
        .governia-bar-label {
            display: flex;
            justify-content: space-between;
            gap: 1rem;
            margin-bottom: .4rem;
            color: #334155;
            font-size: .85rem;
        }
        .governia-bar-label strong {
            color: #15233b;
            font-variant-numeric: tabular-nums;
        }
        .governia-bar-track {
            width: 100%;
            height: 9px;
            overflow: hidden;
            border-radius: 99px;
            background: #e8edf5;
        }
        .governia-bar-fill {
            display: block;
            height: 100%;
            border-radius: inherit;
        }
        .governia-badge {
            display: inline-flex;
            align-items: center;
            gap: 6px;
            border-radius: 99px;
            padding: .28rem .65rem;
            font-size: 11px;
            font-weight: 700;
            white-space: nowrap;
        }
        .governia-badge.blue { color: #1d4ed8; background: #dbeafe; }
        .governia-badge.green { color: #047857; background: #d1fae5; }
        .governia-badge.yellow { color: #a16207; background: #fef3c7; }
        .governia-badge.orange { color: #c2410c; background: #ffedd5; }
        .governia-badge.red { color: #b91c1c; background: #fee2e2; }
        .governia-badge.gray { color: #475569; background: #e2e8f0; }
        .governia-alert {
            border: 1px solid #f4d28b;
            background: #fff9e8;
            color: #8a5a08;
            border-radius: 9px;
            padding: .65rem .85rem;
            font-size: 12px;
        }
        @media (max-width: 900px) {
            .block-container { padding: 1.2rem 1.1rem 2rem; }
            .governia-orbit { opacity: .35; right: -80px; }
            .governia-hero { padding: 1.7rem; }
        }
        </style>
        """,
        unsafe_allow_html=True,
    )
