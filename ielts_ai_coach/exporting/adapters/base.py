"""Provider-neutral destination adapter interface."""

from __future__ import annotations

from abc import ABC, abstractmethod

from ielts_ai_coach.exporting.contracts import FeedbackExportRecord


class ExportAdapter(ABC):
    """Render or validate one shared feedback export record."""

    def validate(self, record: FeedbackExportRecord) -> None:
        """Validate through the strict contract boundary."""

        FeedbackExportRecord.model_validate(record)

    @abstractmethod
    def preview(self, record: FeedbackExportRecord) -> str:
        """Return a deterministic destination preview."""
