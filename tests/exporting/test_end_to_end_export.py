"""End-to-end test from temporary SQLite records to temporary Vault."""

from __future__ import annotations

from pathlib import Path

from sqlalchemy.orm import Session, sessionmaker

from tests.exporting.test_source_repository import _seed_user

from ielts_ai_coach.exporting.enums import ExportAction
from ielts_ai_coach.exporting.service import ExportService
from ielts_ai_coach.exporting.source_repository import (
    list_exportable_reading_attempts,
    list_exportable_writing_feedback,
)
from ielts_ai_coach.exporting.transform import (
    transform_reading,
    transform_writing,
)


def test_temporary_database_to_temporary_vault_export(
    tmp_path: Path,
    session_factory: sessionmaker[Session],
) -> None:
    user_id, _, _ = _seed_user(
        "EndToEnd", session_factory, attempt_score=1
    )
    with session_factory() as session:
        records = [
            *[
                transform_reading(item, test=True)
                for item in list_exportable_reading_attempts(
                    session, user_id=user_id
                )
            ],
            *[
                transform_writing(item, test=True)
                for item in list_exportable_writing_feedback(
                    session, user_id=user_id
                )
            ],
        ]
    vault = tmp_path / "Miao OS"
    for relative in ("00 Dashboard", "02 IELTS", "99 Templates"):
        (vault / relative).mkdir(parents=True)
    service = ExportService(
        vault_root=vault,
        state_path=tmp_path / "state.json",
    )

    first = service.execute(records, user_id=user_id, apply=True)
    second = service.execute(records, user_id=user_id, apply=True)
    notes = sorted((vault / "02 IELTS" / "AI Feedback").rglob("*.md"))

    assert [item.action for item in first.items] == [
        ExportAction.CREATE,
        ExportAction.CREATE,
    ]
    assert all(
        item.action is ExportAction.SKIP_UNCHANGED for item in second.items
    )
    assert len(notes) == 2
    combined = "\n".join(item.read_text(encoding="utf-8") for item in notes)
    assert "Private full essay content" not in combined
    assert "Private full prompt" not in combined
    assert '"q1":"A"' not in combined
