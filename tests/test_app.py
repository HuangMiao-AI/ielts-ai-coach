"""End-to-end smoke test for the Streamlit authentication flow."""

from __future__ import annotations

from pathlib import Path

import pytest
from streamlit.navigation.page import calc_hash
from streamlit.testing.v1 import AppTest


def test_student_can_register_open_profile_and_logout(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """A new student should be guided to a profile and be able to log out."""

    database_url = f"sqlite:///{(tmp_path / 'app.db').as_posix()}"
    monkeypatch.setenv("DATABASE_URL", database_url)
    monkeypatch.setenv("BACKUP_DIR", str(tmp_path / "backups"))

    app = AppTest.from_file("app.py").run()
    assert not app.exception
    assert [button.label for button in app.button] == [
        "立即体验 · 游客模式\nTry as Guest",
        "登录",
        "创建账号",
    ]

    app.text_input[2].input("DemoStudent")
    app.text_input[3].input("secure-pass-01")
    app.text_input[4].input("secure-pass-01")
    app.button[2].click().run()

    assert not app.exception
    assert app.title[0].value == "开始设置学习档案"
    assert any("步骤 1/4" in item.value for item in app.caption)
    user_id = app.session_state["user_id"]
    app = AppTest.from_file("app.py")
    app.session_state["authenticated"] = True
    app.session_state["user_id"] = user_id
    app.session_state["username"] = "DemoStudent"
    app._page_hash = calc_hash("settings")
    app.run()
    logout_button = next(
        button for button in app.button if button.label == "退出登录"
    )
    logout_button.click().run()
    assert not app.exception
    button_labels = [button.label for button in app.button]
    assert "登录" in button_labels
    assert "创建账号" in button_labels
    assert any(item.label == "用户名" for item in app.text_input)
    assert app.session_state.filtered_state.get("authenticated") is not True
