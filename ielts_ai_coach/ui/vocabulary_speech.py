"""Streamlit wrapper for browser-native vocabulary pronunciation."""

from __future__ import annotations

from pathlib import Path
import re

import streamlit.components.v1 as components


_FRONTEND_PATH = (
    Path(__file__).resolve().parents[1]
    / "components"
    / "vocabulary_speech"
    / "frontend"
)
_speech_component = components.declare_component(
    "ielts_vocabulary_speech",
    path=str(_FRONTEND_PATH),
)
_SAFE_WORD = re.compile(r"^[a-z]+$")


def render_vocabulary_speech(word: str, *, key: str) -> None:
    """Render a replayable speech button for one validated English word."""

    if not _SAFE_WORD.fullmatch(word):
        raise ValueError("invalid_speech_word")
    _speech_component(
        word=word,
        key=key,
        default=None,
    )
