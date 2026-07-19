"""Explicit privacy rules for every export boundary."""

from __future__ import annotations

from collections.abc import Iterable

from ielts_ai_coach.exporting.errors import ExportPrivacyError


FORBIDDEN_FIELD_NAMES = frozenset(
    {
        "user_id",
        "username",
        "username_normalized",
        "nickname",
        "grade",
        "password",
        "password_hash",
        "token",
        "api_key",
        "secret",
        "answers_json",
        "user_answer",
        "essay_content",
        "content",
        "prompt",
        "raw_metadata",
        "last_error",
        "database_path",
        "database_url",
    }
)


def assert_safe_field_names(field_names: Iterable[str]) -> None:
    """Reject sensitive, raw, identity, and credential field names."""

    normalized = {name.strip().lower() for name in field_names}
    if normalized & FORBIDDEN_FIELD_NAMES:
        raise ExportPrivacyError("forbidden_export_field")
