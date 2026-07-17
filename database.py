"""SQLite persistence for study profiles, plans and history."""

import json
import sqlite3
from datetime import datetime
from pathlib import Path
from typing import Any

from config import DATABASE_PATH
from models import AnalysisResult, StudyRecord


SCHEMA = """
CREATE TABLE IF NOT EXISTS study_records (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    student_name TEXT NOT NULL,
    listening REAL NOT NULL,
    reading REAL NOT NULL,
    writing REAL NOT NULL,
    speaking REAL NOT NULL,
    overall_band REAL NOT NULL,
    lowest_subjects TEXT NOT NULL,
    daily_minutes INTEGER NOT NULL,
    recommendations TEXT NOT NULL,
    study_plan TEXT NOT NULL,
    created_at TEXT NOT NULL
)
"""


def _connect(database_path: Path = DATABASE_PATH) -> sqlite3.Connection:
    database_path.parent.mkdir(parents=True, exist_ok=True)
    connection = sqlite3.connect(database_path)
    connection.row_factory = sqlite3.Row
    return connection


def initialize_database(database_path: Path = DATABASE_PATH) -> None:
    """Create the local database and table when they do not yet exist."""

    with _connect(database_path) as connection:
        connection.execute(SCHEMA)


def save_study_record(
    student_name: str,
    scores: dict[str, float],
    analysis: AnalysisResult,
    daily_minutes: int,
    study_plan: dict[str, Any],
    database_path: Path = DATABASE_PATH,
) -> int:
    """Persist one generated study profile and return its record ID."""

    cleaned_name = student_name.strip()
    if not cleaned_name:
        raise ValueError("姓名不能为空。")

    initialize_database(database_path)
    values = (
        cleaned_name,
        scores["listening"],
        scores["reading"],
        scores["writing"],
        scores["speaking"],
        analysis.overall_band,
        json.dumps(analysis.lowest_subjects, ensure_ascii=False),
        daily_minutes,
        json.dumps(analysis.recommendations, ensure_ascii=False),
        json.dumps(study_plan, ensure_ascii=False),
        datetime.now().astimezone().isoformat(timespec="seconds"),
    )

    with _connect(database_path) as connection:
        cursor = connection.execute(
            """
            INSERT INTO study_records (
                student_name, listening, reading, writing, speaking,
                overall_band, lowest_subjects, daily_minutes,
                recommendations, study_plan, created_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            values,
        )
        return int(cursor.lastrowid)


def get_recent_records(
    limit: int = 10, database_path: Path = DATABASE_PATH
) -> list[StudyRecord]:
    """Return recent records, newest first."""

    if limit < 1:
        return []
    initialize_database(database_path)

    with _connect(database_path) as connection:
        rows = connection.execute(
            "SELECT * FROM study_records ORDER BY id DESC LIMIT ?", (limit,)
        ).fetchall()

    return [
        StudyRecord(
            id=row["id"],
            student_name=row["student_name"],
            scores={
                "listening": row["listening"],
                "reading": row["reading"],
                "writing": row["writing"],
                "speaking": row["speaking"],
            },
            overall_band=row["overall_band"],
            lowest_subjects=json.loads(row["lowest_subjects"]),
            daily_minutes=row["daily_minutes"],
            recommendations=json.loads(row["recommendations"]),
            study_plan=json.loads(row["study_plan"]),
            created_at=row["created_at"],
        )
        for row in rows
    ]
