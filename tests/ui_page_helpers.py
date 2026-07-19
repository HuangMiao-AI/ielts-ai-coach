"""Shared isolated Streamlit page setup for behavioral UI tests."""

from __future__ import annotations

from pathlib import Path

import pytest
from streamlit.navigation.page import calc_hash
from streamlit.testing.v1 import AppTest

from ielts_ai_coach.auth import register_user
from ielts_ai_coach.database.connection import initialize_database


def open_authenticated_page(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    *,
    route: str,
    username: str,
) -> AppTest:
    """Open one route with an isolated local user and forced Mock mode."""

    database_url = f"sqlite:///{(tmp_path / f'{route}.db').as_posix()}"
    monkeypatch.setenv("DATABASE_URL", database_url)
    monkeypatch.setenv("BACKUP_DIR", str(tmp_path / "backups"))
    monkeypatch.delenv("QWEN_API_KEY", raising=False)
    monkeypatch.delenv("DASHSCOPE_API_KEY", raising=False)
    initialize_database(database_url)
    user_id = register_user(
        username,
        "secure-pass-01",
        state={},
    ).id
    app = AppTest.from_file("app.py")
    app.session_state["authenticated"] = True
    app.session_state["user_id"] = user_id
    app.session_state["username"] = username
    app.run(timeout=10)
    app._page_hash = calc_hash(route)
    return app.run(timeout=10)
