# AI Learning Analytics V1 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build a request-time, user-isolated IELTS analytics pipeline with deterministic weaknesses, seven-day recommendations, a Mock-only explanation, and a responsive Home Growth Dashboard.

**Architecture:** Existing user-scoped repositories provide score, profile, study-log, Reading-attempt, and Writing-feedback records. Focused services transform those records into immutable analytics, weaknesses, recommendations, and a Mock explanation; a separate view component renders the results without writing analytics data or changing the database schema.

**Tech Stack:** Python 3.12, Streamlit 1.59, SQLAlchemy 2.0, SQLite, pytest 8, existing `AIProvider` and `MockAIProvider`.

## Global Constraints

- Do not add or alter database tables, columns, indexes, migrations, or model metadata.
- Analytics results are computed only at request time and are never persisted.
- Do not modify real user records or use the default runtime database in tests.
- Every database query must require and filter by the authenticated `user_id`.
- Pages must use `user.id` from the authenticated `User`; no widget or query parameter may accept a user ID.
- Do not call a real AI API. Analytics defaults to `MockAIProvider` and rejects every provider with `is_mock == False` before `generate()`.
- Listening and Speaking use `ScoreRecord` only for latest band and trend. They never produce granular weakness claims.
- With score data, Listening and Speaking detail status is exactly `No detailed practice analytics available`.
- Without score data, the statuses are exactly `No enough listening data` and `No enough speaking data`.
- Preserve Reading Exam, Writing, authentication, Home navigation, and Obsidian Exporter behavior.
- Keep student-facing labels in Simplified Chinese except the three required English status messages.
- Every production behavior follows RED → GREEN → REFACTOR and receives focused pytest coverage.
- Each task ends in a local commit. Do not push, deploy, or access external accounts.

---

### Task 1: Read-only Analytics Service

**Files:**
- Create: `ielts_ai_coach/services/analytics.py`
- Modify: `ielts_ai_coach/database/writing_repository.py`
- Create: `tests/analytics/__init__.py`
- Create: `tests/analytics/helpers.py`
- Create: `tests/analytics/test_service.py`

**Interfaces:**
- Consumes: existing `get_profile`, `list_score_records`, `list_study_logs`, `list_task_question_attempts`, `deserialize_reading_score`, and a new user-scoped `list_user_writing_feedback`.
- Produces:
  - `ScorePoint(recorded_at: datetime, band: float)`
  - `SkillScoreAnalytics(skill: str, latest_band: float | None, trend: tuple[ScorePoint, ...], detail_status: str)`
  - `ReadingAnalytics(attempt_count: int, correct: int, total: int, accuracy: float | None, error_counts: tuple[tuple[str, int], ...], frequent_error_types: tuple[str, ...], warnings: tuple[str, ...])`
  - `WritingDimensionAnalytics(name: str, latest_band: float | None, trend: tuple[ScorePoint, ...])`
  - `WritingAnalytics(feedback_count: int, dimensions: tuple[WritingDimensionAnalytics, ...])`
  - `LearningBehavior(streak_days: int, recent_minutes: int, daily_study_minutes: int | None)`
  - `AnalyticsResult(current_band: float | None, target_band: float | None, target_gap: float | None, overall_trend: tuple[ScorePoint, ...], skills: tuple[SkillScoreAnalytics, ...], reading: ReadingAnalytics, writing: WritingAnalytics, behavior: LearningBehavior)`
  - `build_analytics_result(user_id: int, *, today: date | None = None, session_factory: sessionmaker[Session] | None = None) -> AnalyticsResult`

- [ ] **Step 1: Write failing analytics and isolation tests**

Create tests that seed two users in the temporary `session_factory` and assert:

```python
result = build_analytics_result(
    owner_id,
    today=date(2026, 7, 19),
    session_factory=session_factory,
)
assert result.current_band == 6.0
assert result.target_band == 7.0
assert result.target_gap == 1.0
assert [point.band for point in result.overall_trend] == [5.5, 6.0]
assert result.skill("listening").latest_band == 6.5
assert result.skill("speaking").detail_status == (
    "No detailed practice analytics available"
)
assert result.reading.accuracy == pytest.approx(0.6)
assert dict(result.reading.error_counts)["matching_heading"] == 3
assert result.writing.dimension("grammar").latest_band == 5.5
assert other_user_unique_band not in {
    point.band for point in result.overall_trend
}
```

Add an empty-user test:

```python
result = build_analytics_result(
    empty_user_id,
    today=date(2026, 7, 19),
    session_factory=session_factory,
)
assert result.current_band is None
assert result.target_gap is None
assert result.skill("listening").detail_status == "No enough listening data"
assert result.skill("speaking").detail_status == "No enough speaking data"
assert result.reading.accuracy is None
assert result.writing.feedback_count == 0
```

- [ ] **Step 2: Run the focused tests and verify RED**

Run:

```powershell
.venv\Scripts\python.exe -m pytest tests\analytics\test_service.py -q
```

Expected: collection fails because `ielts_ai_coach.services.analytics` and
`list_user_writing_feedback` do not exist.

- [ ] **Step 3: Add the user-scoped Writing-feedback read**

Add to `writing_repository.py`:

```python
def list_user_writing_feedback(
    session: Session,
    *,
    user_id: int,
    limit: int = 100,
) -> list[WritingFeedback]:
    statement = (
        select(WritingFeedback)
        .where(WritingFeedback.user_id == user_id)
        .order_by(WritingFeedback.created_at.desc(), WritingFeedback.id.desc())
        .limit(max(1, min(limit, 500)))
    )
    return list(session.scalars(statement))
```

- [ ] **Step 4: Implement immutable analytics aggregation**

Implement the declared dataclasses plus:

```python
LISTENING_DETAIL_UNAVAILABLE = "No detailed practice analytics available"
LISTENING_NO_DATA = "No enough listening data"
SPEAKING_NO_DATA = "No enough speaking data"
WRITING_DIMENSIONS = (
    ("task_achievement", "task_response_or_achievement"),
    ("coherence", "coherence_and_cohesion"),
    ("vocabulary", "lexical_resource"),
    ("grammar", "grammatical_range_and_accuracy"),
)
```

Within one read-only session:

1. Query every source with the supplied `user_id`.
2. Reverse newest-first score/feedback records before building trends.
3. Compute Reading accuracy as `sum(attempt.score) / sum(attempt.total_questions)`.
4. Deserialize each valid Reading snapshot and count incorrect `question_type`.
5. Record `invalid_reading_snapshot` for malformed snapshots without exposing raw payloads.
6. Count streak from distinct log dates ending today or yesterday.
7. Return `None` for absent measured values rather than fabricated defaults.

Add `AnalyticsResult.skill(name)` and `WritingAnalytics.dimension(name)` lookup
methods that raise `KeyError` for unsupported names.

- [ ] **Step 5: Verify GREEN and regression safety**

Run:

```powershell
.venv\Scripts\python.exe -m pytest tests\analytics\test_service.py tests\test_home.py tests\test_reading_page_flow.py tests\exporting -q
```

Expected: all selected tests pass.

- [ ] **Step 6: Commit Phase 1**

```powershell
git add ielts_ai_coach/services/analytics.py ielts_ai_coach/database/writing_repository.py tests/analytics
git commit -m "feat(analytics): add user-scoped learning analytics"
```

---

### Task 2: Deterministic Weakness Analyzer

**Files:**
- Create: `ielts_ai_coach/services/weakness_analyzer.py`
- Create: `tests/analytics/test_weaknesses.py`

**Interfaces:**
- Consumes: `AnalyticsResult` from Task 1.
- Produces:
  - `Weakness(skill: str, weakness: str, severity: Literal["low", "medium", "high"], evidence: str, recommendation: str)`
  - `analyze_weaknesses(analytics: AnalyticsResult) -> tuple[Weakness, ...]`

- [ ] **Step 1: Write threshold and no-inference tests**

Use dataclass fixtures to verify:

```python
assert reading_49.severity == "high"
assert reading_55.severity == "medium"
assert reading_65.severity == "low"
assert not reading_70_weaknesses
assert grammar_gap.weakness == "Grammar improvement needed"
assert grammar_gap.severity == "high"
assert all(
    item.skill not in {"listening", "speaking"}
    for item in analyze_weaknesses(analytics_with_low_section_scores)
)
```

Also assert evidence contains the measured percentage/count and that the
Reading weakness names the frequent question type when available.

- [ ] **Step 2: Run the focused tests and verify RED**

```powershell
.venv\Scripts\python.exe -m pytest tests\analytics\test_weaknesses.py -q
```

Expected: collection fails because `weakness_analyzer` does not exist.

- [ ] **Step 3: Implement deterministic severity rules**

Implement:

```python
Severity = Literal["low", "medium", "high"]

def _reading_severity(accuracy: float) -> Severity | None:
    if accuracy < 0.5:
        return "high"
    if accuracy < 0.6:
        return "medium"
    if accuracy < 0.7:
        return "low"
    return None

def _writing_severity(gap: float) -> Severity | None:
    if gap >= 1.5:
        return "high"
    if gap >= 1.0:
        return "medium"
    if gap > 0:
        return "low"
    return None
```

Create Reading weaknesses only from `analytics.reading`. Create Writing
weaknesses only from the latest four feedback dimensions and target band.
Sort results by severity rank `high`, `medium`, `low`, then skill and weakness.
Never inspect Listening/Speaking section gaps.

- [ ] **Step 4: Verify GREEN**

```powershell
.venv\Scripts\python.exe -m pytest tests\analytics\test_weaknesses.py tests\analytics\test_service.py -q
```

Expected: all tests pass.

- [ ] **Step 5: Commit Phase 2**

```powershell
git add ielts_ai_coach/services/weakness_analyzer.py tests/analytics/test_weaknesses.py
git commit -m "feat(analytics): detect evidence-backed weaknesses"
```

---

### Task 3: Seven-Day Recommendation Engine

**Files:**
- Create: `ielts_ai_coach/services/recommendations.py`
- Create: `tests/analytics/test_recommendations.py`

**Interfaces:**
- Consumes: `AnalyticsResult` and ordered `Weakness` values.
- Produces:
  - `StudyRecommendation(day: int, skill: str, activity: str, minutes: int | None, evidence: str)`
  - `build_seven_day_recommendations(analytics: AnalyticsResult, weaknesses: tuple[Weakness, ...]) -> tuple[StudyRecommendation, ...]`

- [ ] **Step 1: Write concrete-output tests**

Assert:

```python
items = build_seven_day_recommendations(analytics, weaknesses)
assert [item.day for item in items] == list(range(1, 8))
assert len(items) == 7
assert all(item.activity.strip() for item in items)
assert all(
    item.minutes is None or item.minutes <= analytics.behavior.daily_study_minutes
    for item in items
)
assert "Matching Heading" in items[0].activity
assert any("Task 2" in item.activity and "grammar" in item.activity.lower() for item in items)
assert not any(
    item.skill in {"listening", "speaking"}
    and "weakness" in item.evidence.lower()
    for item in items
)
```

Add missing-evidence tests that expect explicit baseline-data actions and
`minutes is None` when no profile daily time exists.

- [ ] **Step 2: Run focused tests and verify RED**

```powershell
.venv\Scripts\python.exe -m pytest tests\analytics\test_recommendations.py -q
```

Expected: collection fails because `recommendations` does not exist.

- [ ] **Step 3: Implement deterministic activity templates**

Use exact mappings:

```python
READING_ACTIVITIES = {
    "matching_heading": "完成 1 组原创 Reading Matching Heading，并逐题记录段落主旨与干扰项原因",
    "multiple_choice": "完成 1 组原创 Reading Multiple Choice，并标出定位词和同义替换",
    "true_false_not_given": "完成 1 组原创 Reading TFNG，并分别记录 False 与 Not Given 的证据边界",
    "general": "完成 1 篇原创 Academic Reading 限时练习并复盘全部错题",
}
WRITING_ACTIVITIES = {
    "task_achievement": "完成 1 份 Writing Task 2 提纲，检查立场、论点和例证是否完整回应题目",
    "coherence": "重写 1 个 Writing Task 2 主体段，明确主题句、论证顺序和衔接",
    "vocabulary": "整理 10 个 Writing Task 2 主题词组，并各写 1 个准确例句",
    "grammar": "复查 1 个 Writing Task 2 主体段的主谓一致、冠词、从句和标点",
}
```

Allocate a focused block of at most 60% of daily minutes, with a minimum of
15 minutes when daily time exists. Cycle through ordered weaknesses. When no
measured weakness exists, rotate concrete Reading baseline, Writing baseline,
error review, and progress-review activities. Recommendations never write
`StudyPlan` or `PlanTask`.

- [ ] **Step 4: Verify GREEN**

```powershell
.venv\Scripts\python.exe -m pytest tests\analytics\test_recommendations.py tests\analytics\test_weaknesses.py -q
```

Expected: all tests pass.

- [ ] **Step 5: Commit Phase 3**

```powershell
git add ielts_ai_coach/services/recommendations.py tests/analytics/test_recommendations.py
git commit -m "feat(analytics): generate seven-day study recommendations"
```

---

### Task 4: Mock-only AI Explanation Layer

**Files:**
- Create: `ielts_ai_coach/services/ai_analysis.py`
- Create: `tests/analytics/test_ai_analysis.py`

**Interfaces:**
- Consumes: `AnalyticsResult`, `Weakness`, `StudyRecommendation`, and `AIProvider`.
- Produces:
  - `AIAnalysisError(code: str)`
  - `AIAnalysisExplanation(content: str, provider: str, model_name: str, is_mock: bool)`
  - `explain_analytics(analytics: AnalyticsResult, weaknesses: tuple[Weakness, ...], recommendations: tuple[StudyRecommendation, ...], *, provider: AIProvider | None = None) -> AIAnalysisExplanation`

- [ ] **Step 1: Write Mock and network-rejection tests**

Verify:

```python
result = explain_analytics(analytics, weaknesses, recommendations)
assert result.provider == "mock"
assert result.is_mock is True
assert "Writing" in result.content or "写作" in result.content
assert AI_ANALYSIS_DISCLAIMER in result.content
```

Create a non-Mock provider whose `generate()` raises `AssertionError`; assert:

```python
with pytest.raises(AIAnalysisError, match="mock_provider_required"):
    explain_analytics(
        analytics,
        weaknesses,
        recommendations,
        provider=non_mock_provider,
    )
assert non_mock_provider.calls == 0
```

- [ ] **Step 2: Run focused tests and verify RED**

```powershell
.venv\Scripts\python.exe -m pytest tests\analytics\test_ai_analysis.py -q
```

Expected: collection fails because `ai_analysis` does not exist.

- [ ] **Step 3: Implement safe prompt and Mock-only guard**

Implement:

```python
AI_ANALYSIS_DISCLAIMER = "以上分析仅用于学习规划，不是官方IELTS评分或诊断。"

active_provider = provider or MockAIProvider()
if not active_provider.is_mock:
    raise AIAnalysisError("mock_provider_required")
```

Build a bounded user message from current/target bands, aggregate Reading and
Writing evidence, the top weakness, and the first recommendation. Do not
include username, essay content, prompts, Reading answers, recordings, or raw
JSON. Call `active_provider.generate(messages)` once, append the disclaimer
when absent, and return normalized provider metadata.

- [ ] **Step 4: Verify GREEN and provider regression**

```powershell
.venv\Scripts\python.exe -m pytest tests\analytics\test_ai_analysis.py tests\test_ai_provider.py tests\test_coaching.py tests\test_writing.py -q
```

Expected: all tests pass and no network provider is called.

- [ ] **Step 5: Commit Phase 4**

```powershell
git add ielts_ai_coach/services/ai_analysis.py tests/analytics/test_ai_analysis.py
git commit -m "feat(analytics): add mock-only learning explanation"
```

---

### Task 5: Home IELTS Growth Dashboard

**Files:**
- Create: `ielts_ai_coach/views/growth_dashboard.py`
- Modify: `ielts_ai_coach/views/dashboard.py`
- Modify: `ielts_ai_coach/ui/design_system.py`
- Create: `tests/analytics/test_home_growth_dashboard.py`
- Modify: `tests/test_navigation_responsive.py`

**Interfaces:**
- Consumes: Task 1–4 services and `user.id` from `render_dashboard(user, page_refs)`.
- Produces:
  - `render_growth_dashboard(user_id: int, *, session_factory: sessionmaker[Session] | None = None, today: date | None = None) -> None`

- [ ] **Step 1: Write failing Home behavior tests**

Use `AppTest` with a temporary database. Assert populated Home renders:

```python
labels = [metric.label for metric in app.metric]
assert "Current Band" in labels
assert "Target Band" in labels
assert "Progress" in labels
assert "Learning Streak" in labels
assert "IELTS Growth Dashboard" in rendered_text
assert "Weakness Cards" in rendered_text
assert "Recommended Next Actions" in rendered_text
assert "No detailed practice analytics available" in rendered_text
```

For an empty user, assert both required no-data messages render and no
exception occurs. Inspect `dashboard.py` to assert the only call is
`render_growth_dashboard(user.id)` and no input widget accepts `user_id`.

Add responsive contract assertions for `.growth-dashboard-grid` at 768 and
430 pixel media queries.

- [ ] **Step 2: Run Home tests and verify RED**

```powershell
.venv\Scripts\python.exe -m pytest tests\analytics\test_home_growth_dashboard.py tests\test_navigation_responsive.py -q
```

Expected: tests fail because the Growth Dashboard view and CSS do not exist.

- [ ] **Step 3: Implement the view component**

`render_growth_dashboard` must:

1. call `build_analytics_result(user_id, ...)`;
2. call `analyze_weaknesses`;
3. call `build_seven_day_recommendations`;
4. call `explain_analytics` without the configured provider factory;
5. render Current Band, Target Band, Progress, and Learning Streak;
6. render Listening/Speaking exact availability text;
7. render evidence-backed weakness cards or an honest empty state;
8. render the first three concrete next actions;
9. render the Mock explanation and disclaimer.

Progress is `min(1.0, current_band / target_band)` only when both values exist
and target is greater than zero; otherwise display `暂无`.

- [ ] **Step 4: Integrate without removing existing Home content**

Import and call:

```python
render_growth_dashboard(user.id)
```

immediately after `_render_core_entries(page_refs)` in `render_dashboard`.
Do not remove `_render_snapshot_overview`, profile guidance, tasks, scores,
weekly statistics, or AI quota.

Add CSS:

```css
.growth-dashboard-grid {
    display: grid;
    grid-template-columns: repeat(2, minmax(0, 1fr));
    gap: .8rem;
}
@media (max-width: 768px) {
    .growth-dashboard-grid { grid-template-columns: 1fr; }
}
@media (max-width: 430px) {
    .growth-dashboard-grid { gap: .65rem; }
}
```

Cards reuse `.glass-card`; no new visual system is introduced.

- [ ] **Step 5: Verify GREEN and existing Home behavior**

```powershell
.venv\Scripts\python.exe -m pytest tests\analytics\test_home_growth_dashboard.py tests\test_dashboard.py tests\test_home.py tests\test_navigation_responsive.py -q
```

Expected: all tests pass.

- [ ] **Step 6: Commit Phase 5**

```powershell
git add ielts_ai_coach/views/growth_dashboard.py ielts_ai_coach/views/dashboard.py ielts_ai_coach/ui/design_system.py tests/analytics/test_home_growth_dashboard.py tests/test_navigation_responsive.py
git commit -m "feat(home): add IELTS growth dashboard"
```

---

### Task 6: Full Regression, Mobile Verification, and Handover

**Files:**
- Modify: `README.md`
- Modify: `README_CN.md`
- Modify: `PROJECT_HANDOVER.md`
- Modify: `.memory.md`
- Create: `docs/plans/ai-learning-analytics-v1-progress.md`

**Interfaces:**
- Consumes: completed Tasks 1–5.
- Produces: verified local branch and current documentation; no runtime data.

- [ ] **Step 1: Run the analytics suite**

```powershell
$env:QWEN_API_KEY=' '
$env:DASHSCOPE_API_KEY=' '
.venv\Scripts\python.exe -m pytest tests\analytics -q
```

Expected: all Analytics tests pass.

- [ ] **Step 2: Run protected workflow regression**

```powershell
.venv\Scripts\python.exe -m pytest tests\test_reading_exam_page.py tests\test_reading_page_flow.py tests\test_writing.py tests\test_writing_editor.py tests\exporting -q
```

Expected: Reading Exam, Writing, and all 54 Exporter tests pass.

- [ ] **Step 3: Run complete verification**

```powershell
.venv\Scripts\python.exe -m pytest -q
.venv\Scripts\python.exe -m compileall -q app.py ielts_ai_coach
.venv\Scripts\python.exe -m pip check
git diff --check
```

Expected: all tests pass, compilation succeeds, dependencies are consistent,
and Git reports no whitespace errors.

- [ ] **Step 4: Run isolated Streamlit and mobile acceptance**

Start Streamlit with a temporary `DATABASE_URL`, temporary `BACKUP_DIR`, and
blank Qwen/Dashscope keys. Verify HTTP 200 for root and `/_stcore/health`.
Using authenticated fictional data, inspect Home at 375, 430, and 768 pixels:

- no horizontal overflow;
- Growth metrics wrap or stack;
- weakness and recommendation cards remain readable;
- required Listening/Speaking messages are visible;
- mobile navigation remains 56 pixels high;
- bottom content padding remains at least 88 pixels.

Do not use the real database or a real AI provider.

- [ ] **Step 5: Compare real database fingerprints**

Hash every real `.db`, `.db-wal`, `.db-shm`, and backup before and after final
verification. Require byte-identical hashes. Also assert the SQLAlchemy model
table-name set is unchanged from the 11-table baseline.

- [ ] **Step 6: Update documentation accurately**

Document:

- request-time Analytics with no schema change;
- exact Listening/Speaking evidence boundary;
- deterministic weaknesses and recommendations;
- Mock-only explanation;
- Home Growth Dashboard;
- current test count and protected-workflow result;
- known limits: no granular Listening/Speaking practice analysis and no
  persisted analytics history.

Do not claim official scoring, real AI analysis, or unsupported data.

- [ ] **Step 7: Commit Phase 6**

```powershell
git add README.md README_CN.md PROJECT_HANDOVER.md .memory.md docs/plans/ai-learning-analytics-v1-progress.md
git commit -m "docs(analytics): complete learning analytics handover"
```

- [ ] **Step 8: Confirm final local state**

```powershell
git status --porcelain
git branch --show-current
git log --oneline --reverse e5f1886..HEAD
git remote -v
```

Expected: clean `feature/ai-learning-analytics-v1`, local commits present, and
no push performed.
