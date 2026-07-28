"""Components-v1 wrapper for the shared full-page hard-pause client."""

from __future__ import annotations

import hashlib
from pathlib import Path

import streamlit.components.v1 as components

from ielts_ai_coach.services.exam_controls import ExamSession, ExamStatus


_FRONTEND_PATH = (
    Path(__file__).resolve().parents[1]
    / "components"
    / "exam_hard_pause"
    / "frontend"
)
_hard_pause = components.declare_component(
    "ielts_exam_hard_pause",
    path=str(_FRONTEND_PATH),
)


def render_exam_hard_pause_client(
    session: ExamSession,
    *,
    subject: str,
    root_key: str,
    resume_key: str,
) -> bool:
    """Mount the browser-owned overlay without colliding with timer iframes."""

    minutes, seconds = divmod(session.remaining_seconds(), 60)
    token = hashlib.sha256(root_key.encode("utf-8")).hexdigest()[:16]
    value = _hard_pause(
        active=session.status is ExamStatus.PAUSED,
        subject=subject,
        remaining=f"{minutes:02d}:{seconds:02d}",
        root_class="",
        resume_class=f"st-key-{resume_key}",
        overlay_id=f"exam-hard-pause-{token}",
        key=f"exam_hard_pause_{root_key}",
        default=None,
    )
    return isinstance(value, dict) and value.get("action") == "resume"
