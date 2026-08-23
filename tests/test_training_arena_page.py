"""Student-facing Training Arena route and home-entry contracts."""

from __future__ import annotations

from pathlib import Path

import pytest

from tests.ui_page_helpers import open_authenticated_page


def test_home_prominently_links_to_training_arena(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    app = open_authenticated_page(
        tmp_path, monkeypatch, route="home", username="ArenaHome"
    )
    rendered = "\n".join(
        [item.value for item in app.markdown]
        + [item.value for item in app.caption]
    )
    assert "IELTS 训练场" in rendered
    assert "IELTS Training Arena" in rendered
    assert "5题一局，快速练习雅思核心能力。" in rendered
    assert any(link.label == "开始一局" for link in app.get("page_link"))


def test_arena_starts_directly_with_four_large_answers(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    app = open_authenticated_page(
        tmp_path, monkeypatch, route="arena", username="ArenaPlay"
    )
    assert not app.exception
    assert app.title[0].value == "IELTS 训练场"
    assert any("第 1/5 题" in item.value for item in app.caption)
    answer_buttons = [button for button in app.button if button.key.startswith("arena_answer_")]
    assert len(answer_buttons) == 4


def test_both_question_types_share_one_answer_component() -> None:
    source = (
        Path(__file__).resolve().parent.parent
        / "ielts_ai_coach"
        / "views"
        / "training_arena.py"
    ).read_text(encoding="utf-8")
    assert source.count("def _render_question(") == 1
    assert source.count('key="arena_answer_grid"') == 1
    assert "st.radio" not in source


def test_arena_completes_summarizes_and_restarts(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    app = open_authenticated_page(
        tmp_path, monkeypatch, route="arena", username="ArenaRound"
    )
    for index in range(5):
        answer = next(
            button
            for button in app.button
            if button.key.startswith("arena_answer_") and not button.disabled
        )
        app = answer.click().run(timeout=10)
        assert any(
            marker in item.value
            for item in [*app.success, *app.error]
            for marker in ("回答正确", "回答错误")
        )
        label = "查看本局战绩" if index == 4 else "下一题"
        app = next(button for button in app.button if button.label == label).click().run(
            timeout=10
        )
    assert any(item.value == "本局战绩" for item in app.subheader)
    assert {metric.label for metric in app.metric} >= {"答对题数", "正确率", "得分"}
    app = next(button for button in app.button if button.label == "再来一局").click().run(
        timeout=10
    )
    assert any("第 1/5 题" in item.value for item in app.caption)
