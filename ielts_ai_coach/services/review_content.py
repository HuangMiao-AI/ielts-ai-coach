"""Static Chinese-first review contracts shared by Reading and Listening."""

from __future__ import annotations

from dataclasses import dataclass
import re

from ielts_ai_coach.services.review_content_listening import (
    LISTENING_REVIEW_SEEDS,
    LISTENING_VOCABULARY_SEEDS,
)
from ielts_ai_coach.services.review_content_reading import (
    READING_REVIEW_SEEDS,
    READING_VOCABULARY_SEEDS,
)


@dataclass(frozen=True)
class VocabularyItem:
    """One bilingual lexical item traced to current source material."""

    word_or_phrase: str
    pronunciation: str
    part_of_speech: str
    meaning_zh: str
    meaning_en: str
    source_context: str
    synonym_or_paraphrase: str
    ielts_note_zh: str


@dataclass(frozen=True)
class QuestionReview:
    """Chinese-first explanation connected to the exact source evidence."""

    explanation_zh: str
    explanation_en_optional: str
    evidence_text: str
    evidence_translation_zh: str
    tested_skill: str
    common_mistake_zh: str
    synonym_pairs: tuple[tuple[str, str], ...]


_TYPE_SKILLS = {
    "multiple_choice": "细节定位、因果关系与同义替换",
    "form_completion": "信息捕捉、拼写与格式核对",
    "note_completion": "数字、时间与关键词听辨",
    "true_false_not_given": "判断原文的支持、矛盾与信息缺失",
    "matching_heading": "概括段落主旨并排除局部细节",
}
_TYPE_MISTAKES = {
    "multiple_choice": "不要只看选项中的熟词；要确认选项完整保留了定位句的范围、因果或比较关系。",
    "form_completion": "填空题要按原文顺序记录信息，并复查专有名词的拼写、大小写和单复数。",
    "note_completion": "听到数字或时间后先确认单位与上下文，避免把相邻信息当作答案。",
    "true_false_not_given": "True 需要完整支持，False 需要明确矛盾；原文没有给出比较、数量或时间信息才选 Not Given。",
    "matching_heading": "标题要覆盖整段的中心论点，不能因为某个例子或细节出现次数多就误选。",
}


def _seed_for(question_id: str) -> tuple[str, str]:
    """Return the reviewed Chinese evidence and reason for one stable item."""

    try:
        return READING_REVIEW_SEEDS[question_id]
    except KeyError:
        try:
            return LISTENING_REVIEW_SEEDS[question_id]
        except KeyError as error:
            raise ValueError("missing_review_content") from error


def build_question_review(
    *,
    question_id: str,
    question_type: str,
    question: str,
    correct_answer: str,
    explanation: str,
    evidence: str,
    source_text: str,
) -> QuestionReview:
    """Build a fully static bilingual review for one bank question."""

    evidence_zh, reason_zh = _seed_for(question_id)
    skill = _TYPE_SKILLS.get(question_type, "定位信息并核对题干要求")
    mistake = _TYPE_MISTAKES.get(
        question_type,
        "先回到定位句核对信息范围，再决定答案。",
    )
    return QuestionReview(
        explanation_zh=f"正确答案是「{correct_answer}」。{reason_zh}",
        explanation_en_optional=explanation,
        evidence_text=_source_evidence(source_text, evidence),
        evidence_translation_zh=evidence_zh,
        tested_skill=skill,
        common_mistake_zh=mistake,
        synonym_pairs=((question, evidence),),
    )


def build_vocabulary_items(
    *,
    source_id: str,
    source_text: str,
) -> tuple[VocabularyItem, ...]:
    """Attach eight source-backed bilingual lexical items to one source unit."""

    seeds = READING_VOCABULARY_SEEDS.get(
        source_id,
        LISTENING_VOCABULARY_SEEDS.get(source_id),
    )
    if seeds is None:
        raise ValueError("missing_vocabulary_content")
    items = []
    for word, pronunciation, part, zh, meaning, synonym, note in seeds:
        context = _source_context(source_text, word)
        items.append(
            VocabularyItem(
                word_or_phrase=word,
                pronunciation=pronunciation,
                part_of_speech=part,
                meaning_zh=zh,
                meaning_en=meaning,
                source_context=context,
                synonym_or_paraphrase=synonym,
                ielts_note_zh=note,
            )
        )
    return tuple(items)


def _source_context(source_text: str, word: str) -> str:
    """Return the source sentence containing a reviewed lexical item."""

    for sentence in re.split(r"(?<=[.!?])\s+", source_text):
        if _normalise_search(word) in _normalise_search(sentence):
            return sentence.strip()
    raise ValueError("vocabulary_not_in_source")


def _source_evidence(source_text: str, evidence: str) -> str:
    """Choose the closest full source sentence for an old review excerpt."""

    sentences = [
        sentence.strip()
        for sentence in re.split(r"(?<=[.!?])\s+", source_text)
        if sentence.strip()
    ]
    if evidence in source_text:
        return evidence
    terms = {
        term.casefold()
        for term in re.findall(r"[A-Za-z]+(?:[-'][A-Za-z]+)*|\d+", evidence)
        if len(term) > 2
    }
    if not sentences or not terms:
        raise ValueError("missing_source_evidence")
    best = max(
        sentences,
        key=lambda sentence: len(
            terms
            & {
                term.casefold()
                for term in re.findall(
                    r"[A-Za-z]+(?:[-'][A-Za-z]+)*|\d+",
                    sentence,
                )
            }
        ),
    )
    if not terms & {
        term.casefold()
        for term in re.findall(r"[A-Za-z]+(?:[-'][A-Za-z]+)*|\d+", best)
    }:
        raise ValueError("missing_source_evidence")
    return best


def _normalise_search(value: str) -> str:
    """Normalise whitespace and hyphens for source-context lookups."""

    return re.sub(r"[\s-]+", " ", value.casefold()).strip()
