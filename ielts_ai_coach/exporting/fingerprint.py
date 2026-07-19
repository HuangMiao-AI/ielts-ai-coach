"""Deterministic SHA-256 helpers for safe DTOs and generated files."""

from __future__ import annotations

import hashlib
import json

from ielts_ai_coach.exporting.contracts import FeedbackExportRecord


def sha256_bytes(payload: bytes) -> str:
    """Return a lowercase SHA-256 digest."""

    return hashlib.sha256(payload).hexdigest()


def sha256_text(payload: str) -> str:
    """Hash one UTF-8 text value."""

    return sha256_bytes(payload.encode("utf-8"))


def canonical_record_json(record: FeedbackExportRecord) -> str:
    """Serialize one already-allowlisted DTO in stable JSON form."""

    return json.dumps(
        record.model_dump(mode="json"),
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    )


def source_fingerprint(record: FeedbackExportRecord) -> str:
    """Hash only the strict allowlisted shared record."""

    return sha256_text(canonical_record_json(record))
