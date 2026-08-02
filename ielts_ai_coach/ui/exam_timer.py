"""Components-v1 wrapper for the shared browser-owned exam countdown."""

from __future__ import annotations

from enum import Enum
from pathlib import Path

import streamlit.components.v1 as components

from ielts_ai_coach.services.exam_controls import ExamSession


_FRONTEND_PATH = (
    Path(__file__).resolve().parents[1]
    / "components"
    / "exam_timer"
    / "frontend"
)
_exam_timer = components.declare_component(
    "ielts_exam_timer",
    path=str(_FRONTEND_PATH),
)


class ExamTimerEvent(str, Enum):
    """Trusted events emitted by the countdown client."""

    NONE = "none"
    TIMEOUT = "timeout"


def coerce_timer_event(value: object) -> ExamTimerEvent:
    """Accept only the single timeout event supported by the client."""

    if isinstance(value, dict) and value.get("action") == "timeout":
        return ExamTimerEvent.TIMEOUT
    return ExamTimerEvent.NONE


def render_exam_timer(
    session: ExamSession,
    *,
    client_key: str,
) -> ExamTimerEvent:
    """Mount one live display client backed by the server-owned deadline."""

    value = _exam_timer(
        clientKey=client_key,
        deadline=session.deadline.isoformat(),
        status=session.status.value,
        remaining=session.remaining_seconds(),
        key=f"exam_timer_{client_key}",
        default=None,
    )
    return coerce_timer_event(value)
