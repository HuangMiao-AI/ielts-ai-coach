"""Install local Progressive Web App metadata in the Streamlit document."""

from __future__ import annotations

from textwrap import dedent

import streamlit as st


def build_pwa_head_markup() -> str:
    """Return local manifest, theme, and Apple mobile metadata."""

    return dedent(
        """
        <link rel="manifest" href="/app/static/manifest.webmanifest">
        <link rel="apple-touch-icon"
              href="/app/static/icons/apple-touch-icon.png">
        <link rel="icon" type="image/png" sizes="32x32"
              href="/app/static/icons/favicon-32.png">
        <meta name="theme-color" content="#0F766E">
        <meta name="apple-mobile-web-app-capable" content="yes">
        <meta name="apple-mobile-web-app-status-bar-style"
              content="black-translucent">
        <meta name="apple-mobile-web-app-title" content="IELTS Coach">
        <meta name="mobile-web-app-capable" content="yes">
        """
    ).strip()


def install_pwa_metadata() -> None:
    """Render install metadata without registering offline behavior."""

    st.markdown(build_pwa_head_markup(), unsafe_allow_html=True)
