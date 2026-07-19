"""Reusable presentation components for Streamlit pages."""

from __future__ import annotations

from html import escape

import streamlit as st


_STATUS_TONES = {"neutral", "success", "warning", "danger"}


def render_page_header(
    title: str,
    description: str,
    *,
    eyebrow: str | None = None,
    progress: float | None = None,
) -> None:
    """Render a consistent page heading with optional progress."""

    eyebrow_html = (
        f'<div class="page-eyebrow">{escape(eyebrow)}</div>'
        if eyebrow
        else ""
    )
    st.markdown(
        (
            '<header class="page-header">'
            f"{eyebrow_html}"
            f"<h1>{escape(title)}</h1>"
            f"<p>{escape(description)}</p>"
            "</header>"
        ),
        unsafe_allow_html=True,
    )
    if progress is not None:
        st.progress(max(0.0, min(1.0, progress)))


def render_status_pill(label: str, tone: str = "neutral") -> None:
    """Render an escaped status label using an approved semantic tone."""

    if tone not in _STATUS_TONES:
        raise ValueError(f"Unsupported status tone: {tone}")
    st.markdown(
        (
            f'<span class="status-pill status-pill--{tone}">'
            f"{escape(label)}</span>"
        ),
        unsafe_allow_html=True,
    )


def render_metric_card(
    label: str,
    value: str,
    *,
    delta: str | None = None,
    help_text: str | None = None,
) -> None:
    """Render a metric through Streamlit's accessible metric component."""

    st.metric(label, value, delta=delta, help=help_text)
