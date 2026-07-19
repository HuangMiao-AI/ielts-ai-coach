"""Safe planning and execution for Obsidian Markdown exports."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path

from ielts_ai_coach.exporting.atomic_writer import atomic_write_text
from ielts_ai_coach.exporting.contracts import FeedbackExportRecord
from ielts_ai_coach.exporting.enums import ExportAction
from ielts_ai_coach.exporting.errors import (
    ExportConfigurationError,
    ExportStateError,
    ExportWriteError,
)
from ielts_ai_coach.exporting.filename import output_relative_path
from ielts_ai_coach.exporting.fingerprint import (
    sha256_bytes,
    sha256_text,
    source_fingerprint,
)
from ielts_ai_coach.exporting.obsidian_renderer import (
    ObsidianMarkdownAdapter,
    parse_source_key,
)
from ielts_ai_coach.exporting.state import (
    ExportState,
    ExportStateEntry,
    load_state,
    save_state,
    state_key,
)


_VAULT_MARKERS = ("00 Dashboard", "02 IELTS", "99 Templates")


@dataclass(frozen=True, slots=True)
class ExportItemResult:
    """Safe result for one source record."""

    action: ExportAction
    source_key: str
    output_relative_path: str
    detail: str | None = None


@dataclass(frozen=True, slots=True)
class ExportResult:
    """Result for one explicit user-scoped run."""

    user_id: int
    apply: bool
    items: tuple[ExportItemResult, ...]


class ExportService:
    """Plan idempotent output and apply only provably safe writes."""

    def __init__(self, *, vault_root: Path, state_path: Path) -> None:
        self.vault_root = vault_root
        self.state_path = state_path
        self._adapter = ObsidianMarkdownAdapter()

    def _validate_vault(self) -> None:
        if not self.vault_root.is_dir() or any(
            not (self.vault_root / marker).is_dir()
            for marker in _VAULT_MARKERS
        ):
            raise ExportConfigurationError("invalid_miao_vault")

    def render(self, record: FeedbackExportRecord) -> str:
        """Return deterministic Obsidian Markdown."""

        return self._adapter.preview(record)

    def target_path_for(
        self,
        record: FeedbackExportRecord,
        *,
        existing_path: str | None = None,
    ) -> Path:
        """Resolve one validated managed path beneath the Vault root."""

        relative = output_relative_path(record, existing_path=existing_path)
        target = self.vault_root.joinpath(*relative.parts)
        try:
            target.resolve().relative_to(self.vault_root.resolve())
        except ValueError as exc:
            raise ExportConfigurationError("unsafe_output_path") from exc
        return target

    def _plan_one(
        self,
        record: FeedbackExportRecord,
        state: ExportState,
    ) -> tuple[ExportItemResult, Path, str, str]:
        key = state_key(record.source_entity, record.source_record_id)
        entry = state.entries.get(key)
        relative = output_relative_path(
            record,
            existing_path=entry.output_relative_path if entry else None,
        )
        target = self.target_path_for(
            record,
            existing_path=str(relative),
        )
        rendered = self.render(record)
        fingerprint = source_fingerprint(record)
        result_kwargs = {
            "source_key": key,
            "output_relative_path": relative.as_posix(),
        }

        if entry is None:
            if not target.exists():
                action = ExportAction.CREATE
            else:
                existing_key = self._read_source_key(target)
                action = (
                    ExportAction.CONFLICT_SOURCE_KEY
                    if existing_key
                    != (record.source_entity, record.source_record_id)
                    else ExportAction.CONFLICT_USER_MODIFIED
                )
            return ExportItemResult(action=action, **result_kwargs), target, (
                rendered
            ), fingerprint

        if not target.is_file():
            return (
                ExportItemResult(
                    action=ExportAction.CONFLICT_OUTPUT_MISSING,
                    **result_kwargs,
                ),
                target,
                rendered,
                fingerprint,
            )
        existing_key = self._read_source_key(target)
        if existing_key != (record.source_entity, record.source_record_id):
            return (
                ExportItemResult(
                    action=ExportAction.CONFLICT_SOURCE_KEY,
                    **result_kwargs,
                ),
                target,
                rendered,
                fingerprint,
            )
        if sha256_bytes(target.read_bytes()) != entry.last_exported_file_hash:
            return (
                ExportItemResult(
                    action=ExportAction.CONFLICT_USER_MODIFIED,
                    **result_kwargs,
                ),
                target,
                rendered,
                fingerprint,
            )
        action = (
            ExportAction.SKIP_UNCHANGED
            if fingerprint == entry.source_fingerprint
            else ExportAction.SAFE_UPDATE
        )
        return (
            ExportItemResult(action=action, **result_kwargs),
            target,
            rendered,
            fingerprint,
        )

    @staticmethod
    def _read_source_key(path: Path) -> tuple[object, int] | None:
        try:
            return parse_source_key(path.read_text(encoding="utf-8"))
        except (OSError, UnicodeError):
            return None

    def plan(
        self,
        records: list[FeedbackExportRecord],
        *,
        user_id: int,
    ) -> ExportResult:
        """Return actions without writing to the Vault or state."""

        self._validate_vault()
        state = load_state(self.state_path, user_id=user_id)
        items = tuple(
            self._plan_one(record, state)[0] for record in records
        )
        return ExportResult(user_id=user_id, apply=False, items=items)

    def execute(
        self,
        records: list[FeedbackExportRecord],
        *,
        user_id: int,
        apply: bool,
    ) -> ExportResult:
        """Plan or safely apply one explicit user-scoped export run."""

        self._validate_vault()
        state = load_state(self.state_path, user_id=user_id)
        results: list[ExportItemResult] = []
        for record in records:
            item, target, rendered, fingerprint = self._plan_one(record, state)
            if not apply or item.action not in {
                ExportAction.CREATE,
                ExportAction.SAFE_UPDATE,
            }:
                results.append(item)
                continue
            previous_state = state
            try:
                atomic_write_text(target, rendered)
                entry = ExportStateEntry(
                    source_entity=record.source_entity,
                    source_record_id=record.source_record_id,
                    source_fingerprint=fingerprint,
                    output_relative_path=item.output_relative_path,
                    last_exported_file_hash=sha256_text(rendered),
                    exported_at=datetime.now(timezone.utc),
                )
                state = state.with_entry(entry)
                save_state(self.state_path, state)
                results.append(item)
            except (ExportWriteError, ExportStateError):
                state = previous_state
                results.append(
                    ExportItemResult(
                        action=ExportAction.WRITE_FAILED,
                        source_key=item.source_key,
                        output_relative_path=item.output_relative_path,
                        detail="write_failed",
                    )
                )
        return ExportResult(
            user_id=user_id,
            apply=apply,
            items=tuple(results),
        )
