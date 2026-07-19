# AI Learning Analytics V1 Design

## Status

The product scope and the Listening/Speaking evidence boundary were approved
in conversation on 2026-07-19. This written specification is pending final
review before implementation planning.

## Goal

Upgrade IELTS AI Coach from an exam workflow into a read-only personalized
learning analytics experience using existing user-owned records, deterministic
rules, and the local Mock AI provider.

## Baseline

- Source branch: `feature/ui-exam-pwa-v1`
- Feature branch: `feature/ai-learning-analytics-v1`
- Baseline commit: `e5f1886`
- Baseline verification: 160 pytest tests pass
- Database: unchanged 11-table SQLite schema
- UI: existing premium glass Home, desktop sidebar, and mobile bottom bar
- Protected workflows: Reading Exam, Writing, and Obsidian Exporter

## Hard Constraints

- Do not add a database table, column, migration, or other schema change.
- Do not write analytics results to the database.
- Do not modify real user records.
- Do not call a real AI API.
- Do not infer ability from plans, task completion, absent recordings, or
  absent text.
- Every repository read must be scoped by the authenticated `user_id`.
- Pages receive a resolved authenticated `User`, never a user-entered ID.
- Preserve all existing features and the 160-test baseline.
- Keep all student-facing UI in Simplified Chinese, except the exact required
  English data-availability messages.

## Considered Approaches

### A. One analytics service containing every rule

This minimizes file count but couples database aggregation, weakness rules,
recommendation scheduling, Mock explanation, and Home rendering. It would make
future provider work and rule testing unnecessarily fragile.

### B. Layered read-only analytics pipeline (selected)

Use one service per responsibility:

```text
user-scoped repositories
→ analytics.py
→ weakness_analyzer.py
→ recommendations.py
→ ai_analysis.py
→ Home Growth Dashboard
```

This preserves the existing repository boundary, keeps calculations pure where
possible, and lets tests verify evidence, rule thresholds, and recommendations
independently.

### C. Persisted analytics snapshots

Materialized analytics could reduce repeat computation but would require a new
schema, invalidation rules, and synchronization with Reading/Writing updates.
It is rejected for V1.

## Reusable Data

### Profile and scores

- `StudentProfile.target_overall`
- `StudentProfile.daily_study_minutes`
- `StudentProfile.exam_date`
- `ScoreRecord.listening`
- `ScoreRecord.reading`
- `ScoreRecord.writing`
- `ScoreRecord.speaking`
- `ScoreRecord.overall`
- `ScoreRecord.recorded_at`

The newest `ScoreRecord` is the current exam snapshot. Subject trends are
ordered from oldest to newest. The target gap is `target - latest overall`;
positive values mean the target has not been reached.

### Reading

- `TaskQuestionAttempt.score`
- `TaskQuestionAttempt.total_questions`
- `TaskQuestionAttempt.accuracy`
- `TaskQuestionAttempt.results_json`
- `TaskQuestionAttempt.submitted_at`

`results_json` already stores `question_type` and `is_correct` for every
question. Reading accuracy is weighted across questions, not averaged across
attempt percentages. Error counts are grouped by question type. A frequent
error is the highest-count incorrect type with at least two errors; equal
counts remain equal rather than receiving an invented ranking.

### Writing

- `WritingFeedback.task_response_or_achievement`
- `WritingFeedback.coherence_and_cohesion`
- `WritingFeedback.lexical_resource`
- `WritingFeedback.grammatical_range_and_accuracy`
- `WritingFeedback.estimated_overall`
- `WritingFeedback.created_at`

The latest completed feedback supplies the four current dimension values.
Chronological values form the dimension trends. Essay content and prompts are
not required by analytics and must not enter the analytics result.

### Study behavior

- `StudyLog.study_date`
- `StudyLog.minutes`
- `PlanTask.subject`
- `PlanTask.task_type`

Study logs support streak and recent time totals. They can size future study
actions but cannot be used as evidence that a skill is strong or weak.

## Analytics Result

`ielts_ai_coach/services/analytics.py` owns immutable dataclasses:

- `ScorePoint`: date and band
- `SkillScoreTrend`: skill, latest band, chronological points, detailed status
- `ReadingAnalytics`: attempts, correct/total, accuracy, error counts, frequent
  error types
- `WritingAnalytics`: feedback count, latest four dimensions, dimension trends
- `LearningBehavior`: streak, recent minutes, configured daily minutes
- `AnalyticsResult`: current band, target band, target gap, overall trend,
  four skill trends, Reading, Writing, and learning behavior

`build_analytics_result(user_id, today, session_factory)` performs read-only
aggregation. Missing profile, score, Reading, Writing, or log data produces
explicit `None`, empty tuples, or zero counts. It never substitutes defaults
that look like measured student performance.

## Listening and Speaking Boundary

When at least one score record exists:

- expose the latest Listening or Speaking band;
- expose the chronological band trend;
- set the detailed status to exactly
  `No detailed practice analytics available`;
- do not generate granular weaknesses or skill claims.

When no score record exists:

- Listening status is exactly `No enough listening data`;
- Speaking status is exactly `No enough speaking data`;
- latest band is `None` and the trend is empty.

Plan tasks, completion counts, audio session state, notes, and absent transcripts
must never change these results.

## Weakness Analyzer

`ielts_ai_coach/services/weakness_analyzer.py` defines:

```text
Weakness(
    skill,
    weakness,
    severity,
    evidence,
    recommendation,
)
```

Allowed severity values are `low`, `medium`, and `high`.

Reading uses only submitted Reading evidence:

- accuracy below 50%: high;
- accuracy from 50% to below 60%: medium;
- accuracy from 60% to below 70%: low;
- accuracy of 70% or higher: no accuracy weakness.

The weakness name includes the highest-frequency question type when one exists.
Evidence reports counts and percentages, not answer text.

Writing compares each latest feedback dimension with the target band:

- gap of 1.5 bands or more: high;
- gap of 1.0 to below 1.5: medium;
- positive gap below 1.0: low;
- no positive gap: no weakness for that dimension.

Grammar uses the required weakness wording `Grammar improvement needed`.
Other dimensions use equally specific labels. Listening and Speaking never
produce weakness objects in V1 because no detailed practice evidence exists.

## Seven-Day Recommendation Engine

`ielts_ai_coach/services/recommendations.py` defines an immutable
`StudyRecommendation` containing day number, skill, activity, minutes, and
evidence link.

`build_seven_day_recommendations(analytics, weaknesses)`:

- returns exactly seven chronological day entries;
- allocates no more than the profile's configured daily minutes;
- prioritizes high, then medium, then low severity;
- maps Reading error types to concrete original-bank practice and review;
- maps each Writing dimension to a concrete Task 1/Task 2 review action;
- never recommends a specific Listening or Speaking weakness exercise based
  only on section scores;
- uses explicit baseline-data actions when Reading or Writing evidence is
  missing;
- uses maintenance and review actions when no measured weakness exists.

Recommendations are computed only for display. They do not replace or write to
`study_plans` or `plan_tasks`.

## Mock AI Explanation

`ielts_ai_coach/services/ai_analysis.py` accepts an `AnalyticsResult`, detected
weaknesses, recommendations, and an optional `AIProvider`.

- The default provider is `MockAIProvider`, never the configured provider
  factory.
- V1 rejects any provider whose `is_mock` is false with a safe
  `mock_provider_required` error.
- The prompt contains only derived bands, aggregate Reading/Writing evidence,
  and the top recommended action.
- It excludes essay content, answers, recordings, profile identity, and
  unrelated history.
- The returned explanation includes provider/model metadata and an explicit
  learning-reference disclaimer.

The provider-neutral signature leaves a future Qwen/OpenAI integration point,
but enabling a network provider requires a separately approved policy change.

## Home Growth Dashboard

The existing Home content remains available. A new `IELTS Growth Dashboard`
section adds:

1. Current Band
2. Target Band
3. Progress toward target
4. Weakness cards with severity and evidence
5. Recommended next actions
6. Learning streak
7. Mock AI explanation

Home calls the analytics service with `user.id` from the authenticated `User`.
No widget or query parameter accepts a user ID. Empty states remain factual.
The current glass components and navigation are reused.

At 375, 430, and 768 pixels:

- metric groups stack without horizontal overflow;
- weakness and recommendation cards become one column;
- text remains readable;
- primary actions retain 44-pixel touch targets;
- the 56-pixel mobile navigation and 88-pixel bottom content spacing remain.

## Repository Changes

No model changes are allowed. Existing repository methods are reused where
possible. A user-scoped read helper may be added only when no suitable method
exists, particularly for listing Writing feedback across a user's essays.
Every such query must include `WritingFeedback.user_id == user_id`.

Analytics services may deserialize existing Reading result snapshots after
obtaining attempts through `list_task_question_attempts(user_id=...)`.
SQL remains in repositories; business calculations remain in services.

## Error Handling

- Malformed historical Reading snapshots are skipped from detailed type
  aggregation but their persisted score/total can still contribute to overall
  Reading accuracy; the result records a safe data-warning code.
- Missing profile prevents target-gap and time-allocation claims.
- Missing scores produce the required Listening/Speaking empty messages.
- Missing Writing feedback produces no dimension weakness.
- An unsupported real provider is rejected before `generate()` can run.
- Home renders safe empty states rather than propagating missing-data errors.

## Test Strategy

Create `tests/analytics/` with behavior-focused tests:

- normal current score, target gap, and chronological trends;
- user with no score records;
- exact Listening/Speaking detailed-unavailable and no-data messages;
- Reading weighted accuracy, error-type counts, and frequent errors;
- latest Writing four-dimension analysis and trends;
- low/medium/high weakness thresholds;
- concrete seven-day recommendation generation and minute bounds;
- no Listening/Speaking weakness inference;
- strict user isolation across every data source;
- Mock-only AI explanation and rejection of non-Mock providers;
- Home loading with populated and empty analytics;
- 375/430/768 responsive CSS contract.

Tests use temporary SQLite databases and Mock/Fake providers. Each production
behavior follows a RED → GREEN → REFACTOR cycle. Final verification runs:

```powershell
.venv\Scripts\python.exe -m pytest
.venv\Scripts\python.exe -m compileall -q app.py ielts_ai_coach
.venv\Scripts\python.exe -m pip check
```

The Reading Exam, Writing, Exporter, authentication, and existing Home tests
remain part of the full suite.

## Acceptance Criteria

- Analytics is generated at request time without writes or schema changes.
- Current band, four trends, latest score, and target gap use only owned data.
- Reading and Writing analysis is evidence-backed.
- Listening/Speaking messages and inference boundaries are exact.
- Weakness severity is deterministic and traceable.
- Seven recommendations are concrete and bounded by configured study time.
- Home displays the Growth Dashboard without removing existing functions.
- No real AI provider can be called by V1 analytics.
- User isolation tests prove one user cannot affect another user's result.
- All new and existing tests, compileall, and pip check pass.
- Real databases remain unchanged and no code is pushed or deployed.
