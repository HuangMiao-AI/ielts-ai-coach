"""Stable enum values shared by exporter contracts and adapters."""

from __future__ import annotations

from enum import IntEnum, StrEnum


class SourceEntity(StrEnum):
    """Database entity that owns a stable source primary key."""

    TASK_QUESTION_ATTEMPT = "task_question_attempt"
    WRITING_FEEDBACK = "writing_feedback"


class Skill(StrEnum):
    """IELTS skills supported by exporter V1."""

    READING = "reading"
    WRITING = "writing"


class FeedbackMethod(StrEnum):
    """How the source feedback was produced."""

    DETERMINISTIC = "deterministic"
    AI = "ai"


class FeedbackStatus(StrEnum):
    """Lifecycle state stored in Obsidian frontmatter."""

    GENERATED = "generated"
    REVIEWED = "reviewed"
    SUPERSEDED = "superseded"


class ExportAction(StrEnum):
    """Safe action selected by the export state machine."""

    CREATE = "create"
    SKIP_UNCHANGED = "skip_unchanged"
    SAFE_UPDATE = "safe_update"
    CONFLICT_USER_MODIFIED = "conflict_user_modified"
    CONFLICT_OUTPUT_MISSING = "conflict_output_missing"
    CONFLICT_SOURCE_KEY = "conflict_source_key"
    WRITE_FAILED = "write_failed"


class ExitCode(IntEnum):
    """Documented CLI process exit codes."""

    SUCCESS = 0
    CONFLICT = 2
    CONFIG_ERROR = 3
    DATABASE_ERROR = 4
    WRITE_ERROR = 5
    PRIVACY_ERROR = 6
