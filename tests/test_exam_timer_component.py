"""Contracts for the shared browser-owned IELTS exam countdown."""

from __future__ import annotations

from importlib import import_module, util
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parent.parent
FRONTEND = (
    PROJECT_ROOT
    / "ielts_ai_coach"
    / "components"
    / "exam_timer"
    / "frontend"
    / "index.html"
)
CONTROL_PANEL = (
    PROJECT_ROOT / "ielts_ai_coach" / "views" / "exam_control_panel.py"
)


def _frontend_source() -> str:
    """Return the packaged timer source after proving it exists."""

    assert FRONTEND.exists(), "the shared timer component is missing"
    return FRONTEND.read_text(encoding="utf-8")


def test_timer_ticks_without_streamlit_reruns_and_corrects_wall_clock() -> None:
    """An idle or backgrounded page must derive display time in the browser."""

    source = _frontend_source()

    assert "Date.now()" in source
    assert "setInterval(update, 1000)" in source
    assert 'addEventListener("visibilitychange", update)' in source
    assert "update();" in source


def test_timer_freezes_paused_state_and_clamps_at_zero() -> None:
    """Pause uses the server snapshot and no display may become negative."""

    source = _frontend_source()

    assert 'config.status === "paused"' in source
    assert "config.remaining" in source
    assert "Math.max(0" in source
    assert 'padStart(2, "0")' in source


def test_timeout_event_is_emitted_once_and_all_timers_are_cleaned_up() -> None:
    """Expiry reruns Python once and component teardown leaves no callbacks."""

    source = _frontend_source()

    assert "let timeoutSent = false" in source
    assert "if (!timeoutSent" in source
    assert "timeoutSent = true" in source
    assert 'action: "timeout"' in source
    assert "streamlit:setComponentValue" in source
    assert "clearInterval" in source
    assert "clearTimeout" in source
    assert 'removeEventListener("visibilitychange", update)' in source
    assert 'addEventListener("pagehide", teardown' in source


def test_python_wrapper_accepts_only_the_timeout_event() -> None:
    """Untrusted component values must not create arbitrary server actions."""

    module_name = "ielts_ai_coach.ui.exam_timer"
    assert util.find_spec(module_name) is not None, "timer wrapper is missing"
    module = import_module(module_name)

    assert module.coerce_timer_event({"action": "timeout"}).value == "timeout"
    assert module.coerce_timer_event({"action": "resume"}).value == "none"
    assert module.coerce_timer_event(None).value == "none"


def test_pause_transition_renders_the_frozen_client_in_the_same_run() -> None:
    """The hidden base clock must receive paused state before the overlay."""

    panel_source = CONTROL_PANEL.read_text(encoding="utf-8")

    assert "timer_slot = st.empty()" in panel_source
    assert panel_source.index("timer_slot = st.empty()") < panel_source.index(
        "pause_exam(session)"
    )
    assert panel_source.index("pause_exam(session)") < panel_source.index(
        "with timer_slot.container():"
    )


def test_reading_listening_and_writing_share_one_timer_renderer() -> None:
    """All three timed skills must keep using the same control panel."""

    for relative_path in (
        "ielts_ai_coach/views/reading_workspace.py",
        "ielts_ai_coach/views/listening.py",
        "ielts_ai_coach/views/writing.py",
    ):
        source = (PROJECT_ROOT / relative_path).read_text(encoding="utf-8")
        assert "render_exam_control_panel" in source

    panel_source = CONTROL_PANEL.read_text(encoding="utf-8")
    assert "render_exam_timer" in panel_source
    assert "ExamTimerEvent.TIMEOUT" in panel_source
