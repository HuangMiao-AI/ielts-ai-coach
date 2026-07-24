"""Authenticated Home behavior for the IELTS Growth Dashboard."""

from __future__ import annotations

import ast
from datetime import date, datetime, timedelta
from pathlib import Path

import pytest
from streamlit.navigation.page import calc_hash
from streamlit.testing.v1 import AppTest

from ielts_ai_coach.database.connection import (
    get_session_factory,
    initialize_database,
)
from tests.analytics.helpers import (
    add_profile,
    add_reading_attempt,
    add_score,
    add_study_log,
    add_writing_feedback,
    create_user,
    reading_snapshot,
)


PROJECT_ROOT = Path(__file__).resolve().parents[2]


def _configure_app(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> object:
    """Use one temporary database and blank every supported AI key."""

    database_url = f"sqlite:///{(tmp_path / 'growth-dashboard.db').as_posix()}"
    monkeypatch.setenv("DATABASE_URL", database_url)
    monkeypatch.setenv("BACKUP_DIR", str(tmp_path / "backups"))
    monkeypatch.delenv("QWEN_API_KEY", raising=False)
    monkeypatch.delenv("DASHSCOPE_API_KEY", raising=False)
    initialize_database(database_url)
    return get_session_factory(database_url)


def _open_home(user_id: int, username: str) -> AppTest:
    """Render Home for one authenticated fictional account."""

    app = AppTest.from_file("app.py")
    app.session_state["authenticated"] = True
    app.session_state["user_id"] = user_id
    app.session_state["username"] = username
    app._page_hash = calc_hash("home")
    return app.run(timeout=10)


def _rendered_text(app: AppTest) -> str:
    """Collect Streamlit text-bearing elements for ownership assertions."""

    values: list[str] = []
    for element_name in (
        "title",
        "header",
        "subheader",
        "markdown",
        "caption",
        "info",
        "warning",
        "success",
        "text",
    ):
        values.extend(
            str(element.value) for element in getattr(app, element_name)
        )
    for metric in app.metric:
        values.extend((str(metric.label), str(metric.value)))
    return "\n".join(values)


def _seed_populated_users(session_factory: object) -> tuple[int, int]:
    """Create one visible owner and one intentionally distinctive other user."""

    owner_id = create_user("GrowthOwner", session_factory)
    other_id = create_user("GrowthOther", session_factory)
    today = date.today()
    with session_factory.begin() as session:
        add_profile(
            session,
            user_id=owner_id,
            target_overall=7.0,
            daily_study_minutes=60,
        )
        add_score(
            session,
            user_id=owner_id,
            overall=5.5,
            listening=6.0,
            reading=5.0,
            writing=5.0,
            speaking=5.5,
            recorded_at=datetime.combine(
                today - timedelta(days=30), datetime.min.time()
            ),
        )
        add_score(
            session,
            user_id=owner_id,
            overall=6.0,
            listening=6.5,
            reading=5.5,
            writing=5.5,
            speaking=6.0,
            recorded_at=datetime.combine(today, datetime.min.time()),
        )
        add_reading_attempt(
            session,
            user_id=owner_id,
            score=4,
            total_questions=10,
            results_json=reading_snapshot(
                [
                    *(("multiple_choice", False),) * 6,
                    *(("multiple_choice", True),) * 4,
                ]
            ),
            submitted_at=datetime.combine(today, datetime.min.time()),
        )
        add_writing_feedback(
            session,
            user_id=owner_id,
            task_response=5.5,
            coherence=5.0,
            vocabulary=5.5,
            grammar=5.0,
            created_at=datetime.combine(
                today - timedelta(days=30), datetime.min.time()
            ),
        )
        add_writing_feedback(
            session,
            user_id=owner_id,
            task_response=6.5,
            coherence=6.5,
            vocabulary=6.5,
            grammar=5.5,
            created_at=datetime.combine(today, datetime.min.time()),
        )
        add_study_log(
            session,
            user_id=owner_id,
            study_date=today - timedelta(days=1),
            minutes=30,
        )
        add_study_log(
            session,
            user_id=owner_id,
            study_date=today,
            minutes=35,
        )

        add_profile(
            session,
            user_id=other_id,
            target_overall=8.5,
            daily_study_minutes=120,
        )
        add_score(
            session,
            user_id=other_id,
            overall=8.5,
            listening=8.5,
            reading=8.5,
            writing=8.5,
            speaking=8.5,
            recorded_at=datetime.combine(today, datetime.min.time()),
        )
        add_reading_attempt(
            session,
            user_id=other_id,
            score=1,
            total_questions=4,
            results_json=reading_snapshot(
                [
                    *(("matching_heading", False),) * 3,
                    ("matching_heading", True),
                ]
            ),
            submitted_at=datetime.combine(today, datetime.min.time()),
        )
    return owner_id, other_id


def test_populated_authenticated_home_renders_owner_growth_dashboard(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Home renders evidence-backed owner analytics and preserves old content."""

    factory = _configure_app(tmp_path, monkeypatch)
    owner_id, _ = _seed_populated_users(factory)

    app = _open_home(owner_id, "GrowthOwner")

    rendered = _rendered_text(app)
    metric_labels = [metric.label for metric in app.metric]
    page_labels = [link.proto.label for link in app.get("page_link")]
    assert not app.exception
    assert "IELTS Growth Dashboard" in rendered
    assert {"Current Band", "Target Band", "Progress", "Learning Streak"} <= set(
        metric_labels
    )
    assert "当前差距" in metric_labels
    assert "1.0 分" in rendered
    assert "四科最新成绩与趋势" in rendered
    assert "听力：6.5" in rendered
    assert "趋势：6.0 → 6.5" in rendered
    assert "阅读：5.5" in rendered
    assert "趋势：5.0 → 5.5" in rendered
    assert "写作：5.5" in rendered
    assert "趋势：5.0 → 5.5" in rendered
    assert "口语：6.0" in rendered
    assert "趋势：5.5 → 6.0" in rendered
    assert rendered.count("No detailed practice analytics available") >= 2
    assert "Reading 细粒度表现" in rendered
    assert "已提交练习：1 次" in rendered
    assert "正确题数：4/10" in rendered
    assert "正确率：40%" in rendered
    assert "高频错误：Multiple Choice" in rendered
    assert "Writing 四项分析" in rendered
    assert "Task Achievement：6.5" in rendered
    assert "Coherence：6.5" in rendered
    assert "Vocabulary：6.5" in rendered
    assert "Grammar：5.5" in rendered
    assert "Weakness Cards" in rendered
    assert "科目：阅读" in rendered
    assert "弱项：阅读 Multiple Choice 正确率需要提高" in rendered
    assert "严重程度：高" in rendered
    assert 'data-severity="high"' in rendered
    assert "证据：已提交 Reading：4/10 正确（40%）" in rendered
    assert "建议：练习 Multiple Choice 题型并复盘错误模式。" in rendered
    assert "证据：Task Achievement：6.5；目标：7.0；差距：0.5。" in rendered
    assert "accuracy needs improvement" not in rendered
    assert "Submitted Reading:" not in rendered
    assert "Practise Multiple Choice question types" not in rendered
    assert "task_achievement band" not in rendered
    assert "Recommended Next Actions" in rendered
    assert "第 1 天" in rendered
    assert "第 2 天" in rendered
    assert "第 3 天" in rendered
    assert "完成 1 组原创 Reading Multiple Choice" in rendered
    assert "36 分钟" in rendered
    assert "未来 7 天建议摘要" in rendered
    assert "第 4 天" in rendered
    assert "第 5 天" in rendered
    assert "第 6 天" in rendered
    assert "第 7 天" in rendered
    assert "Mock AI Explanation" in rendered
    assert "以上分析仅用于学习规划，不是官方IELTS评分或诊断。" in rendered

    assert "8.5" not in rendered
    assert "阅读 Matching Heading 正确率需要提高" not in rendered
    assert "完成 1 组原创 Reading Matching Heading" not in rendered

    assert {"阅读", "听力", "写作", "口语"} <= set(page_labels)
    assert {"连续学习", "今日完成", "最近阅读", "最近写作"} <= set(
        metric_labels
    )
    for existing_section in (
        "推荐下一步",
        "计划预览",
        "近期活动",
        "今日学习进度",
        "当前目标",
        "今日任务",
        "最新成绩",
        "本周学习统计",
        "AI剩余额度",
    ):
        assert existing_section in rendered


def test_empty_authenticated_home_is_factual_and_has_no_weakness_card(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """An empty owner sees exact no-data statuses without fabricated weakness."""

    factory = _configure_app(tmp_path, monkeypatch)
    user_id = create_user("GrowthEmpty", factory)

    app = _open_home(user_id, "GrowthEmpty")

    rendered = _rendered_text(app)
    metric_values = {metric.label: metric.value for metric in app.metric}
    assert not app.exception
    assert "Current Band" in metric_values
    assert "Target Band" in metric_values
    assert "Progress" in metric_values
    assert "Learning Streak" in metric_values
    assert metric_values["Current Band"] == "暂无"
    assert metric_values["Target Band"] == "暂无"
    assert metric_values["Progress"] == "暂无"
    assert metric_values["Learning Streak"] == "0 天"
    assert metric_values["当前差距"] == "暂无"
    assert "四科最新成绩与趋势" in rendered
    assert "Reading 细粒度表现" in rendered
    assert "暂无已提交的 Reading 练习数据。" in rendered
    assert "Writing 四项分析" in rendered
    assert "暂无已完成的 Writing 反馈数据。" in rendered
    assert "No enough listening data" in rendered
    assert "No enough speaking data" in rendered
    assert "暂无基于已提交阅读或写作数据识别的弱项。" in rendered
    assert "严重程度：" not in rendered
    assert "data-severity=" not in rendered


def test_dashboard_uses_only_authenticated_user_and_default_mock_boundary() -> None:
    """Home passes user.id only and explanation omits provider selection."""

    dashboard_path = PROJECT_ROOT / "ielts_ai_coach" / "views" / "dashboard.py"
    growth_path = (
        PROJECT_ROOT / "ielts_ai_coach" / "views" / "growth_dashboard.py"
    )
    dashboard_source = dashboard_path.read_text(encoding="utf-8")
    assert growth_path.exists()
    growth_source = growth_path.read_text(encoding="utf-8")
    dashboard_tree = ast.parse(dashboard_source)
    growth_tree = ast.parse(growth_source)

    dashboard_calls = [
        node
        for node in ast.walk(dashboard_tree)
        if isinstance(node, ast.Call)
        and isinstance(node.func, ast.Name)
        and node.func.id == "render_growth_dashboard"
    ]
    explanation_calls = [
        node
        for node in ast.walk(growth_tree)
        if isinstance(node, ast.Call)
        and isinstance(node.func, ast.Name)
        and node.func.id == "explain_analytics"
    ]

    assert len(dashboard_calls) == 1
    assert ast.unparse(dashboard_calls[0]) == "render_growth_dashboard(user.id)"
    assert len(explanation_calls) == 1
    assert len(explanation_calls[0].args) == 3
    assert explanation_calls[0].keywords == []
    assert "get_ai_provider" not in growth_source
    assert "number_input" not in dashboard_source
    assert "text_input" not in dashboard_source
    assert "user_id=" not in dashboard_source
