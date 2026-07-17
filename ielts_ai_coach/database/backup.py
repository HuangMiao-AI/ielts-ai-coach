"""Consistent daily backups for the local SQLite database."""

from __future__ import annotations

import logging
import os
import sqlite3
import threading
import uuid
from contextlib import closing
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

from sqlalchemy.engine import make_url

from ielts_ai_coach.config import get_backup_dir, get_database_url


LOGGER = logging.getLogger(__name__)
BACKUP_LOCK = threading.Lock()
SHANGHAI_TIMEZONE = ZoneInfo("Asia/Shanghai")


@dataclass(frozen=True)
class BackupResult:
    """The outcome of one backup check."""

    created: bool
    path: Path | None
    reason: str


def _sqlite_path(database_url: str) -> Path | None:
    """Return the source path when the URL describes file-based SQLite."""

    parsed_url = make_url(database_url)
    if not parsed_url.drivername.startswith("sqlite"):
        return None
    if parsed_url.database in (None, "", ":memory:"):
        return None
    return Path(parsed_url.database).expanduser().resolve()


def _remove_expired_backups(
    backup_dir: Path, source_stem: str, retention: int
) -> None:
    """Keep only the newest configured number of automatic backups."""

    backups = sorted(
        backup_dir.glob(f"{source_stem}_????-??-??.db"),
        key=lambda item: item.name,
        reverse=True,
    )
    for expired_backup in backups[retention:]:
        expired_backup.unlink(missing_ok=True)


def backup_database_if_due(
    *,
    database_url: str | None = None,
    backup_dir: Path | None = None,
    now: datetime | None = None,
    retention: int = 7,
) -> BackupResult:
    """Create at most one consistent SQLite backup per Shanghai date."""

    if retention < 1:
        raise ValueError("Backup retention must be at least one.")

    source_path = _sqlite_path(database_url or get_database_url())
    if source_path is None:
        return BackupResult(False, None, "not_file_sqlite")
    if not source_path.exists():
        return BackupResult(False, None, "source_missing")

    target_dir = (backup_dir or get_backup_dir()).resolve()
    active_time = now or datetime.now(SHANGHAI_TIMEZONE)
    if active_time.tzinfo is None:
        active_time = active_time.replace(tzinfo=SHANGHAI_TIMEZONE)
    date_label = active_time.astimezone(SHANGHAI_TIMEZONE).date().isoformat()
    destination = target_dir / f"{source_path.stem}_{date_label}.db"

    with BACKUP_LOCK:
        target_dir.mkdir(parents=True, exist_ok=True)
        if destination.exists():
            _remove_expired_backups(target_dir, source_path.stem, retention)
            return BackupResult(False, destination, "already_created")

        temporary_path = target_dir / (
            f".{destination.name}.{uuid.uuid4().hex}.tmp"
        )
        try:
            with closing(sqlite3.connect(source_path)) as source_connection:
                with closing(
                    sqlite3.connect(temporary_path)
                ) as backup_connection:
                    source_connection.backup(backup_connection)
            os.replace(temporary_path, destination)
            _remove_expired_backups(target_dir, source_path.stem, retention)
            return BackupResult(True, destination, "created")
        except (OSError, sqlite3.Error):
            try:
                temporary_path.unlink(missing_ok=True)
            except OSError:
                LOGGER.warning("Could not remove a failed backup temporary file.")
            LOGGER.exception("SQLite backup failed.")
            return BackupResult(False, None, "failed")
