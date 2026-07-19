"""Inactive future Feishu adapter boundary with no network behavior."""

from __future__ import annotations

from ielts_ai_coach.exporting.adapters.base import ExportAdapter
from ielts_ai_coach.exporting.contracts import FeedbackExportRecord
from ielts_ai_coach.exporting.errors import UnsupportedAdapterError


class FeishuAdapterStub(ExportAdapter):
    """Reject all destination operations until separately approved."""

    def preview(self, record: FeedbackExportRecord) -> str:
        """Reject preview because Feishu is intentionally unavailable."""

        self.validate(record)
        raise UnsupportedAdapterError("feishu_not_configured")

    def apply(self, record: FeedbackExportRecord) -> None:
        """Reject apply without reading credentials or using the network."""

        self.validate(record)
        raise UnsupportedAdapterError("feishu_not_configured")
