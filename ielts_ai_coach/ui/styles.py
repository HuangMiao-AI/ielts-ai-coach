"""Visual styling for the V1 Streamlit application."""

from __future__ import annotations

import streamlit as st


APP_CSS = """
<style>
    .stApp {
        background:
            radial-gradient(circle at top right, #dff7f4 0, transparent 32rem),
            linear-gradient(180deg, #f7fbff 0%, #ffffff 48%);
    }
    .block-container {
        max-width: 1040px;
        padding-top: 2.2rem;
        padding-bottom: 4rem;
        min-width: 0;
    }
    .auth-hero {
        margin: 0 auto 1.6rem;
        max-width: 760px;
        padding: 2.2rem;
        border-radius: 24px;
        color: white;
        background: linear-gradient(135deg, #0f766e, #0284c7);
        box-shadow: 0 18px 48px rgba(2, 132, 199, 0.16);
        text-align: center;
    }
    .auth-hero h1 {
        color: white;
        margin: .45rem 0 .6rem;
        font-size: clamp(2rem, 5vw, 3rem);
    }
    .auth-hero p {
        margin: 0;
        color: rgba(255, 255, 255, .9);
        font-size: 1.05rem;
    }
    .auth-kicker {
        display: inline-block;
        padding: .28rem .7rem;
        border: 1px solid rgba(255, 255, 255, .4);
        border-radius: 999px;
        font-size: .76rem;
        font-weight: 800;
        letter-spacing: .08em;
    }
    .section-heading {
        margin: 1.5rem 0 .65rem;
        color: #12343b;
        font-size: 1.2rem;
        font-weight: 800;
    }
    .empty-card {
        margin-top: 1rem;
        padding: 1.2rem 1.3rem;
        border: 1px solid #dbeafe;
        border-radius: 18px;
        background: rgba(255, 255, 255, .9);
        box-shadow: 0 10px 30px rgba(15, 118, 110, .06);
    }
    div[data-testid="stMetric"] {
        padding: .8rem 1rem;
        border: 1px solid #dbeafe;
        border-radius: 16px;
        background: white;
    }
    .stButton > button, .stFormSubmitButton > button {
        min-height: 2.7rem;
        border-radius: 12px;
        font-weight: 750;
    }
    .current-user {
        margin: .4rem 0 .2rem;
        color: #52717a;
        font-size: .82rem;
        font-weight: 700;
        text-align: right;
    }
    .task-time-badge {
        display: inline-flex;
        align-items: center;
        margin: .15rem 0 .45rem;
        padding: .28rem .7rem;
        border-radius: 999px;
        color: #0f5e59;
        background: #e6f7f5;
        font-size: .88rem;
        font-weight: 800;
        white-space: nowrap;
        overflow: visible;
        text-overflow: clip;
    }
    .core-entry {
        margin-bottom: .6rem;
        padding: .75rem .85rem;
        border: 1px solid #dbeafe;
        border-radius: 14px;
        background: rgba(255, 255, 255, .92);
    }
    .st-key-mobile_quick_navigation {
        display: none;
    }
    html, body, .stApp, [data-testid="stAppViewContainer"] {
        max-width: 100%;
        overflow-x: clip;
    }
    [data-testid="stMarkdownContainer"],
    [data-testid="stVerticalBlock"],
    [data-testid="stForm"] {
        min-width: 0;
        overflow-wrap: anywhere;
    }
    @media (max-width: 1024px) {
        .block-container {
            max-width: 100%;
            padding-left: 1.25rem;
            padding-right: 1.25rem;
        }
    }
    @media (max-width: 768px) {
        .block-container {
            max-width: 100%;
            padding: 1rem .85rem 4.5rem;
        }
        h1 {
            font-size: 1.65rem !important;
            line-height: 1.25 !important;
        }
        h2 {
            font-size: 1.3rem !important;
        }
        h3 {
            font-size: 1.08rem !important;
        }
        .section-heading {
            margin-top: 1.15rem;
            font-size: 1.08rem;
        }
        .current-user {
            text-align: left;
        }
        .st-key-mobile_quick_navigation {
            display: block;
            margin: .25rem 0 .65rem;
        }
        .st-key-mobile_quick_navigation details {
            border: 1px solid #dbeafe;
            border-radius: 14px;
            background: rgba(255, 255, 255, .94);
        }
        [data-testid="stHorizontalBlock"] {
            flex-direction: column !important;
            gap: .65rem !important;
        }
        [data-testid="stColumn"] {
            width: 100% !important;
            min-width: 0 !important;
            flex: 1 1 100% !important;
        }
        div[data-testid="stMetric"] {
            width: 100%;
            padding: .75rem .85rem;
        }
        .stButton > button,
        .stFormSubmitButton > button,
        [data-testid="stPageLink"] a {
            width: 100% !important;
            min-height: 2.9rem;
            justify-content: center;
        }
        [data-testid="stForm"] {
            width: 100%;
        }
        [data-testid="stDataFrame"],
        [data-testid="stTable"] {
            max-width: 100%;
        }
        .auth-hero {
            padding: 1.5rem 1rem;
            border-radius: 18px;
        }
        .task-time-badge {
            max-width: 100%;
            white-space: nowrap;
        }
    }
    footer { visibility: hidden; }
</style>
"""


def apply_styles() -> None:
    """Apply the shared CSS used by public and protected pages."""

    st.markdown(APP_CSS, unsafe_allow_html=True)
