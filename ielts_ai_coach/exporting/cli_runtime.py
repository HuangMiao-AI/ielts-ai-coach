"""Runtime operations kept separate from CLI parsing and presentation."""

from __future__ import annotations

import argparse
from datetime import datetime, timezone
import json
import logging
from logging.handlers import RotatingFileHandler
import os
from pathlib import Path
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from sqlalchemy import text

from ielts_ai_coach.exporting.enums import ExitCode, ExportAction
from ielts_ai_coach.exporting.errors import (
    ExportConfigurationError,
    ExportWriteError,
)
from ielts_ai_coach.exporting.service import ExportResult, ExportService
from ielts_ai_coach.exporting.source_repository import (
    create_read_only_session_factory,
    list_export_users,
    list_exportable_reading_attempts,
    list_exportable_writing_feedback,
)
from ielts_ai_coach.exporting.state import load_state
from ielts_ai_coach.exporting.transform import (
    transform_reading,
    transform_writing,
)


def _is_explicit_test_database(path: Path) -> bool:
    """Require an obvious test path or an explicit test environment."""

    return (
        "test" in path.name.lower()
        or os.environ.get("IELTS_EXPORT_TEST_DATABASE") == "1"
    )


def _state_path(user_id: int, supplied: Path | None) -> Path:
    """Return the supplied state path or one isolated per-user default."""

    if supplied is not None:
        return supplied
    return Path(f"data/export_state/obsidian-user-{user_id}.json")


def _path_is_within(path: Path, directory: Path) -> bool:
    """Return whether a resolved path is inside the supplied directory."""

    try:
        path.resolve().relative_to(directory.resolve())
    except ValueError:
        return False
    return True


def export_summary(
    result: ExportResult,
    *,
    scanned: int,
) -> dict[str, object]:
    """Build the required content-free command summary."""

    actions = [item.action for item in result.items]
    conflicts = {
        ExportAction.CONFLICT_USER_MODIFIED,
        ExportAction.CONFLICT_OUTPUT_MISSING,
        ExportAction.CONFLICT_SOURCE_KEY,
    }
    return {
        "scanned": scanned,
        "eligible": len(result.items),
        "create": actions.count(ExportAction.CREATE),
        "update": actions.count(ExportAction.SAFE_UPDATE),
        "unchanged": actions.count(ExportAction.SKIP_UNCHANGED),
        "conflicts": sum(action in conflicts for action in actions),
        "failed": actions.count(ExportAction.WRITE_FAILED),
        "mode": "apply" if result.apply else "dry-run",
    }


def write_safe_log(path: Path, *, result: ExportResult) -> None:
    """Write allowlisted metadata without content or absolute DB paths."""

    path.parent.mkdir(parents=True, exist_ok=True)
    logger = logging.getLogger(f"obsidian-export-{id(result)}")
    logger.setLevel(logging.INFO)
    logger.propagate = False
    handler = RotatingFileHandler(
        path,
        maxBytes=1_000_000,
        backupCount=3,
        encoding="utf-8",
    )
    handler.setFormatter(logging.Formatter("%(message)s"))
    logger.addHandler(handler)
    try:
        for item in result.items:
            source_entity, source_record_id = item.source_key.split(":", 1)
            payload = {
                "timestamp": datetime.now(timezone.utc)
                .isoformat(timespec="seconds")
                .replace("+00:00", "Z"),
                "mode": "apply",
                "user_id": result.user_id,
                "source_entity": source_entity,
                "source_record_id": int(source_record_id),
                "status": item.action.value,
                "output_relative_path": item.output_relative_path,
                "error_type": item.detail,
            }
            logger.info(
                json.dumps(
                    payload,
                    ensure_ascii=False,
                    separators=(",", ":"),
                )
            )
    finally:
        handler.close()
        logger.removeHandler(handler)


def exit_for_result(result: ExportResult) -> ExitCode:
    """Map result actions to the documented process exit code."""

    actions = {item.action for item in result.items}
    if ExportAction.WRITE_FAILED in actions:
        return ExitCode.WRITE_ERROR
    if actions & {
        ExportAction.CONFLICT_USER_MODIFIED,
        ExportAction.CONFLICT_OUTPUT_MISSING,
        ExportAction.CONFLICT_SOURCE_KEY,
    }:
        return ExitCode.CONFLICT
    return ExitCode.SUCCESS


def list_users_payload(database: Path) -> list[dict[str, object]]:
    """Read and return minimum user-selection metadata."""

    factory = create_read_only_session_factory(database)
    with factory() as session:
        users = list_export_users(session)
    return [
        {
            "user_id": item.user_id,
            "account_label": item.account_label,
            "has_profile": item.has_profile,
            "reading_count": item.reading_count,
            "writing_count": item.writing_count,
            "recent_activity_at": (
                item.recent_activity_at.isoformat()
                if item.recent_activity_at
                else None
            ),
        }
        for item in users
    ]


def validate_config_payload(
    database: Path,
    vault: Path,
) -> dict[str, str]:
    """Validate read-only DB access and the required Miao OS markers."""

    factory = create_read_only_session_factory(database)
    with factory() as session:
        session.execute(text("SELECT 1")).scalar_one()
    service = ExportService(
        vault_root=vault,
        state_path=Path("data/export_state/validation-only.json"),
    )
    service.plan([], user_id=1)
    return {"database": "read-only-ok", "vault": "miao-os-ok"}


def show_state_payload(path: Path, user_id: int) -> dict[str, int]:
    """Return only the owner and entry count from local state."""

    state = load_state(path, user_id=user_id)
    return {"user_id": user_id, "entries": len(state.entries)}


def run_export(
    args: argparse.Namespace,
) -> tuple[ExitCode, dict[str, object]]:
    """Read, transform, plan/apply, log, and summarize one safe export."""

    if args.test and not _is_explicit_test_database(args.database):
        raise ExportConfigurationError("test_database_required")
    if _path_is_within(args.log_path, args.vault):
        raise ExportConfigurationError("log_path_inside_vault")
    try:
        ZoneInfo(args.timezone)
    except ZoneInfoNotFoundError as exc:
        raise ExportConfigurationError("invalid_timezone") from exc
    factory = create_read_only_session_factory(args.database)
    with factory() as session:
        reading = (
            list_exportable_reading_attempts(
                session,
                user_id=args.user_id,
                limit=args.limit,
            )
            if args.source in {"reading", "all"}
            else []
        )
        writing = (
            list_exportable_writing_feedback(
                session,
                user_id=args.user_id,
                limit=args.limit,
            )
            if args.source in {"writing", "all"}
            else []
        )
    records = [
        *[
            transform_reading(
                item,
                timezone_name=args.timezone,
                test=args.test,
            )
            for item in reading
        ],
        *[
            transform_writing(
                item,
                timezone_name=args.timezone,
                test=args.test,
            )
            for item in writing
        ],
    ]
    service = ExportService(
        vault_root=args.vault,
        state_path=_state_path(args.user_id, args.state_path),
    )
    result = service.execute(
        records,
        user_id=args.user_id,
        apply=args.apply,
    )
    summary = export_summary(result, scanned=len(reading) + len(writing))
    if args.apply:
        try:
            write_safe_log(args.log_path, result=result)
        except (OSError, UnicodeError) as exc:
            raise ExportWriteError("log_write_failed") from exc
    return exit_for_result(result), summary
