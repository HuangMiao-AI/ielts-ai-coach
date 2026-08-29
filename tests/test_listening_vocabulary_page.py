"""Streamlit flow contracts for Listening Vocabulary Lab."""

from __future__ import annotations

from pathlib import Path

import pytest
from sqlalchemy import func, select
from streamlit.navigation.page import calc_hash
from streamlit.testing.v1 import AppTest

from ielts_ai_coach.database.connection import get_session_factory, initialize_database
from ielts_ai_coach.database.models import (
    AIUsageDaily,
    Essay,
    LearnerProfileV2,
    PlanTask,
    ScoreRecord,
    StudentProfile,
    StudyPlan,
    TaskQuestionAttempt,
    User,
)
from ielts_ai_coach.services.listening_vocabulary import load_vocabulary_bank
from tests.ui_page_helpers import open_authenticated_page


PROJECT_ROOT = Path(__file__).resolve().parent.parent


def _button(app: AppTest, label: str):
    """Return one visible exact-label button."""

    return next(button for button in app.button if button.label == label)


def _open_guest_listening(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> AppTest:
    """Open Listening as a guest against an isolated database."""

    database_url = f"sqlite:///{(tmp_path / 'guest-listening.db').as_posix()}"
    monkeypatch.setenv("DATABASE_URL", database_url)
    monkeypatch.setenv("BACKUP_DIR", str(tmp_path / "backups"))
    initialize_database(database_url)
    app = AppTest.from_file("app.py").run(timeout=10)
    _button(app, "立即体验 · 游客模式\nTry as Guest").click().run(timeout=10)
    app._page_hash = calc_hash("listening")
    return app.run(timeout=10)


def test_listening_navigation_opens_vocabulary_lab_not_mini_practice(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """The normal Listening route exposes only the new low-friction entry."""

    app = open_authenticated_page(
        tmp_path, monkeypatch, route="listening", username="VocabularyRoute"
    )
    rendered = "\n".join(item.value for item in [*app.markdown, *app.caption])

    assert app.title[0].value == "Listening Vocabulary Lab"
    assert "听力词汇训练" in rendered
    assert "听发音 · 记单词 · 练拼写" in rendered
    assert {button.label for button in app.button} >= {"开始学习", "拼写挑战"}
    assert "Listening Mini Practice" not in rendered
    assert not any("开始 Mini Practice" in button.label for button in app.button)


def test_learning_ten_words_then_starts_same_spelling_group(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """The complete study-to-spelling handoff retains exactly the learned IDs."""

    app = open_authenticated_page(
        tmp_path, monkeypatch, route="listening", username="VocabularyStudy"
    )
    user_id = app.session_state["user_id"]
    _button(app, "开始学习").click().run(timeout=10)
    learning_key = f"listening_vocab_learning_{user_id}"
    learned_ids = app.session_state[learning_key].word_ids
    for _ in range(10):
        _button(app, "下一个").click().run(timeout=10)

    assert any("你刚刚学习了 10 个单词" in item.value for item in app.markdown)
    _button(app, "开始拼写测试").click().run(timeout=10)
    spelling = app.session_state[f"listening_vocab_spelling_{user_id}"]
    assert spelling.word_ids == learned_ids
    visible_markdown = "\n".join(item.value for item in app.markdown)
    current_word = load_vocabulary_bank().by_id[spelling.current_word_id].word
    assert f"**{current_word}**" not in visible_markdown
    assert "正确答案" not in visible_markdown


def test_spelling_feedback_locks_submit_and_final_summary_is_exact(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """One submission per question produces stable feedback and final metrics."""

    app = open_authenticated_page(
        tmp_path, monkeypatch, route="listening", username="VocabularySpell"
    )
    user_id = app.session_state["user_id"]
    _button(app, "拼写挑战").click().run(timeout=10)
    bank = load_vocabulary_bank()
    spelling_key = f"listening_vocab_spelling_{user_id}"
    for index in range(10):
        session = app.session_state[spelling_key]
        expected = bank.by_id[session.word_ids[session.current_index]].word
        answer = f" {expected.upper()} " if index < 8 else "wrong"
        next(item for item in app.text_input if item.label == "请输入你听到的单词").input(
            answer
        ).run(timeout=10)
        _button(app, "提交").click().run(timeout=10)
        assert not any(button.label == "提交" for button in app.button)
        _button(app, "下一题").click().run(timeout=10)

    metrics = {metric.label: metric.value for metric in app.metric}
    assert metrics["正确"] == "8 / 10"
    assert metrics["正确率"] == "80%"
    assert metrics["本局得分"] == "80 / 100"
    assert len(app.session_state[spelling_key].attempts) == 10
    assert len(app.session_state[spelling_key].wrong_word_ids) == 2


def test_wrong_word_review_and_replay_reset_without_database_writes(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Guest review and replay remain session-only and reset their round state."""

    app = _open_guest_listening(tmp_path, monkeypatch)
    guest_id = app.session_state["guest_session_id"]
    _button(app, "拼写挑战").click().run(timeout=10)
    spelling_key = f"listening_vocab_spelling_{guest_id}"
    for _ in range(10):
        next(item for item in app.text_input if item.label == "请输入你听到的单词").input(
            "wrong"
        ).run(timeout=10)
        _button(app, "提交").click().run(timeout=10)
        _button(app, "下一题").click().run(timeout=10)
    wrong_ids = app.session_state[spelling_key].wrong_word_ids

    _button(app, "重新学习这些词").click().run(timeout=10)
    assert app.session_state[f"listening_vocab_learning_{guest_id}"].word_ids == wrong_ids
    assert not app.exception

    app.session_state[f"listening_vocab_mode_{guest_id}"] = "summary"
    app.run(timeout=10)
    _button(app, "再来一局").click().run(timeout=10)
    replay = app.session_state[spelling_key]
    assert replay.attempts == ()
    assert replay.current_index == 0

    models = (
        User, StudentProfile, LearnerProfileV2, ScoreRecord, StudyPlan,
        PlanTask, TaskQuestionAttempt, Essay, AIUsageDaily,
    )
    with get_session_factory()() as session:
        assert all(session.scalar(select(func.count(model.id))) == 0 for model in models)


def test_vocabulary_lab_css_is_mobile_safe() -> None:
    """The new page keeps controls readable at 390px and wider breakpoints."""

    source = (
        PROJECT_ROOT / "ielts_ai_coach" / "ui" / "listening_vocabulary_styles.py"
    ).read_text(encoding="utf-8")
    global_css = (
        PROJECT_ROOT / "ielts_ai_coach" / "ui" / "design_system.py"
    ).read_text(encoding="utf-8")

    assert "min-height: 44px" in source
    assert "max-width: 100%" in source
    assert "@media (max-width: 430px)" in source
    assert "390" in source
    assert "768" in source
    assert "1440" in source
    assert "overflow-x: hidden" in global_css
