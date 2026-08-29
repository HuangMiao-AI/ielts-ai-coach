"""Static and wrapper contracts for browser-native vocabulary speech."""

from __future__ import annotations

from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parent.parent
FRONTEND = (
    PROJECT_ROOT
    / "ielts_ai_coach"
    / "components"
    / "vocabulary_speech"
    / "frontend"
    / "index.html"
)


def test_speech_component_cancels_before_play_and_on_teardown() -> None:
    """Rapid replay, word changes, and navigation cannot stack old speech."""

    source = FRONTEND.read_text(encoding="utf-8")

    assert "speechSynthesis.cancel()" in source
    assert source.index("speechSynthesis.cancel()") < source.index("speechSynthesis.speak")
    assert 'addEventListener("pagehide", teardown' in source
    assert 'addEventListener("beforeunload", teardown' in source
    assert 'removeEventListener("voiceschanged"' in source


def test_speech_component_prefers_british_then_american_then_english() -> None:
    """Voice choice is asynchronous and deterministic without assuming a platform."""

    source = FRONTEND.read_text(encoding="utf-8")

    assert 'lang.toLowerCase() === "en-gb"' in source
    assert 'lang.toLowerCase() === "en-us"' in source
    assert 'lang.toLowerCase().startsWith("en")' in source
    assert 'addEventListener("voiceschanged"' in source
    assert "SpeechSynthesisUtterance" in source


def test_speech_component_fails_softly_without_browser_support() -> None:
    """Unsupported speech leaves the page usable and explains the fallback."""

    source = FRONTEND.read_text(encoding="utf-8")

    assert '"speechSynthesis" in window' in source
    assert "当前浏览器暂不支持语音播放，请尝试最新版 Chrome、Edge 或 Safari。" in source
    assert "disabled = true" in source


def test_speech_component_fails_softly_when_no_english_voice_exists() -> None:
    """A loaded voice list without English must not speak with a guessed voice."""

    source = FRONTEND.read_text(encoding="utf-8")

    assert "voices.length > 0 && !voice" in source
    assert "if (voices.length === 0)" in source
