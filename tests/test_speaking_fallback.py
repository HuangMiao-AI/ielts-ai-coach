"""Microphone recovery and honest text fallback for Speaking practice."""

from __future__ import annotations

from pathlib import Path

import pytest

from tests.ui_page_helpers import open_authenticated_page


PROJECT_ROOT = Path(__file__).resolve().parent.parent


def _button(app, label: str):
    """Return one visible button by its exact label."""

    return next(button for button in app.button if button.label == label)


def test_speaking_page_explains_microphone_test_and_fallback_contract() -> None:
    """The page must disclose permission recovery and never promise scoring."""

    source = (
        PROJECT_ROOT / "ielts_ai_coach" / "views" / "speaking.py"
    ).read_text(encoding="utf-8")

    assert "麦克风测试" in source
    assert "麦克风无法使用" in source
    assert "文字回答替代" in source
    assert "浏览器设置" in source
    assert "不提供自动评分" in source
    assert "自动评分已经可用" not in source


def test_microphone_failure_unlocks_text_completion_without_a_score(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """A rejection path still permits an honest local text practice outcome."""

    app = open_authenticated_page(
        tmp_path,
        monkeypatch,
        route="speaking",
        username="SpeakingFallback",
    )

    app = _button(app, "麦克风测试").click().run(timeout=10)
    assert any("权限" in item.value for item in app.info)
    app = _button(app, "麦克风无法使用").click().run(timeout=10)
    fallback = next(
        area for area in app.text_area if area.label == "文字回答替代"
    )
    fallback.input(
        "I prefer a quiet place because it helps me organise my ideas."
    ).run(timeout=10)

    complete = _button(app, "完成本次练习")
    assert complete.disabled is False
    app = complete.click().run(timeout=10)

    assert any("文字回答" in item.value for item in app.success)
    assert not any("分数" in item.value and "已获得" in item.value for item in app.success)
