"""Tests for deterministic Obsidian Markdown rendering."""

from __future__ import annotations

import hashlib

from tests.exporting.test_contracts import _record
from tests.exporting.test_transform_writing import _source

from ielts_ai_coach.exporting.enums import SourceEntity
from ielts_ai_coach.exporting.obsidian_renderer import (
    ObsidianMarkdownAdapter,
    parse_source_key,
)
from ielts_ai_coach.exporting.transform import transform_writing


def test_renderer_uses_fixed_short_yaml_and_true_boolean() -> None:
    markdown = ObsidianMarkdownAdapter().preview(_record())

    expected_frontmatter = """---
schema_version: 1
type: ai-coach-feedback
source_system: ielts-ai-coach
source_entity: task_question_attempt
source_record_id: 7
session_date: 2026-07-19
generated_at: 2026-07-19T02:30:00Z
coach_version:
exporter_version: 1.0.0
skill: reading
feedback_method: deterministic
provider:
model_name:
feedback_status: generated
source_note:
test: true
tags:
  - ielts
  - ai-coach-feedback
---"""
    assert markdown.startswith(expected_frontmatter)
    frontmatter = markdown.split("---", 2)[1]
    assert "overall_summary" not in frontmatter
    assert "weaknesses" not in frontmatter
    assert "recommendations" not in frontmatter
    assert "exported_at" not in markdown
    assert "C:\\" not in markdown


def test_renderer_outputs_required_reading_sections_without_answers() -> None:
    markdown = ObsidianMarkdownAdapter().preview(_record())

    for heading in (
        "# IELTS AI Coach Feedback",
        "## Overall Summary",
        "## Weaknesses",
        "## Recommendations",
        "## Detailed Feedback",
        "## Personal Notes",
    ):
        assert heading in markdown
    assert "### Question r1-q2" in markdown
    assert "- Result: Incorrect" in markdown
    assert "user_answer" not in markdown
    assert "correct_answer" not in markdown


def test_writing_renderer_includes_strengths_and_rewrite_not_essay() -> None:
    markdown = ObsidianMarkdownAdapter().preview(
        transform_writing(_source())
    )

    assert "## Strengths" in markdown
    assert "- Clear position" in markdown
    assert "### Rewrite Example" in markdown
    assert "A clearer paragraph" in markdown
    assert "essay_content" not in markdown
    assert "Private full essay" not in markdown


def test_renderer_is_byte_deterministic_and_source_key_is_parseable() -> None:
    adapter = ObsidianMarkdownAdapter()
    first = adapter.preview(_record())
    second = adapter.preview(_record())

    assert first.encode("utf-8") == second.encode("utf-8")
    assert hashlib.sha256(first.encode()).hexdigest() == hashlib.sha256(
        second.encode()
    ).hexdigest()
    assert parse_source_key(first) == (
        SourceEntity.TASK_QUESTION_ATTEMPT,
        7,
    )
