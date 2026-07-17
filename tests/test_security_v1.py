"""Static and schema checks for V1 privacy and repository safety."""

from __future__ import annotations

import ast
import re
from pathlib import Path

from sqlalchemy import inspect
from sqlalchemy.orm import Session, sessionmaker

from ielts_ai_coach.auth import register_user
from ielts_ai_coach.database.models import (
    AIUsageDaily,
    CoachMessage,
    Essay,
    PlanTask,
    ScoreRecord,
    StudentProfile,
    StudyLog,
    StudyPlan,
    TaskQuestionAttempt,
    WritingFeedback,
)


PROJECT_ROOT = Path(__file__).resolve().parent.parent
BUSINESS_MODELS = (
    StudentProfile,
    ScoreRecord,
    StudyPlan,
    PlanTask,
    StudyLog,
    CoachMessage,
    AIUsageDaily,
    Essay,
    WritingFeedback,
    TaskQuestionAttempt,
)


def test_every_business_table_has_required_user_id(
    session_factory: sessionmaker[Session],
) -> None:
    """Every student-owned table must expose a non-null user ownership key."""

    inspector = inspect(session_factory.kw["bind"])
    for model in BUSINESS_MODELS:
        columns = {
            column["name"]: column
            for column in inspector.get_columns(model.__tablename__)
        }
        assert "user_id" in columns, model.__tablename__
        assert columns["user_id"]["nullable"] is False, model.__tablename__


def test_authenticated_session_never_contains_password(
    session_factory: sessionmaker[Session],
) -> None:
    """Registration must store only minimum identity fields in session state."""

    state: dict[str, object] = {}
    register_user(
        "SessionSafety",
        "secure-pass-01",
        state=state,
        session_factory=session_factory,
    )

    assert set(state) == {"authenticated", "user_id", "username"}
    assert "secure-pass-01" not in repr(state)


def test_active_source_never_imports_enterprise_archive() -> None:
    """The V1 runtime and tests must not import archived enterprise code."""

    active_files = [PROJECT_ROOT / "app.py"]
    active_files.extend((PROJECT_ROOT / "ielts_ai_coach").rglob("*.py"))
    active_files.extend((PROJECT_ROOT / "tests").rglob("*.py"))
    for source_file in active_files:
        tree = ast.parse(source_file.read_text(encoding="utf-8"))
        imported_modules = []
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                imported_modules.extend(alias.name for alias in node.names)
            elif isinstance(node, ast.ImportFrom) and node.module:
                imported_modules.append(node.module)
        assert not any(
            "archive" in module or "enterprise" in module
            for module in imported_modules
        ), source_file


def test_gitignore_covers_private_runtime_files() -> None:
    """Git exclusions must cover every approved secret and data category."""

    ignore_text = (PROJECT_ROOT / ".gitignore").read_text(encoding="utf-8")
    required_entries = {
        ".env",
        ".streamlit/secrets.toml",
        "data/*.db",
        "data/*.db-shm",
        "data/*.db-wal",
        "data/backups/",
        ".venv/",
        "__pycache__/",
        ".pytest_cache/",
        "/archive/enterprise-v0/",
        "*.log",
        "*.tmp",
    }

    assert required_entries <= set(ignore_text.splitlines())


def test_active_files_contain_no_key_like_literal() -> None:
    """Active project files must not contain a likely real API credential."""

    candidate_files = [PROJECT_ROOT / ".env.example"]
    candidate_files.extend((PROJECT_ROOT / "ielts_ai_coach").rglob("*.py"))
    key_pattern = re.compile(
        r"(?i)(?:sk-|dashscope[-_])[A-Za-z0-9_-]{16,}"
    )

    for candidate in candidate_files:
        assert not key_pattern.search(
            candidate.read_text(encoding="utf-8")
        ), candidate
