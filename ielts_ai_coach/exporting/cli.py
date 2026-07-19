"""Command-line interface for safe Obsidian exports."""

from __future__ import annotations

import argparse
from datetime import datetime, timezone
import json
import logging
from logging.handlers import RotatingFileHandler
import os
from pathlib import Path
import sys
from typing import Sequence
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from sqlalchemy import text
from sqlalchemy.exc import SQLAlchemyError

from ielts_ai_coach.exporting.enums import (
    ExitCode,
    ExportAction,
)
from ielts_ai_coach.exporting.errors import (
    ExportConfigurationError,
    ExportDatabaseError,
    ExportPrivacyError,
    ExportStateError,
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
    DEFAULT_TIMEZONE,
    transform_reading,
    transform_writing,
)


DEFAULT_DATABASE = Path("data/ielts_ai_coach.db")
DEFAULT_LOG_PATH = Path("data/export_logs/obsidian-export.log")


class SafeArgumentParser(argparse.ArgumentParser):
    """Add the user-selection hint without printing source data."""

    def error(self, message: str) -> None:
        if "--user-id" in message:
            message = f"{message}. Run list-users first"
        super().error(message)


def _positive_int(value: str) -> int:
    parsed = int(value)
    if parsed < 1:
        raise argparse.ArgumentTypeError("must be a positive integer")
    return parsed


def _add_database(parser: argparse.ArgumentParser) -> None:
    parser.add_argument(
        "--database",
        type=Path,
        default=DEFAULT_DATABASE,
        help="SQLite database path (default: data/ielts_ai_coach.db)",
    )


def build_parser() -> argparse.ArgumentParser:
    """Build the stable V1 command tree."""

    parser = SafeArgumentParser(
        prog="python -m ielts_ai_coach.exporting.cli",
        description="Export allowlisted IELTS feedback to Miao OS.",
    )
    subparsers = parser.add_subparsers(dest="command", required=True)

    list_users = subparsers.add_parser(
        "list-users",
        help="List minimum account labels and exportable record counts.",
    )
    _add_database(list_users)

    validate = subparsers.add_parser(
        "validate-config",
        help="Validate the read-only database and Miao OS markers.",
    )
    _add_database(validate)
    validate.add_argument("--vault", type=Path, required=True)

    show_state = subparsers.add_parser(
        "show-state",
        help="Show a safe count for one user's local export state.",
    )
    show_state.add_argument("--state-path", type=Path, required=True)
    show_state.add_argument("--user-id", type=_positive_int, required=True)

    export = subparsers.add_parser(
        "export",
        help="Preview by default, or apply a user-scoped export.",
    )
    _add_database(export)
    export.add_argument("--vault", type=Path, required=True)
    export.add_argument("--user-id", type=_positive_int, required=True)
    export.add_argument(
        "--source",
        choices=("reading", "writing", "all"),
        default="all",
    )
    export.add_argument("--limit", type=_positive_int)
    export.add_argument("--timezone", default=DEFAULT_TIMEZONE)
    mode = export.add_mutually_exclusive_group()
    mode.add_argument(
        "--dry-run",
        action="store_true",
        help="Preview only (the default).",
    )
    mode.add_argument(
        "--apply",
        action="store_true",
        help="Atomically write safe Markdown, state, and logs.",
    )
    export.add_argument(
        "--test",
        action="store_true",
        help="Mark exports from an explicit test database as test data.",
    )
    export.add_argument("--state-path", type=Path)
    export.add_argument("--log-path", type=Path, default=DEFAULT_LOG_PATH)
    return parser


def _print_json(payload: object, *, stream: object | None = None) -> None:
    destination = sys.stdout if stream is None else stream
    print(
        json.dumps(
            payload,
            ensure_ascii=False,
            sort_keys=False,
            separators=(",", ":"),
        ),
        file=destination,
    )


def _safe_error(code: str) -> None:
    print(code, file=sys.stderr)


def _is_explicit_test_database(path: Path) -> bool:
    """Require an obvious test path or an explicit test environment."""

    return (
        "test" in path.name.lower()
        or os.environ.get("IELTS_EXPORT_TEST_DATABASE") == "1"
    )


def _state_path(user_id: int, supplied: Path | None) -> Path:
    if supplied is not None:
        return supplied
    return Path(f"data/export_state/obsidian-user-{user_id}.json")


def _summary(result: ExportResult, *, scanned: int) -> dict[str, object]:
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


def _write_safe_log(
    path: Path,
    *,
    result: ExportResult,
) -> None:
    """Write allowlisted structured metadata, never source content or DB paths."""

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


def _exit_for_result(result: ExportResult) -> ExitCode:
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


def _list_users(database: Path) -> ExitCode:
    factory = create_read_only_session_factory(database)
    with factory() as session:
        users = list_export_users(session)
    payload = [
        {
            "user_id": item.user_id,
            "account_label": item.account_label,
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
    _print_json(payload)
    return ExitCode.SUCCESS


def _validate_config(database: Path, vault: Path) -> ExitCode:
    factory = create_read_only_session_factory(database)
    with factory() as session:
        session.execute(text("SELECT 1")).scalar_one()
    service = ExportService(
        vault_root=vault,
        state_path=Path("data/export_state/validation-only.json"),
    )
    service.plan([], user_id=1)
    _print_json({"database": "read-only-ok", "vault": "miao-os-ok"})
    return ExitCode.SUCCESS


def _show_state(path: Path, user_id: int) -> ExitCode:
    state = load_state(path, user_id=user_id)
    _print_json({"user_id": user_id, "entries": len(state.entries)})
    return ExitCode.SUCCESS


def _export(args: argparse.Namespace) -> ExitCode:
    if args.test and not _is_explicit_test_database(args.database):
        raise ExportConfigurationError("test_database_required")
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
    summary = _summary(result, scanned=len(reading) + len(writing))
    _print_json(summary)
    if args.apply:
        try:
            _write_safe_log(args.log_path, result=result)
        except (OSError, UnicodeError) as exc:
            raise ExportWriteError("log_write_failed") from exc
    return _exit_for_result(result)


def main(argv: Sequence[str] | None = None) -> int:
    """Run one command and return a documented process exit code."""

    parser = build_parser()
    try:
        args = parser.parse_args(argv)
    except SystemExit as exc:
        return (
            ExitCode.SUCCESS
            if exc.code == 0
            else ExitCode.CONFIG_ERROR
        )
    try:
        if args.command == "list-users":
            return _list_users(args.database)
        if args.command == "validate-config":
            return _validate_config(args.database, args.vault)
        if args.command == "show-state":
            return _show_state(args.state_path, args.user_id)
        return _export(args)
    except ExportConfigurationError as exc:
        _safe_error(str(exc))
        return ExitCode.CONFIG_ERROR
    except (ExportDatabaseError, SQLAlchemyError):
        _safe_error("database_error")
        return ExitCode.DATABASE_ERROR
    except ExportPrivacyError:
        _safe_error("privacy_error")
        return ExitCode.PRIVACY_ERROR
    except ExportStateError:
        _safe_error("state_error")
        return ExitCode.CONFIG_ERROR
    except ExportWriteError:
        _safe_error("write_error")
        return ExitCode.WRITE_ERROR
    except (ValueError, TypeError):
        _safe_error("configuration_error")
        return ExitCode.CONFIG_ERROR


if __name__ == "__main__":
    raise SystemExit(main())
