"""Source-quality contracts for the expanded original Reading catalog."""

from __future__ import annotations

from collections import Counter

from ielts_ai_coach.services.question_bank import (
    VALID_QUESTION_TYPES,
    load_reading_catalog,
)


def test_catalog_contains_eight_original_passages_and_77_questions() -> None:
    """The additive catalog must preserve v1 and add five complete passages."""

    passages = load_reading_catalog()
    question_ids = [
        question.question_id
        for passage in passages
        for question in passage.questions
    ]

    assert len(passages) == 8
    assert sum(len(passage.questions) for passage in passages) == 77
    assert len({passage.passage_id for passage in passages}) == 8
    assert len(question_ids) == len(set(question_ids))
    assert tuple(passage.passage_id for passage in passages[-5:]) == (
        "AR-V2-001",
        "AR-V2-002",
        "AR-V2-003",
        "AR-V2-004",
        "AR-V2-005",
    )


def test_every_v2_passage_meets_length_question_and_source_rules() -> None:
    """Each new passage must be substantial, complete, and clearly original."""

    passages = load_reading_catalog()[-5:]
    for passage in passages:
        assert 750 <= passage.word_count <= 950
        assert len(passage.questions) == 10
        assert {
            question.question_type for question in passage.questions
        } == VALID_QUESTION_TYPES
        assert passage.source_type == "project_original"
        assert passage.is_official_ielts_content is False
        assert "非官方" in passage.copyright_notice
        assert passage.topic

        type_counts = Counter(
            question.question_type for question in passage.questions
        )
        assert min(type_counts.values()) >= 3
        for question in passage.questions:
            assert question.correct_answer in question.options
            assert question.explanation
            assert question.evidence
