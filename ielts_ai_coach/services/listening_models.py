"""Immutable Listening bank model objects separated from JSON validation."""

from __future__ import annotations

from dataclasses import dataclass

from ielts_ai_coach.services.review_content import QuestionReview, VocabularyItem


@dataclass(frozen=True)
class ListeningScriptTurn:
    """One voiced turn in an original Listening script."""

    speaker: str
    text: str
    pause_ms: int


@dataclass(frozen=True)
class ListeningQuestion:
    """One deterministically scored Listening question."""

    question_id: str
    question_type: str
    question: str
    options: tuple[str, ...]
    correct_answer: str
    explanation: str
    evidence: str
    review: QuestionReview

    @property
    def explanation_zh(self) -> str:
        """Return the Chinese-first explanation for this exact question."""

        return self.review.explanation_zh

    @property
    def evidence_translation_zh(self) -> str:
        """Return the reviewed Chinese translation of the listening evidence."""

        return self.review.evidence_translation_zh

    @property
    def tested_skill(self) -> str:
        """Return the assessed listening skill."""

        return self.review.tested_skill

    @property
    def common_mistake_zh(self) -> str:
        """Return the Chinese warning for a common listening error."""

        return self.review.common_mistake_zh

    @property
    def evidence_text(self) -> str:
        """Return the source-backed English evidence."""

        return self.review.evidence_text

    @property
    def synonym_pairs(self) -> tuple[tuple[str, str], ...]:
        """Return question-to-script paraphrase pairs."""

        return self.review.synonym_pairs


@dataclass(frozen=True)
class ListeningSection:
    """One scenario, script, and ordered question group."""

    section_id: str
    title: str
    scenario: str
    script: tuple[ListeningScriptTurn, ...]
    questions: tuple[ListeningQuestion, ...]
    vocabulary_items: tuple[VocabularyItem, ...]


@dataclass(frozen=True)
class ListeningTest:
    """One complete two-section original mini test."""

    test_id: str
    title: str
    audio_path: str
    estimated_minutes: int
    sections: tuple[ListeningSection, ...]

    @property
    def questions(self) -> tuple[ListeningQuestion, ...]:
        """Return all questions in playback order."""

        return tuple(question for section in self.sections for question in section.questions)


@dataclass(frozen=True)
class ListeningBank:
    """Immutable validated collection of Listening mini tests."""

    bank_id: str
    version: str
    source_type: str
    source_name: str
    copyright_notice: str
    is_official_ielts_content: bool
    tests: tuple[ListeningTest, ...]
