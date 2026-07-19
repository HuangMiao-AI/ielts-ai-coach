"""Contracts for the honest local Listening demo flow."""

from __future__ import annotations

from pathlib import Path

import pytest

from tests.ui_page_helpers import open_authenticated_page

PROJECT_ROOT = Path(__file__).resolve().parent.parent


def test_listening_page_has_sections_timer_confirmation_and_no_score_claim() -> None:
    """The demo may guide practice but must not imply real scoring."""

    source = (
        PROJECT_ROOT / "ielts_ai_coach" / "views" / "listening.py"
    ).read_text(encoding="utf-8")

    assert "Demo" in source
    assert "选择练习" in source
    assert "Section 1" in source and "Section 4" in source
    assert "剩余时间" in source
    assert "确认完成" in source
    assert "不保存分数" in source
    assert "自动评分" not in source


def test_listening_demo_completes_without_creating_a_score(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """A student can navigate and complete the transient Demo checklist."""

    app = open_authenticated_page(
        tmp_path,
        monkeypatch,
        route="listening",
        username="ListeningDemo",
    )
    next(button for button in app.button if button.label == "开始 Demo").click().run(
        timeout=10
    )
    for index in range(3):
        app.text_input[0].input(f"answer-{index}").run(timeout=10)
        if index < 2:
            next(
                button for button in app.button if button.label == "下一项"
            ).click().run(timeout=10)
    next(
        button for button in app.button if button.label == "完成练习"
    ).click().run(timeout=10)
    assert any("不保存分数" in item.value for item in app.warning)
    next(
        button for button in app.button if button.label == "确认完成"
    ).click().run(timeout=10)
    assert any("Demo 已完成" in item.value for item in app.success)
    assert not app.metric
