"""Desktop and responsive contracts for the independent core learning flow."""

from __future__ import annotations

from pathlib import Path

from ielts_ai_coach.ui.styles import APP_CSS


PROJECT_ROOT = Path(__file__).resolve().parent.parent


def _source(path: str) -> str:
    """Read one active source file as UTF-8."""

    return (PROJECT_ROOT / path).read_text(encoding="utf-8")


def test_home_has_one_independent_skill_group_with_honest_empty_plan() -> None:
    """Home keeps exactly one four-skill entry group even without a plan."""

    source = _source("ielts_ai_coach/views/dashboard.py")

    assert source.count('_section("快捷开始")') == 1
    for route in ("reading", "listening", "writing", "speaking"):
        assert f'("{route}",' in source
    assert "8 篇原创文章" in source
    assert "2 套 Mini Practice" in source
    assert "Task 1 / Task 2" in source
    assert "Part 1 / 2 / 3" in source
    assert "目前没有学习计划。你可以生成计划，也可以直接开始四科练习。" in source


def test_skill_cards_expose_actionable_honest_metadata() -> None:
    """Each skill exposes its actual practice scope without fake claims."""

    reading = _source("ielts_ai_coach/views/reading.py")
    listening = _source("ielts_ai_coach/views/listening.py") + _source(
        "ielts_ai_coach/views/listening_sections.py"
    )
    writing = _source("ielts_ai_coach/views/writing.py")
    speaking = _source("ielts_ai_coach/views/speaking.py")

    assert "版本" in reading and "难度" in reading and "最近成绩" in reading
    assert "2 个短场景" in listening and "本地 WAV 开发用合成音频" in listening
    assert "建议" in writing and "至少" in writing
    assert "准备时间" in speaking and "回答时间" in speaking
    assert "排行榜" not in "\n".join((reading, listening, writing, speaking))


def test_css_covers_supported_mobile_and_desktop_widths_without_overflow() -> None:
    """Responsive rules keep cards and primary controls within the viewport."""

    for width in ("375", "430", "768", "1024", "1366", "1440", "1920"):
        assert width in APP_CSS
    assert "overflow-x: hidden" in APP_CSS
    assert "minmax(0, 1fr)" in APP_CSS
    assert "min-width: 0" in APP_CSS
    assert "flex-wrap: wrap !important" in APP_CSS
    assert "min-height: 44px" in APP_CSS
    assert "calc(5.5rem + env(safe-area-inset-bottom))" in APP_CSS
    assert "@media (min-width: 1366px)" in APP_CSS
    assert "@media (max-width: 375px)" in APP_CSS
