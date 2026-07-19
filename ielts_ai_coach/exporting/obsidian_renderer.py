"""Deterministic fixed-schema Obsidian Markdown rendering."""

from __future__ import annotations

from datetime import datetime, timezone
import json
import re

from ielts_ai_coach.exporting.adapters.base import ExportAdapter
from ielts_ai_coach.exporting.contracts import FeedbackExportRecord
from ielts_ai_coach.exporting.enums import SourceEntity


_SIMPLE_YAML = re.compile(r"^[A-Za-z0-9._/-]+$")


def _yaml_text(value: str | None) -> str:
    """Serialize one controlled optional YAML scalar."""

    if value is None or value == "":
        return ""
    if _SIMPLE_YAML.fullmatch(value):
        return value
    return json.dumps(value, ensure_ascii=False)


def _timestamp(value: datetime) -> str:
    """Normalize a timestamp to canonical UTC ISO 8601."""

    return value.astimezone(timezone.utc).isoformat(timespec="seconds").replace(
        "+00:00", "Z"
    )


def _yaml_field(name: str, value: str | None) -> str:
    """Render an optional scalar without trailing whitespace."""

    serialized = _yaml_text(value)
    return f"{name}: {serialized}" if serialized else f"{name}:"


def _line(value: str) -> str:
    """Keep generated bullet values on one deterministic line."""

    return " ".join(value.split())


def _frontmatter(record: FeedbackExportRecord) -> list[str]:
    """Return fixed-order short YAML frontmatter lines."""

    return [
        "---",
        f"schema_version: {record.schema_version}",
        f"type: {record.type}",
        f"source_system: {record.source_system}",
        f"source_entity: {record.source_entity.value}",
        f"source_record_id: {record.source_record_id}",
        f"session_date: {record.session_date.isoformat()}",
        f"generated_at: {_timestamp(record.generated_at)}",
        _yaml_field("coach_version", record.coach_version),
        f"exporter_version: {record.exporter_version}",
        f"skill: {record.skill.value}",
        f"feedback_method: {record.feedback_method.value}",
        _yaml_field("provider", record.provider),
        _yaml_field("model_name", record.model_name),
        f"feedback_status: {record.feedback_status.value}",
        _yaml_field("source_note", record.source_note),
        f"test: {'true' if record.test else 'false'}",
        "tags:",
        *[f"  - {_yaml_text(tag)}" for tag in record.tags],
        "---",
    ]


def _bullets(heading: str, values: tuple[str, ...]) -> list[str]:
    """Render one optional bullet section."""

    lines = [f"## {heading}", ""]
    lines.extend(f"- {_line(value)}" for value in values)
    return lines


class ObsidianMarkdownAdapter(ExportAdapter):
    """Render the canonical AI Feedback Markdown format."""

    def preview(self, record: FeedbackExportRecord) -> str:
        self.validate(record)
        lines = [
            *_frontmatter(record),
            "",
            "# IELTS AI Coach Feedback",
            "",
            *_bullets("Overall Summary", record.overall_summary),
            "",
        ]
        if record.strengths:
            lines.extend([*_bullets("Strengths", record.strengths), ""])
        lines.extend(
            [
                *_bullets("Weaknesses", record.weaknesses),
                "",
                *_bullets("Recommendations", record.recommendations),
                "",
                "## Detailed Feedback",
                "",
            ]
        )
        for detail in record.detailed_feedback:
            lines.extend(
                [
                    f"### Question {_line(detail.question_id)}",
                    "",
                    f"- Question Type: {_line(detail.question_type)}",
                    f"- Result: {detail.result.title()}",
                    f"- Explanation: {_line(detail.explanation)}",
                    f"- Evidence: {_line(detail.evidence)}",
                    "",
                ]
            )
        if record.rewrite_example:
            lines.extend(
                [
                    "### Rewrite Example",
                    "",
                    _line(record.rewrite_example),
                    "",
                ]
            )
        if not record.detailed_feedback and not record.rewrite_example:
            lines.extend(["- No additional detail.", ""])
        lines.extend(["## Personal Notes", "", ""])
        return "\n".join(lines)


def parse_source_key(
    markdown: str,
) -> tuple[SourceEntity, int] | None:
    """Read only the controlled source key from top-level frontmatter."""

    if not markdown.startswith("---\n"):
        return None
    try:
        frontmatter = markdown.split("---", 2)[1]
    except IndexError:
        return None
    entity_match = re.search(
        r"^source_entity: ([a-z_]+)$", frontmatter, re.MULTILINE
    )
    id_match = re.search(
        r"^source_record_id: ([1-9][0-9]*)$", frontmatter, re.MULTILINE
    )
    if not entity_match or not id_match:
        return None
    try:
        return SourceEntity(entity_match.group(1)), int(id_match.group(1))
    except ValueError:
        return None
