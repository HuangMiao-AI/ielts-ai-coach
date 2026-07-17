"""Streamlit dashboard tests for empty and populated student data."""

from __future__ import annotations

from datetime import date, timedelta
from pathlib import Path

import pytest
from streamlit.navigation.page import calc_hash
from streamlit.testing.v1 import AppTest

from ielts_ai_coach.auth import register_user
from ielts_ai_coach.database.connection import initialize_database
from ielts_ai_coach.services.planning import generate_plan
from ielts_ai_coach.services.profiles import save_profile
from ielts_ai_coach.services.scores import save_score_record


def _configure_test_app(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> str:
    """Point the application at an isolated database and backup directory."""

    database_url = f"sqlite:///{(tmp_path / 'dashboard.db').as_posix()}"
    monkeypatch.setenv("DATABASE_URL", database_url)
    monkeypatch.setenv("BACKUP_DIR", str(tmp_path / "backups"))
    monkeypatch.delenv("QWEN_API_KEY", raising=False)
    initialize_database(database_url)
    return database_url


def test_dashboard_guides_user_with_empty_data(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """An account without profile data must render guidance, not an error."""

    _configure_test_app(tmp_path, monkeypatch)
    app = AppTest.from_file("app.py").run(timeout=10)
    app.text_input[2].input("EmptyDashboard")
    app.text_input[3].input("secure-pass-01")
    app.text_input[4].input("secure-pass-01")
    app.button[1].click().run(timeout=10)
    user_id = app.session_state["user_id"]
    app = AppTest.from_file("app.py")
    app.session_state["authenticated"] = True
    app.session_state["user_id"] = user_id
    app.session_state["username"] = "EmptyDashboard"
    app._page_hash = calc_hash("home")
    app.run(timeout=10)

    assert not app.exception
    assert app.title[0].value == "你好，EmptyDashboard"
    assert app.info


def test_dashboard_renders_complete_student_metrics(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """A prepared student must see scores, tasks, progress, and AI quota."""

    database_url = _configure_test_app(tmp_path, monkeypatch)
    from ielts_ai_coach.database.connection import get_session_factory

    factory = get_session_factory(database_url)
    today = date.today()
    user_id = register_user(
        "FullDashboard",
        "secure-pass-01",
        state={},
        session_factory=factory,
    ).id
    save_profile(
        user_id=user_id,
        nickname="小航",
        grade="高二",
        target_overall=7.0,
        exam_date=today + timedelta(days=60),
        daily_study_minutes=90,
        today=today,
        session_factory=factory,
    )
    save_score_record(
        user_id=user_id,
        scores={
            "listening": 6.5,
            "reading": 6.0,
            "writing": 5.5,
            "speaking": 6.0,
        },
        session_factory=factory,
    )
    generate_plan(user_id, today=today, session_factory=factory)

    app = AppTest.from_file("app.py").run(timeout=10)
    app.text_input[0].input("FullDashboard")
    app.text_input[1].input("secure-pass-01")
    app.button[0].click().run(timeout=10)

    metric_labels = [metric.label for metric in app.metric]
    assert not app.exception
    assert app.title[0].value == "你好，小航"
    assert "目标IELTS分数" in metric_labels
    assert "最新总分" in metric_labels
    assert "本周任务完成率" in metric_labels
    assert "AI教练剩余" in metric_labels
