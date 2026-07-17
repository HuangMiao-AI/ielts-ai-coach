"""Pure deterministic rules for seven-day IELTS plans."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date, timedelta

from ielts_ai_coach.services.scoring import SUBJECTS, analyze_scores
from ielts_ai_coach.services.task_content import serialize_task_content
from ielts_ai_coach.services.task_templates import build_task_content


PHASE_LABELS = {
    "foundation": "基础能力阶段",
    "targeted": "专项提高阶段",
    "exam": "限时训练与模拟阶段",
}
PHASE_TASK_TYPES = {
    "foundation": "基础训练",
    "targeted": "专项训练",
    "exam": "限时模拟",
}
class PlanGenerationError(ValueError):
    """Raised when required data cannot produce a valid study plan."""


@dataclass(frozen=True)
class TaskBlueprint:
    """A deterministic task before database persistence."""

    task_date: date
    subject: str
    task_type: str
    task_title: str
    objective: str
    material: str
    instructions: tuple[str, ...]
    completion_criteria: str
    description: str
    planned_minutes: int
    difficulty: str
    expected_output: str
    priority: int


@dataclass(frozen=True)
class PlanBlueprint:
    """A complete deterministic seven-day plan."""

    start_date: date
    end_date: date
    phase: str
    tasks: tuple[TaskBlueprint, ...]


def determine_exam_phase(exam_date: date, today: date | None = None) -> str:
    """Return the approved phase from days remaining until the exam."""

    active_date = today or date.today()
    days_remaining = (exam_date - active_date).days
    if days_remaining < 0:
        raise PlanGenerationError("exam_in_past")
    if days_remaining > 90:
        return "foundation"
    if days_remaining >= 31:
        return "targeted"
    return "exam"


def _task_count(daily_minutes: int, completion_rate: float) -> int:
    """Choose a manageable deterministic task count."""

    if daily_minutes < 45:
        count = 2
    elif daily_minutes < 150:
        count = 3
    else:
        count = 4
    return max(2, count - 1) if completion_rate < 0.5 else count


def _subject_weights(
    scores: dict[str, float],
    target_overall: float,
    weakest_subjects: tuple[str, ...],
) -> dict[str, float]:
    """Calculate section weights from gaps and weaknesses."""

    return {
        subject: (
            1.0
            + max(0.0, target_overall - scores[subject])
            + (2.0 if subject in weakest_subjects else 0.0)
        )
        for subject in SUBJECTS
    }


def _select_subjects(
    weights: dict[str, float],
    weakest_subjects: tuple[str, ...],
    count: int,
    day_offset: int,
) -> list[str]:
    """Select unique daily subjects while rotating tied priorities."""

    subject_order = {subject: index for index, subject in enumerate(SUBJECTS)}
    ranked = sorted(
        SUBJECTS,
        key=lambda subject: (-weights[subject], subject_order[subject]),
    )
    weakest = [subject for subject in ranked if subject in weakest_subjects]
    if weakest:
        rotation = day_offset % len(weakest)
        weakest = weakest[rotation:] + weakest[:rotation]

    selected: list[str] = []
    rotated_ranked = ranked[day_offset % 4 :] + ranked[: day_offset % 4]
    for subject in weakest + rotated_ranked:
        if subject not in selected:
            selected.append(subject)
        if len(selected) == count:
            break
    return selected


def _allocate_minutes(
    total_minutes: int,
    subjects: list[str],
    weights: dict[str, float],
) -> list[int]:
    """Allocate every available minute using largest remainders."""

    total_weight = sum(weights[subject] for subject in subjects)
    raw_values = [
        total_minutes * weights[subject] / total_weight for subject in subjects
    ]
    allocated = [int(value) for value in raw_values]
    remainder_order = sorted(
        range(len(subjects)),
        key=lambda index: raw_values[index] - allocated[index],
        reverse=True,
    )
    for index in remainder_order[: total_minutes - sum(allocated)]:
        allocated[index] += 1
    return allocated


def build_plan_blueprint(
    *,
    scores: dict[str, float],
    target_overall: float,
    exam_date: date,
    daily_minutes: int,
    completion_rate: float = 1.0,
    start_date: date | None = None,
) -> PlanBlueprint:
    """Build a complete seven-day plan without database or AI access."""

    if not 15 <= daily_minutes <= 480:
        raise PlanGenerationError("invalid_minutes")
    first_date = start_date or date.today()
    phase = determine_exam_phase(exam_date, first_date)
    diagnosis = analyze_scores(scores, target_overall)
    weights = _subject_weights(scores, target_overall, diagnosis.lowest_subjects)
    count = _task_count(daily_minutes, completion_rate)
    tasks: list[TaskBlueprint] = []

    for day_offset in range(7):
        task_date = first_date + timedelta(days=day_offset)
        subjects = _select_subjects(
            weights, diagnosis.lowest_subjects, count, day_offset
        )
        minutes = _allocate_minutes(daily_minutes, subjects, weights)
        for priority, (subject, task_minutes) in enumerate(
            zip(subjects, minutes), start=1
        ):
            content = build_task_content(
                subject=subject,
                phase=phase,
                day_offset=day_offset,
                planned_minutes=task_minutes,
            )
            tasks.append(
                TaskBlueprint(
                    task_date=task_date,
                    subject=subject,
                    task_type=PHASE_TASK_TYPES[phase],
                    task_title=content.task_title,
                    objective=content.objective,
                    material=content.material,
                    instructions=content.instructions,
                    completion_criteria=content.completion_criteria,
                    description=serialize_task_content(content),
                    planned_minutes=task_minutes,
                    difficulty=content.difficulty,
                    expected_output=content.expected_output,
                    priority=priority,
                )
            )

    return PlanBlueprint(
        start_date=first_date,
        end_date=first_date + timedelta(days=6),
        phase=phase,
        tasks=tuple(tasks),
    )
