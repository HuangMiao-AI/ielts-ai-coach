"""End-to-end Streamlit flow across the complete local V1."""

from __future__ import annotations

from datetime import date, timedelta
from pathlib import Path

import pytest
from streamlit.navigation.page import calc_hash
from streamlit.testing.v1 import AppTest


def _button(app: AppTest, label: str):
    """Return the first visible button with an exact label."""

    return next(button for button in app.button if button.label == label)


def _text_input(app: AppTest, label: str):
    """Return the first visible text input with an exact label."""

    return next(item for item in app.text_input if item.label == label)


def _text_area(app: AppTest, label: str):
    """Return the first visible text area with an exact label."""

    return next(item for item in app.text_area if item.label == label)


def _selectbox(app: AppTest, label: str):
    """Return the first visible select box with an exact label."""

    return next(item for item in app.selectbox if item.label == label)


def _open_page(app: AppTest, url_path: str) -> AppTest:
    """Open a callable Streamlit page by its registered URL path."""

    app._page_hash = calc_hash(url_path)
    return app.run(timeout=10)


def test_complete_student_flow_runs_in_mock_mode(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """A student can complete the approved V1 loop without a real AI key."""

    database_url = f"sqlite:///{(tmp_path / 'flow.db').as_posix()}"
    monkeypatch.setenv("DATABASE_URL", database_url)
    monkeypatch.setenv("BACKUP_DIR", str(tmp_path / "backups"))
    monkeypatch.delenv("QWEN_API_KEY", raising=False)
    monkeypatch.delenv("DASHSCOPE_API_KEY", raising=False)

    app = AppTest.from_file("app.py").run(timeout=10)
    app.text_input[2].input("FlowStudent")
    app.text_input[3].input("secure-pass-01")
    app.text_input[4].input("secure-pass-01")
    app.button[1].click().run(timeout=10)
    user_id = app.session_state["user_id"]
    app = AppTest.from_file("app.py")
    app.session_state["authenticated"] = True
    app.session_state["user_id"] = user_id
    app.session_state["username"] = "FlowStudent"
    app.run(timeout=10)

    _text_input(app, "姓名或昵称").input("")
    _selectbox(app, "当前年级或阶段").select("高二")
    _button(app, "下一步").click().run(timeout=10)
    assert any("昵称长度" in item.value for item in app.error)

    _text_input(app, "姓名或昵称").input("小流")
    _button(app, "下一步").click().run(timeout=10)
    _button(app, "下一步").click().run(timeout=10)
    app.slider[0].set_value(90)
    _button(app, "下一步").click().run(timeout=10)
    _button(app, "保存并进入首页").click().run(timeout=10)
    assert any("资料已保存" in item.value for item in app.success)

    _open_page(app, "scores")
    _selectbox(app, "听力").select(6.5)
    _selectbox(app, "阅读").select(6.0)
    _selectbox(app, "写作").select(5.5)
    _selectbox(app, "口语").select(5.5)
    _button(app, "保存并诊断").click().run(timeout=10)
    assert any(metric.label == "当前总分" for metric in app.metric)

    _open_page(app, "plan")
    _button(app, "生成七天计划").click().run(timeout=10)
    assert any(metric.label == "任务数量" for metric in app.metric)

    _open_page(app, "today")
    complete_buttons = [
        button for button in app.button if button.label == "标记完成"
    ]
    assert complete_buttons
    complete_buttons[0].click().run(timeout=10)
    assert app.success

    _open_page(app, "coach")
    assert any("演示模式" in item.value for item in app.info)
    app.chat_input[0].set_value("如何提高写作？").run(timeout=10)
    assert any("学习参考" in item.value for item in app.markdown)

    _open_page(app, "writing")
    _text_area(app, "作文题目").input(
        "Some people think schools should teach practical skills. Discuss."
    )
    _text_area(app, "作文正文").input(
        "Schools should teach practical skills because students need them in "
        "daily life. Practical lessons can also help learners connect theory "
        "with real experience and become more independent."
    )
    _button(app, "提交AI批改").click().run(timeout=10)
    assert any("提交后将占用一次成功额度" in item.value for item in app.warning)
    _button(app, "确认提交AI批改").click().run(timeout=10)

    assert not app.exception
    assert any(metric.label == "预估总分" for metric in app.metric)
    assert any("AI预估" in item.value for item in app.error)
