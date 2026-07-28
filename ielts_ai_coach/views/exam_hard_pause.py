"""Shared Streamlit entry point for full-page paused exam states."""

from __future__ import annotations

import hashlib

import streamlit as st

from ielts_ai_coach.services.exam_controls import ExamSession
from ielts_ai_coach.ui.exam_hard_pause import render_exam_hard_pause_client


def render_hard_pause_overlay(
    session: ExamSession,
    *,
    subject: str,
    root_key: str,
) -> bool:
    """Mount the independent pause client and expose its hidden resume action."""

    token = hashlib.sha256(root_key.encode("utf-8")).hexdigest()[:16]
    resume_key = f"hard_pause_resume_{token}"
    resumed_from_overlay = render_exam_hard_pause_client(
        session,
        subject=subject,
        root_key=root_key,
        resume_key=resume_key,
    )
    resumed_from_fallback = st.button(
        "恢复考试",
        key=resume_key,
        type="primary",
        use_container_width=True,
    )
    return resumed_from_overlay or resumed_from_fallback
