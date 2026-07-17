"""Visual styling for the student-friendly Streamlit interface."""

import streamlit as st


APP_CSS = """
<style>
    .stApp {
        background: linear-gradient(180deg, #f5fbff 0%, #ffffff 32%);
    }
    .block-container {
        max-width: 1060px;
        padding-top: 2.2rem;
        padding-bottom: 4rem;
    }
    .coach-hero {
        padding: 1.8rem 2rem;
        border-radius: 24px;
        background: linear-gradient(135deg, #0f766e 0%, #0891b2 100%);
        color: white;
        box-shadow: 0 18px 40px rgba(8, 145, 178, 0.16);
        margin-bottom: 1.4rem;
    }
    .coach-hero h1 {
        color: white;
        font-size: clamp(2rem, 5vw, 3.1rem);
        line-height: 1.1;
        margin: 0 0 .55rem 0;
    }
    .coach-hero p {
        color: rgba(255,255,255,.9);
        font-size: 1.05rem;
        margin: 0;
    }
    .coach-kicker {
        display: inline-block;
        padding: .3rem .7rem;
        border: 1px solid rgba(255,255,255,.35);
        border-radius: 999px;
        font-size: .78rem;
        font-weight: 700;
        letter-spacing: .05em;
        margin-bottom: .85rem;
    }
    .section-title {
        font-size: 1.25rem;
        font-weight: 800;
        color: #12343b;
        margin: 1.4rem 0 .35rem;
    }
    .section-subtitle {
        color: #64748b;
        margin: 0 0 1rem;
    }
    .advice-card, .plan-card, .history-card {
        border: 1px solid #dbeafe;
        background: rgba(255,255,255,.92);
        border-radius: 16px;
        padding: 1rem 1.1rem;
        margin: .55rem 0;
        box-shadow: 0 8px 24px rgba(15, 118, 110, .06);
    }
    .advice-card h4, .plan-card h4 {
        color: #0f766e;
        margin: 0 0 .45rem;
    }
    .plan-time {
        display: inline-block;
        min-width: 64px;
        text-align: center;
        color: #0369a1;
        background: #e0f2fe;
        border-radius: 999px;
        padding: .18rem .55rem;
        font-weight: 800;
        margin-right: .45rem;
    }
    div[data-testid="stMetric"] {
        border: 1px solid #dbeafe;
        border-radius: 16px;
        padding: .7rem 1rem;
        background: white;
    }
    .stButton > button, .stFormSubmitButton > button {
        border-radius: 12px;
        font-weight: 750;
        min-height: 2.8rem;
    }
    footer { visibility: hidden; }
</style>
"""


def apply_styles() -> None:
    st.markdown(APP_CSS, unsafe_allow_html=True)
