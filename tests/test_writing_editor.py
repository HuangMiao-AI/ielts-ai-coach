"""Contracts for the resilient Writing editor."""

from __future__ import annotations

from pathlib import Path

import pytest

from tests.ui_page_helpers import open_authenticated_page

PROJECT_ROOT = Path(__file__).resolve().parent.parent


def test_writing_editor_uses_live_isolated_drafts_and_submit_guard() -> None:
    """Task drafts, live count, clear confirmation, and submit lock are required."""

    source = (
        PROJECT_ROOT / "ielts_ai_coach" / "views" / "writing.py"
    ).read_text(encoding="utf-8")

    assert "st.form(" not in source
    assert "draft_key(" in source
    assert "count_words(content)" in source
    assert "确认清空当前草稿" in source
    assert "claim_submission(" in source
    assert "release_submission(" in source


def test_writing_editor_updates_word_count_and_requires_confirmation(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Editing is live and the first submit click never calls the provider."""

    app = open_authenticated_page(
        tmp_path,
        monkeypatch,
        route="writing",
        username="WritingEditor",
    )
    prompt = next(area for area in app.text_area if area.label == "作文题目")
    content = next(area for area in app.text_area if area.label == "作文正文")
    prompt.input("Discuss whether practical skills belong in schools.")
    content.input("One two three four five.").run(timeout=10)

    assert any("当前字数：5词" in item.value for item in app.caption)
    next(
        button for button in app.button if button.label == "提交AI批改"
    ).click().run(timeout=10)
    assert any("占用一次成功额度" in item.value for item in app.warning)
    assert not any(metric.label == "预估总分" for metric in app.metric)
