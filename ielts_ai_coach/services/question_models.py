"""Immutable Reading bank model objects kept separate from loader validation."""

from __future__ import annotations

from dataclasses import dataclass
import re

from ielts_ai_coach.services.review_content import QuestionReview, VocabularyItem


@dataclass(frozen=True)
class ReadingSection:
    """One labelled section of an original academic reading passage."""

    label: str
    text: str


@dataclass(frozen=True)
class ReadingQuestion:
    """One deterministically scored question with review evidence."""

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
        """Return the reviewed Chinese translation of the evidence sentence."""

        return self.review.evidence_translation_zh

    @property
    def tested_skill(self) -> str:
        """Return the IELTS skill assessed by this question."""

        return self.review.tested_skill

    @property
    def common_mistake_zh(self) -> str:
        """Return the Chinese warning for a common error pattern."""

        return self.review.common_mistake_zh

    @property
    def evidence_text(self) -> str:
        """Return the traceable English source evidence."""

        return self.review.evidence_text

    @property
    def synonym_pairs(self) -> tuple[tuple[str, str], ...]:
        """Return question-to-evidence paraphrase pairs."""

        return self.review.synonym_pairs


@dataclass(frozen=True)
class ReadingPassage:
    """One versioned original passage and its complete question set."""

    passage_id: str
    version: str
    title: str
    recommended_minutes: int
    sections: tuple[ReadingSection, ...]
    questions: tuple[ReadingQuestion, ...]
    vocabulary_items: tuple[VocabularyItem, ...]
    topic: str
    source_type: str
    source_name: str
    copyright_notice: str
    is_official_ielts_content: bool

    @property
    def word_count(self) -> int:
        """Return an English word count for source-quality checks."""

        text = " ".join(section.text for section in self.sections)
        return len(re.findall(r"\b[A-Za-z]+(?:[-'][A-Za-z]+)*\b", text))


@dataclass(frozen=True)
class ReadingBank:
    """A validated immutable collection of original reading passages."""

    bank_id: str
    version: str
    passages: tuple[ReadingPassage, ...]
