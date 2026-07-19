"""Command-line interface for safe Obsidian exports."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys
from typing import Sequence

from sqlalchemy.exc import SQLAlchemyError

from ielts_ai_coach.exporting.cli_runtime import (
    list_users_payload,
    run_export,
    show_state_payload,
    validate_config_payload,
)
from ielts_ai_coach.exporting.enums import ExitCode
from ielts_ai_coach.exporting.errors import (
    ExportConfigurationError,
    ExportDatabaseError,
    ExportPrivacyError,
    ExportStateError,
    ExportWriteError,
)
from ielts_ai_coach.exporting.transform import DEFAULT_TIMEZONE


DEFAULT_DATABASE = Path("data/ielts_ai_coach.db")
DEFAULT_LOG_PATH = Path("data/export_logs/obsidian-export.log")


class SafeArgumentParser(argparse.ArgumentParser):
    """Add the user-selection hint without printing source data."""

    def error(self, message: str) -> None:
        """Print a safe parser error and stop argument parsing."""

        if "--user-id" in message:
            message = f"{message}. Run list-users first"
        super().error(message)


def _positive_int(value: str) -> int:
    """Parse a strictly positive command-line integer."""

    parsed = int(value)
    if parsed < 1:
        raise argparse.ArgumentTypeError("must be a positive integer")
    return parsed


def _add_database(parser: argparse.ArgumentParser) -> None:
    """Add the shared database option to one subcommand."""

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
    """Print compact UTF-8 JSON to the current output stream."""

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
    """Print one content-free error code."""

    print(code, file=sys.stderr)


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
            _print_json(list_users_payload(args.database))
            return ExitCode.SUCCESS
        if args.command == "validate-config":
            _print_json(validate_config_payload(args.database, args.vault))
            return ExitCode.SUCCESS
        if args.command == "show-state":
            _print_json(show_state_payload(args.state_path, args.user_id))
            return ExitCode.SUCCESS
        exit_code, summary = run_export(args)
        _print_json(summary)
        return exit_code
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
