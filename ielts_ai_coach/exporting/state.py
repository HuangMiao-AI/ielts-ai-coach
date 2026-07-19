"""Versioned per-user state for safe Obsidian exports."""

from __future__ import annotations

from dataclasses import dataclass, field, replace
from datetime import datetime, timezone
import json
from pathlib import Path
import re
from typing import Any

from ielts_ai_coach.exporting.atomic_writer import atomic_write_text
from ielts_ai_coach.exporting.enums import SourceEntity
from ielts_ai_coach.exporting.errors import ExportStateError, ExportWriteError
from ielts_ai_coach.exporting.filename import validate_existing_output_path


STATE_SCHEMA_VERSION = 1
EXPORTER_VERSION = "1.0.0"
SOURCE_SYSTEM = "ielts-ai-coach"
_SHA256 = re.compile(r"^[0-9a-f]{64}$")


def state_key(source_entity: SourceEntity, source_record_id: int) -> str:
    """Build the stable state key for one source record."""

    if source_record_id <= 0:
        raise ExportStateError("state_invalid_source_record_id")
    return f"{source_entity.value}:{source_record_id}"


@dataclass(frozen=True, slots=True)
class ExportStateEntry:
    """Trusted metadata about one previously generated Markdown file."""

    source_entity: SourceEntity
    source_record_id: int
    source_fingerprint: str
    output_relative_path: str
    last_exported_file_hash: str
    exported_at: datetime

    def __post_init__(self) -> None:
        if (
            not isinstance(self.source_record_id, int)
            or isinstance(self.source_record_id, bool)
            or self.source_record_id <= 0
        ):
            raise ExportStateError("state_invalid_source_record_id")
        if not isinstance(self.source_fingerprint, str) or not _SHA256.fullmatch(
            self.source_fingerprint
        ):
            raise ExportStateError("state_invalid_source_fingerprint")
        if not isinstance(
            self.last_exported_file_hash, str
        ) or not _SHA256.fullmatch(self.last_exported_file_hash):
            raise ExportStateError("state_invalid_file_hash")
        if not isinstance(self.exported_at, datetime):
            raise ExportStateError("state_invalid_exported_at")
        if (
            self.exported_at.tzinfo is None
            or self.exported_at.utcoffset() is None
        ):
            raise ExportStateError("state_invalid_exported_at")
        if not isinstance(self.output_relative_path, str):
            raise ExportStateError("state_invalid_output_path")
        validate_existing_output_path(self.output_relative_path)


@dataclass(frozen=True, slots=True)
class ExportState:
    """One isolated state document for one explicitly selected user."""

    user_id: int
    entries: dict[str, ExportStateEntry] = field(default_factory=dict)

    def __post_init__(self) -> None:
        if (
            not isinstance(self.user_id, int)
            or isinstance(self.user_id, bool)
            or self.user_id <= 0
        ):
            raise ExportStateError("state_invalid_user_id")
        for key, entry in self.entries.items():
            if key != state_key(entry.source_entity, entry.source_record_id):
                raise ExportStateError("state_invalid_entry_key")

    def with_entry(self, entry: ExportStateEntry) -> ExportState:
        """Return a new state containing the supplied entry."""

        entries = dict(self.entries)
        entries[state_key(entry.source_entity, entry.source_record_id)] = entry
        return replace(self, entries=entries)


def _timestamp(value: datetime) -> str:
    return value.astimezone(timezone.utc).isoformat(timespec="seconds").replace(
        "+00:00", "Z"
    )


def _entry_payload(entry: ExportStateEntry) -> dict[str, Any]:
    return {
        "source_entity": entry.source_entity.value,
        "source_record_id": entry.source_record_id,
        "source_fingerprint": entry.source_fingerprint,
        "output_relative_path": entry.output_relative_path,
        "last_exported_file_hash": entry.last_exported_file_hash,
        "exported_at": _timestamp(entry.exported_at),
    }


def _state_payload(state: ExportState) -> dict[str, Any]:
    return {
        "schema_version": STATE_SCHEMA_VERSION,
        "exporter_version": EXPORTER_VERSION,
        "source_system": SOURCE_SYSTEM,
        "user_id": state.user_id,
        "entries": {
            key: _entry_payload(state.entries[key])
            for key in sorted(state.entries)
        },
    }


def _parse_timestamp(value: object) -> datetime:
    if not isinstance(value, str):
        raise ExportStateError("state_invalid")
    parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    if parsed.tzinfo is None or parsed.utcoffset() is None:
        raise ExportStateError("state_invalid")
    return parsed


def _parse_entry(value: object) -> ExportStateEntry:
    if not isinstance(value, dict) or set(value) != {
        "source_entity",
        "source_record_id",
        "source_fingerprint",
        "output_relative_path",
        "last_exported_file_hash",
        "exported_at",
    }:
        raise ExportStateError("state_invalid")
    return ExportStateEntry(
        source_entity=SourceEntity(value["source_entity"]),
        source_record_id=value["source_record_id"],
        source_fingerprint=value["source_fingerprint"],
        output_relative_path=value["output_relative_path"],
        last_exported_file_hash=value["last_exported_file_hash"],
        exported_at=_parse_timestamp(value["exported_at"]),
    )


def load_state(path: Path, *, user_id: int) -> ExportState:
    """Load trusted state or return an empty state when no file exists."""

    if not path.exists():
        return ExportState(user_id=user_id)
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
        if (
            not isinstance(payload, dict)
            or set(payload)
            != {
                "schema_version",
                "exporter_version",
                "source_system",
                "user_id",
                "entries",
            }
            or payload["schema_version"] != STATE_SCHEMA_VERSION
            or payload["exporter_version"] != EXPORTER_VERSION
            or payload["source_system"] != SOURCE_SYSTEM
            or not isinstance(payload["entries"], dict)
        ):
            raise ExportStateError("state_invalid")
        if payload["user_id"] != user_id:
            raise ExportStateError("state_user_mismatch")
        entries = {
            key: _parse_entry(value)
            for key, value in payload["entries"].items()
        }
        return ExportState(user_id=user_id, entries=entries)
    except ExportStateError:
        raise
    except (OSError, UnicodeError, ValueError, TypeError, KeyError) as exc:
        raise ExportStateError("state_invalid") from exc


def save_state(path: Path, state: ExportState) -> None:
    """Persist state in deterministic JSON via atomic replacement."""

    content = (
        json.dumps(
            _state_payload(state),
            ensure_ascii=False,
            sort_keys=False,
            indent=2,
        )
        + "\n"
    )
    try:
        atomic_write_text(path, content)
    except ExportWriteError as exc:
        raise ExportStateError("state_write_failed") from exc
