"""Guest access, session score, and Academic Task 1 visual contracts."""

from __future__ import annotations

from pathlib import Path

import pytest
from sqlalchemy import func, select
from streamlit.navigation.page import calc_hash
from streamlit.testing.v1 import AppTest

from ielts_ai_coach.auth import (
    get_guest_identity,
    start_guest_session,
)
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
from ielts_ai_coach.services.training_arena import (
    ArenaRound,
    arena_round_key,
    arena_session_score_key,
    arena_session_score,
    record_completed_round_score,
    load_training_arena_bank,
)
from tests.ui_page_helpers import open_authenticated_page
from ielts_ai_coach.services.writing_tasks import (
    list_writing_tasks,
    load_writing_tasks,
)


PROJECT_ROOT = Path(__file__).resolve().parent.parent
EXPECTED_VISUAL_TYPES = {
    "line_graph",
    "bar_chart",
    "pie_chart",
    "table",
    "process_diagram",
    "map",
}


def _configure_app(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    database_url = f"sqlite:///{(tmp_path / 'guest.db').as_posix()}"
    monkeypatch.setenv("DATABASE_URL", database_url)
    monkeypatch.setenv("BACKUP_DIR", str(tmp_path / "backups"))
    monkeypatch.delenv("QWEN_API_KEY", raising=False)
    monkeypatch.delenv("DASHSCOPE_API_KEY", raising=False)
    initialize_database(database_url)


def test_guest_identity_is_session_only_and_not_authenticated() -> None:
    state: dict[str, object] = {
        "authenticated": True,
        "user_id": 4,
        "username": "old-user",
    }

    guest = start_guest_session(state)

    assert guest.id > 0
    assert guest.username == "游客"
    assert state.get("authenticated") is not True
    assert get_guest_identity(state) == guest


def test_public_page_offers_one_click_guest_access_without_creating_user(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _configure_app(tmp_path, monkeypatch)

    app = AppTest.from_file("app.py").run(timeout=10)
    guest_button = next(
        button for button in app.button
        if button.label == "立即体验 · 游客模式\nTry as Guest"
    )
    guest_button.click().run(timeout=10)

    assert not app.exception
    assert app.title[0].value == "IELTS AI Coach"
    assert any("游客模式 · 登录后可保存学习记录" in item.value for item in app.markdown)
    assert any(button.label == "登录 / 注册" for button in app.button)
    factory = get_session_factory()
    with factory() as session:
        assert session.scalar(select(func.count(User.id))) == 0


def test_guest_can_open_every_approved_route_without_database_records(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _configure_app(tmp_path, monkeypatch)
    app = AppTest.from_file("app.py").run(timeout=10)
    next(
        button for button in app.button
        if button.label == "立即体验 · 游客模式\nTry as Guest"
    ).click().run(timeout=10)

    expected_titles = {
        "home": "IELTS AI Coach",
        "arena": "IELTS 训练场",
        "reading": "阅读练习",
        "listening": "听力练习",
        "writing": "写作练习",
    }
    for route, title in expected_titles.items():
        app._page_hash = calc_hash(route)
        app.run(timeout=10)
        assert not app.exception
        assert app.title[0].value == title

    factory = get_session_factory()
    models = (
        User,
        StudentProfile,
        LearnerProfileV2,
        ScoreRecord,
        StudyPlan,
        PlanTask,
        TaskQuestionAttempt,
        Essay,
        AIUsageDaily,
    )
    with factory() as session:
        assert all(
            session.scalar(select(func.count(model.id))) == 0
            for model in models
        )


def test_logged_home_score_chip_uses_verified_current_session_score(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    app = open_authenticated_page(
        tmp_path,
        monkeypatch,
        route="home",
        username="ScoreChipUser",
    )
    user_id = app.session_state["user_id"]
    app.session_state[arena_session_score_key(user_id)] = 30
    app.run(timeout=10)

    rendered = "\n".join(item.value for item in app.markdown)
    assert "本次积分" in rendered
    assert ">30<" in rendered


def test_guest_writing_draft_and_visual_survive_page_navigation(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _configure_app(tmp_path, monkeypatch)
    app = AppTest.from_file("app.py").run(timeout=10)
    next(
        button for button in app.button
        if button.label == "立即体验 · 游客模式\nTry as Guest"
    ).click().run(timeout=10)
    app._page_hash = calc_hash("writing")
    app.run(timeout=10)
    visual = next(item for item in app.selectbox if item.label == "视觉题目")
    visual.select("WRITE-V1-A1-MAP").run(timeout=10)
    content = next(item for item in app.text_area if item.label == "作文正文")
    content.input("Riverside Park retained its pond while adding new facilities.").run(
        timeout=10
    )

    app._page_hash = calc_hash("listening")
    app.run(timeout=10)
    app._page_hash = calc_hash("writing")
    app.run(timeout=10)

    restored_visual = next(item for item in app.selectbox if item.label == "视觉题目")
    restored_content = next(item for item in app.text_area if item.label == "作文正文")
    assert restored_visual.value == "WRITE-V1-A1-MAP"
    assert "Riverside Park retained" in restored_content.value


def test_guest_completes_writing_without_creating_essay(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _configure_app(tmp_path, monkeypatch)
    app = AppTest.from_file("app.py").run(timeout=10)
    next(
        button for button in app.button
        if button.label == "立即体验 · 游客模式\nTry as Guest"
    ).click().run(timeout=10)
    app._page_hash = calc_hash("writing")
    app.run(timeout=10)
    content = next(item for item in app.text_area if item.label == "作文正文")
    content.input("The chart rises steadily over the period shown.").run(timeout=10)
    next(
        button for button in app.button if button.label == "完成本次练习"
    ).click().run(timeout=10)
    next(button for button in app.button if button.label == "确认完成").click().run(
        timeout=10
    )

    assert any("结果仅保存在当前会话" in item.value for item in app.success)
    with get_session_factory()() as session:
        assert session.scalar(select(func.count(Essay.id))) == 0


def test_academic_task_one_visuals_keep_drafts_and_results_isolated(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _configure_app(tmp_path, monkeypatch)
    app = AppTest.from_file("app.py").run(timeout=10)
    next(
        button for button in app.button
        if button.label == "立即体验 · 游客模式\nTry as Guest"
    ).click().run(timeout=10)
    app._page_hash = calc_hash("writing")
    app.run(timeout=10)
    next(item for item in app.text_area if item.label == "作文正文").input(
        "The renewable energy line graph rises over time."
    ).run(timeout=10)

    next(item for item in app.selectbox if item.label == "视觉题目").select(
        "WRITE-V1-A1-MAP"
    ).run(timeout=10)
    map_content = next(item for item in app.text_area if item.label == "作文正文")
    assert map_content.value == ""
    map_content.input("Riverside Park added facilities around the retained pond.").run(
        timeout=10
    )
    next(
        button for button in app.button if button.label == "完成本次练习"
    ).click().run(timeout=10)
    next(button for button in app.button if button.label == "确认完成").click().run(
        timeout=10
    )
    assert any("本次写作已完成" in item.value for item in app.success)

    next(item for item in app.selectbox if item.label == "视觉题目").select(
        "WRITE-V1-A1-LINE"
    ).run(timeout=10)
    line_content = next(item for item in app.text_area if item.label == "作文正文")
    assert "renewable energy line graph" in line_content.value
    assert not any("本次写作已完成" in item.value for item in app.success)


def test_completed_arena_round_is_added_to_session_score_once() -> None:
    store: dict[str, object] = {}
    round_state = ArenaRound(
        question_ids=("a", "b", "c", "d", "e"),
        answers=("1", "2", "3", "4", "5"),
        correct_count=4,
        completed=True,
    )

    recorded = record_completed_round_score(store, 91, round_state)
    recorded_again = record_completed_round_score(store, 91, recorded)

    assert recorded.score_recorded is True
    assert recorded_again == recorded
    assert arena_session_score(store, 91) == 40
    assert arena_session_score(store, 92) == 0


def test_guest_can_complete_arena_and_receive_current_session_score(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _configure_app(tmp_path, monkeypatch)
    app = AppTest.from_file("app.py").run(timeout=10)
    next(
        button for button in app.button
        if button.label == "立即体验 · 游客模式\nTry as Guest"
    ).click().run(timeout=10)
    app._page_hash = calc_hash("arena")
    app.run(timeout=10)
    guest_id = app.session_state["guest_session_id"]
    bank = load_training_arena_bank()

    for index in range(5):
        round_state = app.session_state[arena_round_key(guest_id)]
        question = bank.by_id[round_state.question_ids[round_state.current_index]]
        next(
            button for button in app.button
            if button.label == question.correct_answer
        ).click().run(timeout=10)
        advance_label = "查看本局战绩" if index == 4 else "下一题"
        next(
            button for button in app.button if button.label == advance_label
        ).click().run(timeout=10)

    assert not app.exception
    assert any(item.value == "本局战绩" for item in app.subheader)
    assert app.session_state[arena_session_score_key(guest_id)] == 50
    with get_session_factory()() as session:
        assert session.scalar(select(func.count(User.id))) == 0


def test_academic_task_one_has_six_original_local_visuals() -> None:
    bank = load_writing_tasks()
    tasks = list_writing_tasks("Academic", "Task 1")

    assert bank.source_type == "project_original"
    assert len(tasks) == 6
    assert {task.visual_type for task in tasks} == EXPECTED_VISUAL_TYPES
    for task in tasks:
        assert task.visual_asset is not None
        asset = PROJECT_ROOT / task.visual_asset
        assert asset.is_file()
        assert asset.suffix == ".svg"
        source = asset.read_text(encoding="utf-8")
        assert "viewBox=" in source
        assert "width=\"100%\"" in source
        assert task.visual_alt
        assert task.prompt


def test_task_two_remains_non_visual() -> None:
    task = list_writing_tasks("Academic", "Task 2")[0]

    assert task.visual_type is None
    assert task.visual_asset is None


def test_visual_css_is_responsive_without_horizontal_overflow() -> None:
    writing_source = (
        PROJECT_ROOT / "ielts_ai_coach" / "views" / "writing.py"
    ).read_text(encoding="utf-8")
    writing_source += (
        PROJECT_ROOT
        / "ielts_ai_coach"
        / "views"
        / "writing_task_presentation.py"
    ).read_text(encoding="utf-8")
    css_source = (
        PROJECT_ROOT / "ielts_ai_coach" / "ui" / "guest_writing_styles.py"
    ).read_text(encoding="utf-8")
    css_source += (
        PROJECT_ROOT / "ielts_ai_coach" / "ui" / "design_system.py"
    ).read_text(encoding="utf-8")

    assert "视觉材料" in writing_source
    assert "题目说明" in writing_source
    assert "写作输入区" in writing_source
    assert ".writing-task-visual" in css_source
    assert "max-width: 100%" in css_source
    assert "overflow-x: hidden" in css_source
