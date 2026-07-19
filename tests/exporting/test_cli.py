"""CLI tests for safe, explicit, user-scoped exports."""

from __future__ import annotations

import json
from pathlib import Path

from sqlalchemy.orm import Session, sessionmaker

from tests.exporting.test_source_repository import _seed_user

from ielts_ai_coach.exporting.cli import main
from ielts_ai_coach.exporting.enums import ExitCode


def _vault(tmp_path: Path) -> Path:
    vault = tmp_path / "Miao OS"
    for relative in ("00 Dashboard", "02 IELTS", "99 Templates"):
        (vault / relative).mkdir(parents=True)
    return vault


def _database_path(test_database_url: str) -> Path:
    return Path(test_database_url.removeprefix("sqlite:///"))


def test_help_lists_only_explicit_subcommands(capsys: object) -> None:
    code = main(["--help"])
    output = capsys.readouterr().out

    assert code == ExitCode.SUCCESS
    assert "list-users" in output
    assert "export" in output
    assert "validate-config" in output
    assert "show-state" in output
    assert "all-users" not in output


def test_export_requires_user_id_and_rejects_all_users(
    capsys: object, tmp_path: Path
) -> None:
    missing = main(
        [
            "export",
            "--database",
            str(tmp_path / "test.db"),
            "--vault",
            str(_vault(tmp_path)),
        ]
    )
    unsupported = main(["export", "--all-users"])
    error = capsys.readouterr().err

    assert missing == ExitCode.CONFIG_ERROR
    assert unsupported == ExitCode.CONFIG_ERROR
    assert "list-users" in error


def test_apply_and_dry_run_are_mutually_exclusive(
    capsys: object,
) -> None:
    code = main(
        [
            "export",
            "--database",
            "test.db",
            "--vault",
            "Miao OS",
            "--user-id",
            "1",
            "--apply",
            "--dry-run",
        ]
    )

    assert code == ExitCode.CONFIG_ERROR
    assert "not allowed" in capsys.readouterr().err


def test_default_export_is_dry_run_and_writes_nothing(
    capsys: object,
    tmp_path: Path,
    test_database_url: str,
    session_factory: sessionmaker[Session],
) -> None:
    user_id, _, _ = _seed_user("CliDryRun", session_factory, attempt_score=1)
    vault = _vault(tmp_path)
    state = tmp_path / "state.json"
    log = tmp_path / "export.log"

    code = main(
        [
            "export",
            "--database",
            str(_database_path(test_database_url)),
            "--vault",
            str(vault),
            "--user-id",
            str(user_id),
            "--state-path",
            str(state),
            "--log-path",
            str(log),
        ]
    )
    summary = json.loads(capsys.readouterr().out)

    assert code == ExitCode.SUCCESS
    assert summary == {
        "scanned": 2,
        "eligible": 2,
        "create": 2,
        "update": 0,
        "unchanged": 0,
        "conflicts": 0,
        "failed": 0,
        "mode": "dry-run",
    }
    assert not (vault / "02 IELTS" / "AI Feedback").exists()
    assert not state.exists()
    assert not log.exists()


def test_apply_writes_safe_outputs_state_and_structured_log(
    capsys: object,
    tmp_path: Path,
    test_database_url: str,
    session_factory: sessionmaker[Session],
) -> None:
    user_id, _, _ = _seed_user("CliApply", session_factory, attempt_score=1)
    vault = _vault(tmp_path)
    state = tmp_path / "state.json"
    log = tmp_path / "export.log"

    code = main(
        [
            "export",
            "--database",
            str(_database_path(test_database_url)),
            "--vault",
            str(vault),
            "--user-id",
            str(user_id),
            "--apply",
            "--test",
            "--state-path",
            str(state),
            "--log-path",
            str(log),
        ]
    )
    summary = json.loads(capsys.readouterr().out)
    notes = list((vault / "02 IELTS" / "AI Feedback").rglob("*.md"))
    combined = "\n".join(note.read_text(encoding="utf-8") for note in notes)
    logged = log.read_text(encoding="utf-8")

    assert code == ExitCode.SUCCESS
    assert summary["create"] == 2
    assert len(notes) == 2
    assert state.is_file()
    assert '"status":"create"' in logged
    assert str(_database_path(test_database_url)) not in logged
    for forbidden in (
        "Private full essay content",
        "Private full prompt",
        '"q1":"A"',
        "secure-pass-01",
    ):
        assert forbidden not in combined
        assert forbidden not in logged


def test_real_database_test_marker_is_rejected_before_access(
    capsys: object, tmp_path: Path
) -> None:
    database = tmp_path / "ielts_ai_coach.db"
    database.write_bytes(b"not accessed")

    code = main(
        [
            "export",
            "--database",
            str(database),
            "--vault",
            str(_vault(tmp_path)),
            "--user-id",
            "1",
            "--test",
        ]
    )

    assert code == ExitCode.CONFIG_ERROR
    assert "test_database_required" in capsys.readouterr().err


def test_list_users_prints_minimum_safe_summary(
    capsys: object,
    test_database_url: str,
    session_factory: sessionmaker[Session],
) -> None:
    user_id, _, _ = _seed_user("CliList", session_factory, attempt_score=1)

    code = main(
        [
            "list-users",
            "--database",
            str(_database_path(test_database_url)),
        ]
    )
    output = capsys.readouterr().out

    assert code == ExitCode.SUCCESS
    assert f'"user_id":{user_id}' in output
    assert '"account_label":"CliList"' in output
    assert "password" not in output.lower()
    assert "profile" not in output.lower()


def test_conflict_returns_documented_exit_code(
    capsys: object,
    tmp_path: Path,
    test_database_url: str,
    session_factory: sessionmaker[Session],
) -> None:
    user_id, _, _ = _seed_user("CliConflict", session_factory, attempt_score=1)
    vault = _vault(tmp_path)
    common = [
        "export",
        "--database",
        str(_database_path(test_database_url)),
        "--vault",
        str(vault),
        "--user-id",
        str(user_id),
        "--apply",
        "--state-path",
        str(tmp_path / "state.json"),
        "--log-path",
        str(tmp_path / "export.log"),
    ]
    assert main(common) == ExitCode.SUCCESS
    capsys.readouterr()
    note = next((vault / "02 IELTS" / "AI Feedback").rglob("*.md"))
    note.write_text(
        note.read_text(encoding="utf-8") + "User edit\n",
        encoding="utf-8",
    )

    code = main(common)
    summary = json.loads(capsys.readouterr().out)

    assert code == ExitCode.CONFLICT
    assert summary["conflicts"] == 1


def test_show_state_reports_metadata_not_generated_content(
    capsys: object, tmp_path: Path
) -> None:
    state_path = tmp_path / "state.json"

    code = main(
        [
            "show-state",
            "--state-path",
            str(state_path),
            "--user-id",
            "8",
        ]
    )
    payload = json.loads(capsys.readouterr().out)

    assert code == ExitCode.SUCCESS
    assert payload == {"user_id": 8, "entries": 0}
