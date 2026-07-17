"""Tests for consistent daily SQLite backups."""

from __future__ import annotations

import sqlite3
from datetime import datetime, timedelta
from pathlib import Path
from zoneinfo import ZoneInfo

from ielts_ai_coach.database.backup import backup_database_if_due
from ielts_ai_coach.database.connection import initialize_database


SHANGHAI_TIMEZONE = ZoneInfo("Asia/Shanghai")


def test_backup_is_created_only_once_per_day(
    test_database_url: str, tmp_path: Path
) -> None:
    """Repeated checks on one date must produce a single backup."""

    initialize_database(test_database_url)
    backup_dir = tmp_path / "backups"
    active_time = datetime(2026, 7, 16, 9, 0, tzinfo=SHANGHAI_TIMEZONE)

    first_result = backup_database_if_due(
        database_url=test_database_url,
        backup_dir=backup_dir,
        now=active_time,
    )
    second_result = backup_database_if_due(
        database_url=test_database_url,
        backup_dir=backup_dir,
        now=active_time,
    )

    assert first_result.created is True
    assert second_result.created is False
    assert second_result.reason == "already_created"
    assert len(list(backup_dir.glob("*.db"))) == 1

    with sqlite3.connect(first_result.path) as backup_connection:
        table = backup_connection.execute(
            "SELECT name FROM sqlite_master WHERE name = 'users'"
        ).fetchone()
    assert table == ("users",)


def test_backup_retention_keeps_latest_seven(
    test_database_url: str, tmp_path: Path
) -> None:
    """Automatic cleanup must retain only the newest seven daily files."""

    initialize_database(test_database_url)
    backup_dir = tmp_path / "backups"
    start_time = datetime(2026, 7, 1, 9, 0, tzinfo=SHANGHAI_TIMEZONE)

    for offset in range(8):
        result = backup_database_if_due(
            database_url=test_database_url,
            backup_dir=backup_dir,
            now=start_time + timedelta(days=offset),
        )
        assert result.created is True

    backup_names = sorted(path.name for path in backup_dir.glob("*.db"))
    assert len(backup_names) == 7
    assert "test_2026-07-01.db" not in backup_names
    assert "test_2026-07-08.db" in backup_names
