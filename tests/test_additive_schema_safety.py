"""Proof that learner profile V2 is an additive, idempotent schema change."""

from __future__ import annotations

import hashlib
import json
import sqlite3
from pathlib import Path

from ielts_ai_coach.database.connection import initialize_database


NEW_TABLE = "learner_profiles_v2"


def _schema(connection: sqlite3.Connection) -> dict[str, str]:
    """Return application table SQL keyed by table name."""

    rows = connection.execute(
        "SELECT name, sql FROM sqlite_master "
        "WHERE type = 'table' AND name NOT LIKE 'sqlite_%' ORDER BY name"
    ).fetchall()
    return {str(name): str(sql) for name, sql in rows}


def _table_fingerprint(
    connection: sqlite3.Connection,
    table_name: str,
) -> tuple[int, str]:
    """Return deterministic row count and content hash for one test table."""

    columns = [
        row[1]
        for row in connection.execute(
            f'PRAGMA table_info("{table_name}")'
        ).fetchall()
    ]
    order = '"id"' if "id" in columns else "rowid"
    rows = connection.execute(
        f'SELECT * FROM "{table_name}" ORDER BY {order}'
    ).fetchall()
    payload = json.dumps(rows, default=str, ensure_ascii=False).encode("utf-8")
    return len(rows), hashlib.sha256(payload).hexdigest()


def test_create_all_adds_only_v2_and_is_idempotent(tmp_path: Path) -> None:
    """Repeated startup adds one table without changing old schema or rows."""

    database_path = tmp_path / "additive.db"
    database_url = f"sqlite:///{database_path.as_posix()}"
    initialize_database(database_url)
    with sqlite3.connect(database_path) as connection:
        first_schema = _schema(connection)
        old_tables = set(first_schema) - {NEW_TABLE}
        connection.execute(
            "INSERT INTO users "
            "(username, username_normalized, password_hash, is_active, created_at) "
            "VALUES (?, ?, ?, ?, ?)",
            ("SchemaOwner", "schemaowner", "hash", 1, "2026-07-25"),
        )
        connection.commit()
        before = {
            name: _table_fingerprint(connection, name)
            for name in old_tables
        }

    initialize_database(database_url)
    initialize_database(database_url)

    with sqlite3.connect(database_path) as connection:
        second_schema = _schema(connection)
        after = {
            name: _table_fingerprint(connection, name)
            for name in old_tables
        }
        new_count = connection.execute(
            f'SELECT COUNT(*) FROM "{NEW_TABLE}"'
        ).fetchone()[0]

    assert set(second_schema) - old_tables == {NEW_TABLE}
    assert {name: first_schema[name] for name in old_tables} == {
        name: second_schema[name] for name in old_tables
    }
    assert before == after
    assert new_count == 0

