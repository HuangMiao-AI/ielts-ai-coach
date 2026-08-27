"""Pure, session-only rules for the IELTS Training Arena."""

from __future__ import annotations

from dataclasses import dataclass
from functools import cached_property, lru_cache
import json
from pathlib import Path
import random
from typing import Any


BANK_PATH = (
    Path(__file__).resolve().parent.parent
    / "content"
    / "question_banks"
    / "training_arena_v1.json"
)
QUESTION_TYPES = {"synonym", "word_form"}
ROUND_SIZE = 5


@dataclass(frozen=True)
class ArenaQuestion:
    """One locally authored four-option vocabulary question."""

    question_id: str
    question_type: str
    prompt: str
    instruction: str
    options: tuple[str, ...]
    correct_answer: str
    explanation_en: str
    explanation_zh: str
    focus_vocabulary: str


@dataclass(frozen=True)
class ArenaBank:
    """Validated immutable local question collection."""

    bank_id: str
    version: str
    questions: tuple[ArenaQuestion, ...]

    @cached_property
    def by_id(self) -> dict[str, ArenaQuestion]:
        """Index questions by their stable identifier."""

        return {question.question_id: question for question in self.questions}


@dataclass(frozen=True)
class ArenaRound:
    """Serializable in-memory progress for one five-question round."""

    question_ids: tuple[str, ...]
    current_index: int = 0
    answers: tuple[str, ...] = ()
    correct_count: int = 0
    combo: int = 0
    completed: bool = False
    score_recorded: bool = False

    @property
    def score(self) -> int:
        """Return ten points for every correct answer."""

        return self.correct_count * 10

    @property
    def awaiting_advance(self) -> bool:
        """Return whether feedback is locked before moving on."""

        return not self.completed and len(self.answers) == self.current_index + 1


@dataclass(frozen=True)
class ArenaSummary:
    """Final metrics shown after a round."""

    correct_count: int
    total_questions: int
    accuracy: float
    score: int
    max_score: int
    focus_vocabulary: tuple[str, ...]


def arena_round_key(user_id: int) -> str:
    """Return a session-state key isolated to one authenticated user."""

    if user_id <= 0:
        raise ValueError("invalid_user")
    return f"training_arena_round_{user_id}"


def arena_session_score_key(user_id: int) -> str:
    """Return the participant-scoped current-session score key."""

    if user_id <= 0:
        raise ValueError("invalid_user")
    return f"training_arena_session_score_{user_id}"


def arena_session_score(store: dict[str, object], user_id: int) -> int:
    """Read the verified score accumulated in the current session."""

    value = store.get(arena_session_score_key(user_id), 0)
    return value if isinstance(value, int) and value >= 0 else 0


def record_completed_round_score(
    store: dict[str, object],
    user_id: int,
    round_state: ArenaRound,
) -> ArenaRound:
    """Add one completed round exactly once and mark it as recorded."""

    if not round_state.completed:
        raise ValueError("round_not_completed")
    if round_state.score_recorded:
        return round_state
    store[arena_session_score_key(user_id)] = (
        arena_session_score(store, user_id) + round_state.score
    )
    return ArenaRound(
        question_ids=round_state.question_ids,
        current_index=round_state.current_index,
        answers=round_state.answers,
        correct_count=round_state.correct_count,
        combo=round_state.combo,
        completed=True,
        score_recorded=True,
    )


def _required_text(payload: dict[str, Any], field: str) -> str:
    """Read one required non-empty text value."""

    value = payload.get(field)
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"invalid_{field}")
    return value.strip()


@lru_cache(maxsize=1)
def load_training_arena_bank(path: Path | None = None) -> ArenaBank:
    """Load the project-original static bank without database access."""

    payload = json.loads((path or BANK_PATH).read_text(encoding="utf-8"))
    raw_questions = payload.get("questions") if isinstance(payload, dict) else None
    if not isinstance(raw_questions, list):
        raise ValueError("invalid_bank")
    questions: list[ArenaQuestion] = []
    for item in raw_questions:
        if not isinstance(item, dict):
            raise ValueError("invalid_question")
        question_type = _required_text(item, "question_type")
        raw_options = item.get("options")
        if question_type not in QUESTION_TYPES or not isinstance(raw_options, list):
            raise ValueError("invalid_question")
        options = tuple(str(option).strip() for option in raw_options)
        answer = _required_text(item, "correct_answer")
        if len(options) != len(set(options)) or len(options) != 4 or answer not in options:
            raise ValueError("invalid_options")
        questions.append(
            ArenaQuestion(
                question_id=_required_text(item, "question_id"),
                question_type=question_type,
                prompt=_required_text(item, "prompt"),
                instruction=_required_text(item, "instruction"),
                options=options,
                correct_answer=answer,
                explanation_en=_required_text(item, "explanation_en"),
                explanation_zh=_required_text(item, "explanation_zh"),
                focus_vocabulary=_required_text(item, "focus_vocabulary"),
            )
        )
    ids = [question.question_id for question in questions]
    counts = {
        kind: sum(question.question_type == kind for question in questions)
        for kind in QUESTION_TYPES
    }
    if len(ids) != len(set(ids)) or any(counts[kind] < 20 for kind in QUESTION_TYPES):
        raise ValueError("invalid_bank_coverage")
    return ArenaBank(
        bank_id=_required_text(payload, "bank_id"),
        version=_required_text(payload, "version"),
        questions=tuple(questions),
    )


def start_arena_round(
    bank: ArenaBank,
    *,
    rng: random.Random | None = None,
) -> ArenaRound:
    """Create a fresh mixed five-question round."""

    chooser = rng or random.SystemRandom()
    synonyms = [q.question_id for q in bank.questions if q.question_type == "synonym"]
    word_forms = [q.question_id for q in bank.questions if q.question_type == "word_form"]
    selected = [chooser.choice(synonyms), chooser.choice(word_forms)]
    remaining = [q.question_id for q in bank.questions if q.question_id not in selected]
    selected.extend(chooser.sample(remaining, ROUND_SIZE - len(selected)))
    chooser.shuffle(selected)
    return ArenaRound(question_ids=tuple(selected))


def answer_arena_question(
    round_state: ArenaRound,
    question: ArenaQuestion,
    selected_answer: str,
) -> ArenaRound:
    """Lock one answer and update score/combo once."""

    if round_state.completed:
        raise ValueError("round_completed")
    if round_state.awaiting_advance:
        raise ValueError("question_already_answered")
    if question.question_id != round_state.question_ids[round_state.current_index]:
        raise ValueError("wrong_question")
    if selected_answer not in question.options:
        raise ValueError("invalid_answer")
    correct = selected_answer == question.correct_answer
    return ArenaRound(
        question_ids=round_state.question_ids,
        current_index=round_state.current_index,
        answers=(*round_state.answers, selected_answer),
        correct_count=round_state.correct_count + int(correct),
        combo=round_state.combo + 1 if correct else 0,
        score_recorded=round_state.score_recorded,
    )


def advance_arena_round(round_state: ArenaRound) -> ArenaRound:
    """Move past feedback, completing after the fifth locked answer."""

    if not round_state.awaiting_advance:
        raise ValueError("answer_required")
    is_last = round_state.current_index == len(round_state.question_ids) - 1
    return ArenaRound(
        question_ids=round_state.question_ids,
        current_index=round_state.current_index if is_last else round_state.current_index + 1,
        answers=round_state.answers,
        correct_count=round_state.correct_count,
        combo=round_state.combo,
        completed=is_last,
        score_recorded=round_state.score_recorded,
    )


def build_arena_summary(round_state: ArenaRound, bank: ArenaBank) -> ArenaSummary:
    """Build final metrics and deduplicated review vocabulary."""

    if not round_state.completed:
        raise ValueError("round_not_completed")
    focus = tuple(
        dict.fromkeys(
            bank.by_id[question_id].focus_vocabulary
            for question_id, answer in zip(round_state.question_ids, round_state.answers)
            if answer != bank.by_id[question_id].correct_answer
        )
    )
    if not focus:
        focus = tuple(
            dict.fromkeys(
                bank.by_id[question_id].focus_vocabulary
                for question_id in round_state.question_ids
            )
        )[:3]
    return ArenaSummary(
        correct_count=round_state.correct_count,
        total_questions=len(round_state.question_ids),
        accuracy=round_state.correct_count / len(round_state.question_ids),
        score=round_state.score,
        max_score=len(round_state.question_ids) * 10,
        focus_vocabulary=focus,
    )
