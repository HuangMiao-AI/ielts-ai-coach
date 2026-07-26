"""Regression contracts for durable local authentication."""

from __future__ import annotations

from pathlib import Path

import pytest
from sqlalchemy.orm import Session, sessionmaker

from ielts_ai_coach.auth import (
    AccountNotFoundError,
    IncorrectPasswordError,
    get_current_user,
    login_user,
    logout,
    register_user,
)
from ielts_ai_coach.config import BASE_DIR, DEFAULT_DATABASE_URL, get_database_url
from ielts_ai_coach.database.connection import create_database_engine
from ielts_ai_coach.database.models import Base
from ielts_ai_coach.services.learner_profiles import get_learner_profile


def test_relative_sqlite_url_is_anchored_to_project_base(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """A launch directory must not select a second local account database."""

    first_cwd = tmp_path / "first-launch-directory"
    second_cwd = tmp_path / "second-launch-directory"
    first_cwd.mkdir()
    second_cwd.mkdir()
    monkeypatch.setenv("DATABASE_URL", "sqlite:///data/persistent.db")
    monkeypatch.chdir(first_cwd)
    first_url = get_database_url()
    monkeypatch.chdir(second_cwd)
    second_url = get_database_url()

    assert first_url == second_url == (
        f"sqlite:///{(BASE_DIR / 'data' / 'persistent.db').as_posix()}"
    )


def test_default_database_url_remains_the_project_absolute_location(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """No configured URL must continue to select the canonical V1 database."""

    monkeypatch.delenv("DATABASE_URL", raising=False)

    assert get_database_url() == DEFAULT_DATABASE_URL


def test_trimmed_casefolded_login_survives_a_new_session_factory(
    test_database_url: str,
) -> None:
    """A real account remains available after logout and a fresh connection."""

    first_engine = create_database_engine(test_database_url)
    Base.metadata.create_all(first_engine)
    first_factory = sessionmaker(
        bind=first_engine,
        class_=Session,
        expire_on_commit=False,
    )
    registered = register_user(
        "Persistent_Student",
        "secure-pass-01",
        state={},
        session_factory=first_factory,
    )
    first_engine.dispose()

    second_engine = create_database_engine(test_database_url)
    second_factory = sessionmaker(
        bind=second_engine,
        class_=Session,
        expire_on_commit=False,
    )
    new_state: dict[str, object] = {}
    logged_in = login_user(
        "  persistent_student  ",
        "secure-pass-01",
        state=new_state,
        session_factory=second_factory,
    )

    assert logged_in.id == registered.id
    assert get_current_user(
        state=new_state,
        session_factory=second_factory,
    ).id == registered.id
    logout(state=new_state)
    assert new_state == {}
    second_engine.dispose()


def test_account_absence_and_wrong_password_are_distinct(
    session_factory: sessionmaker[Session],
) -> None:
    """The login page can guide the two recoverable errors honestly."""

    register_user(
        "KnownStudent",
        "secure-pass-01",
        state={},
        session_factory=session_factory,
    )

    with pytest.raises(AccountNotFoundError):
        login_user(
            "UnknownStudent",
            "secure-pass-01",
            state={},
            session_factory=session_factory,
        )
    with pytest.raises(IncorrectPasswordError):
        login_user(
            "knownstudent",
            "wrong-password",
            state={},
            session_factory=session_factory,
        )


def test_missing_profile_is_not_treated_as_a_missing_account(
    session_factory: sessionmaker[Session],
) -> None:
    """An authenticated account without a profile must be routed to onboarding."""

    account = register_user(
        "NeedsProfile",
        "secure-pass-01",
        state={},
        session_factory=session_factory,
    )
    state: dict[str, object] = {}

    logged_in = login_user(
        "needsprofile",
        "secure-pass-01",
        state=state,
        session_factory=session_factory,
    )

    assert logged_in.id == account.id
    assert state["authenticated"] is True
    assert get_learner_profile(
        account.id,
        session_factory=session_factory,
    ) is None
