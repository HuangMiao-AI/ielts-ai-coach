# Desktop Core Learning Flow V1 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Deliver persistent onboarding plus independent Reading, Listening,
Writing, and Speaking practice flows without changing any old database table.

**Architecture:** One additive learner-profile table owns optional onboarding
baselines, while a compatibility service adapts legacy profiles and real score
records without backfill. Skill services remain independent from plans;
Reading reuses an internal non-active task container, Listening uses bundled
session-scoped deterministic practice, Writing saves without Mock scoring, and
Speaking retains local-only recording with a text fallback.

**Tech Stack:** Python 3.12, Streamlit 1.59, SQLAlchemy 2.0, SQLite WAL, pytest
8, static JSON/WAV assets, existing premium glass UI.

## Global Constraints

- Add only `learner_profiles_v2`; never ALTER, DROP, RENAME, or rebuild an old table.
- Do not batch backfill, rewrite, delete, or fabricate user data.
- Missing bands are `None`/SQL `NULL`; zero is a measured value.
- Keep `score_records` limited to complete real score sets.
- Every repository operation requires and filters by authenticated `user_id`.
- Use temporary databases for tests and blank AI keys for every runtime check.
- Do not call external AI/TTS, Obsidian, Sync, Feishu, GitHub, or deployment.
- Update the progress document, run focused tests, and commit after each phase.

---

### Task 1: Additive V2 Profile Schema and Compatibility Contract

**Files:**
- Create: `ielts_ai_coach/database/learner_profile_models.py`
- Create: `ielts_ai_coach/database/learner_profile_repository.py`
- Modify: `ielts_ai_coach/database/models.py`
- Create: `ielts_ai_coach/services/learner_profiles.py`
- Create: `tests/test_learner_profiles_v2.py`
- Create: `tests/test_additive_schema_safety.py`
- Modify: `docs/plans/desktop-core-learning-flow-v1-progress.md`

**Interfaces:**
- Produces `LearnerProfileV2`, `LearnerProfileSnapshot`,
  `get_learner_profile(user_id, session_factory)`, and
  `save_learner_profile(user_id, ..., session_factory)`.
- Legacy reads consume only `student_profiles` and the newest real
  `score_records` row owned by the same user.

- [ ] **Step 1: Write failing model, validation, compatibility, isolation, and idempotency tests**

```python
profile = save_learner_profile(
    user_id=owner_id,
    display_name="审计学生",
    current_grade="高二",
    exam_date=None,
    daily_study_minutes=75,
    target_overall_band=7.0,
    current_reading_band=6.5,
    current_listening_band=None,
    current_writing_band=5.5,
    current_speaking_band=None,
    onboarding_completed=True,
    session_factory=factory,
)
assert profile.current_listening_band is None
assert get_learner_profile(owner_id, session_factory=factory) == profile
assert get_learner_profile(other_id, session_factory=factory) != profile
```

Assert invalid quarter bands fail, zero remains `0.0`, all four bands may be
`None`, a legacy profile reads without creating a V2 row, a real legacy
`ScoreRecord` supplies four bands, and two `create_all` calls leave old table
SQL/count/content fingerprints unchanged.

- [ ] **Step 2: Run RED**

```powershell
.venv\Scripts\python.exe -m pytest tests\test_learner_profiles_v2.py tests\test_additive_schema_safety.py -q
```

Expected: import failure for the new model/service.

- [ ] **Step 3: Implement the table and repository**

Use one unique FK `user_id`, nullable band columns, nullable `exam_date`,
timestamp defaults, and SQL checks for range/half-band values. Repository
functions are:

```python
get_learner_profile_v2(session, user_id: int) -> LearnerProfileV2 | None
upsert_learner_profile_v2(session, *, user_id: int, ...) -> LearnerProfileV2
```

Every query contains `LearnerProfileV2.user_id == user_id`.

- [ ] **Step 4: Implement compatibility and validation**

`get_learner_profile` selects V2 first. Without V2, it adapts the owned legacy
profile and only an actually present latest score record. Reads never write.
`save_learner_profile` validates display name, grade, optional date, minutes,
target, and every non-`None` band before an upsert.

- [ ] **Step 5: Run GREEN and old database tests**

```powershell
.venv\Scripts\python.exe -m pytest tests\test_learner_profiles_v2.py tests\test_additive_schema_safety.py tests\test_v1_database.py tests\test_database.py tests\test_user_isolation.py -q
```

- [ ] **Step 6: Update progress and commit**

```powershell
git add ielts_ai_coach/database ielts_ai_coach/services/learner_profiles.py tests/test_learner_profiles_v2.py tests/test_additive_schema_safety.py docs/plans/desktop-core-learning-flow-v1-progress.md
git commit -m "feat(profile): add additive learner profile v2"
```

---

### Task 2: Four-Step Onboarding and Editable Learning Settings

**Files:**
- Create: `ielts_ai_coach/views/learner_profile_form.py`
- Modify: `ielts_ai_coach/views/profile.py`
- Modify: `ielts_ai_coach/views/settings.py`
- Modify: `ielts_ai_coach/views/navigation.py`
- Modify: `ielts_ai_coach/ui/design_system.py`
- Create: `tests/test_onboarding_flow.py`
- Modify: `tests/test_profiles.py`
- Modify: `docs/plans/desktop-core-learning-flow-v1-progress.md`

**Interfaces:**
- Consumes `LearnerProfileSnapshot` and `save_learner_profile`.
- Produces `render_onboarding(user, page_refs)` and
  `render_learning_profile_editor(user, source_key)`.

- [ ] **Step 1: Write failing onboarding tests**

Use `AppTest` and a temporary database to register a fictional user, complete
four steps, leave all bands and exam date empty, save, and assert:

```python
assert app.session_state["onboarding_step"] == 4
assert "资料已保存，正在进入首页。" in rendered_text
assert saved.exam_date is None
assert saved.current_reading_band is None
assert app._page_hash == calc_hash("home")
```

Add tests for partial bands, quarter-band rejection at service level, persisted
completion after a fresh authenticated AppTest session, and legacy-save
creation of one V2 row.

- [ ] **Step 2: Run RED**

```powershell
.venv\Scripts\python.exe -m pytest tests\test_onboarding_flow.py tests\test_profiles.py -q
```

- [ ] **Step 3: Implement step state and shared form**

Use user-scoped keys such as `onboarding_{user.id}_step`. Step controls validate
only the current section. Optional bands use a select control with a visible
`未填写` option mapped to `None`, followed by real 0.0–9.0 half bands. Optional
exam date uses an explicit `暂未确定考试日期` checkbox rather than a fake date.

- [ ] **Step 4: Switch to Home after successful save**

Pass `page_refs` to Profile and call `st.switch_page(page_refs["home"])` only
after the transaction succeeds. Navigation considers onboarding complete only
when the resolved snapshot exists and `onboarding_completed` is true.

- [ ] **Step 5: Add Profile and Settings editors**

Both surfaces read the same snapshot and call the same save service. Saving a
legacy profile creates V2 only after the button is pressed. Settings must not
duplicate password or authentication logic.

- [ ] **Step 6: Run GREEN and navigation regression**

```powershell
.venv\Scripts\python.exe -m pytest tests\test_onboarding_flow.py tests\test_profiles.py tests\test_streamlit_v1_flow.py tests\test_navigation_shell.py -q
```

- [ ] **Step 7: Update progress and commit**

```powershell
git add ielts_ai_coach/views ielts_ai_coach/ui tests/test_onboarding_flow.py tests/test_profiles.py docs/plans/desktop-core-learning-flow-v1-progress.md
git commit -m "feat(onboarding): add persistent four-step setup"
```

---

### Task 3: Baseline-Aware Plans and Independent Home Actions

**Files:**
- Modify: `ielts_ai_coach/services/planning.py`
- Modify: `ielts_ai_coach/services/planning_rules.py`
- Modify: `ielts_ai_coach/services/analytics.py`
- Modify: `ielts_ai_coach/services/home.py`
- Modify: `ielts_ai_coach/views/plan.py`
- Modify: `ielts_ai_coach/views/dashboard.py`
- Create: `tests/test_baseline_planning.py`
- Modify: `tests/analytics/test_service.py`
- Modify: `docs/plans/desktop-core-learning-flow-v1-progress.md`

**Interfaces:**
- `build_plan_blueprint` accepts `dict[str, float | None]` and
  `exam_date: date | None`.
- Known values influence gaps; missing values receive no invented band.

- [ ] **Step 1: Write failing complete/partial/empty plan tests**

```python
empty = build_plan_blueprint(
    scores={subject: None for subject in SUBJECTS},
    target_overall=7.0,
    exam_date=None,
    daily_minutes=60,
    start_date=date(2026, 7, 25),
)
assert {task.subject for task in empty.tasks} == set(SUBJECTS)
assert empty.phase == "foundation"
```

Assert a single known Reading band prioritizes its measured gap without
treating missing Listening/Writing/Speaking as zero. Assert no `ScoreRecord` is
created by plan generation.

- [ ] **Step 2: Run RED**

```powershell
.venv\Scripts\python.exe -m pytest tests\test_baseline_planning.py tests\analytics\test_service.py -q
```

- [ ] **Step 3: Implement optional evidence rules**

Complete scores retain current deterministic behavior. Partial scores rank
known positive gaps, then rotate unknown subjects for exploration. No scores
use balanced rotation. A missing exam date selects `foundation` directly.

- [ ] **Step 4: Update Analytics and Home profile source**

Analytics target/time/current optional baselines come from the compatibility
snapshot. Historical `ScoreRecord` trends remain real-record trends. Home
always renders four skill links and a no-plan plan-generation action.

- [ ] **Step 5: Run GREEN**

```powershell
.venv\Scripts\python.exe -m pytest tests\test_baseline_planning.py tests\test_planning_v1.py tests\test_home.py tests\analytics -q
```

- [ ] **Step 6: Update progress and commit**

```powershell
git add ielts_ai_coach/services ielts_ai_coach/views/plan.py ielts_ai_coach/views/dashboard.py tests docs/plans/desktop-core-learning-flow-v1-progress.md
git commit -m "feat(plan): support honest baseline and exploration plans"
```

---

### Task 4: Plan-Independent Reading Library

**Files:**
- Modify: `ielts_ai_coach/database/plan_repository.py`
- Modify: `ielts_ai_coach/services/reading_exam.py`
- Modify: `ielts_ai_coach/services/reading_practice.py`
- Modify: `ielts_ai_coach/views/reading.py`
- Modify: `ielts_ai_coach/views/reading_workspace.py`
- Create: `tests/test_reading_library_independent.py`
- Modify: `tests/test_reading_page_flow.py`
- Modify: `docs/plans/desktop-core-learning-flow-v1-progress.md`

**Interfaces:**
- Produces `list_reading_library(user_id)` and
  `open_reading_library_item(user_id, passage_id)`.
- Internal library plans use `status="library"` and are excluded from visible
  plan history.

- [ ] **Step 1: Write failing no-plan library tests**

Assert a new user with no score and no active plan sees eight unique passage
IDs, can open any selected passage, creates one user-owned backing task only on
start, cannot access another user's task, and retains the existing complete
submission/review/history flow.

- [ ] **Step 2: Run RED**

```powershell
.venv\Scripts\python.exe -m pytest tests\test_reading_library_independent.py tests\test_reading_page_flow.py -q
```

- [ ] **Step 3: Implement virtual library and backing-task reuse**

List the validated catalog first. Match existing owned structured Reading
tasks by passage ID. On start, reuse an owned task or create one task beneath a
single non-active library container. Never archive an active study plan.

- [ ] **Step 4: Render richer cards**

Each card shows topic, version/difficulty, question count, estimated minutes,
and `未开始`/`继续练习`/`已提交`. Correct answers and evidence remain hidden until
submission.

- [ ] **Step 5: Run GREEN and protected scoring/export tests**

```powershell
.venv\Scripts\python.exe -m pytest tests\test_reading_library_independent.py tests\test_reading_exam_page.py tests\test_reading_practice.py tests\test_reading_scoring.py tests\exporting -q
```

- [ ] **Step 6: Update progress and commit**

```powershell
git add ielts_ai_coach/database/plan_repository.py ielts_ai_coach/services/reading* ielts_ai_coach/views/reading* tests docs/plans/desktop-core-learning-flow-v1-progress.md
git commit -m "feat(reading): decouple original library from study plans"
```

---

### Task 5: Original Listening Mini Tests and Offline Audio

**Files:**
- Create: `ielts_ai_coach/content/question_banks/listening_v1.json`
- Create: `ielts_ai_coach/services/listening_bank.py`
- Create: `ielts_ai_coach/services/listening_scoring.py`
- Create: `ielts_ai_coach/services/listening_session.py`
- Replace: `ielts_ai_coach/views/listening.py`
- Create: `static/audio/listening_v1_test_1.wav`
- Create: `static/audio/listening_v1_test_2.wav`
- Create: `scripts/generate_listening_audio.ps1`
- Create: `tests/test_listening_bank.py`
- Create: `tests/test_listening_scoring.py`
- Modify: `tests/test_listening_page.py`
- Modify: `docs/plans/desktop-core-learning-flow-v1-progress.md`

**Interfaces:**
- `load_listening_bank() -> ListeningBank`
- `score_listening_answers(test, answers) -> ListeningScore`
- Session state keys include authenticated `user_id` and stable test ID.

- [ ] **Step 1: Write failing content, audio, scoring, and flow tests**

Require exactly two tests, two sections per test, 16 questions per test, all
three approved types, unique IDs, project-original copyright metadata, WAV
files beginning with `RIFF`, complete-answer enforcement, normalization,
confirmation, per-question review, and user-scoped session keys.

- [ ] **Step 2: Run RED**

```powershell
.venv\Scripts\python.exe -m pytest tests\test_listening_bank.py tests\test_listening_scoring.py tests\test_listening_page.py -q
```

- [ ] **Step 3: Add original scripts and deterministic question bank**

Write two original everyday/academic scenarios with explicit Speaker A/B
turns, pauses, 16 questions, answers, explanations, and script evidence.
Copyright metadata states that the content is project-original and not
official IELTS or Cambridge material.

- [ ] **Step 4: Generate and inspect offline WAV assets**

Use only installed Windows speech voices. Alternate two voices when available;
otherwise retain explicit spoken “Speaker A”/“Speaker B” labels. Verify each
WAV is non-empty, playable by Python's `wave` module, has positive duration,
and contains audible PCM frames.

- [ ] **Step 5: Implement bank, session, scoring, and page**

The page renders test cards, bundled audio, two sections, question navigation,
unanswered count, explicit confirmation, deterministic total/correct score,
and explanations/evidence after submission. Results remain session-only and
are never advertised as persistent Analytics.

- [ ] **Step 6: Run GREEN**

```powershell
.venv\Scripts\python.exe -m pytest tests\test_listening_bank.py tests\test_listening_scoring.py tests\test_listening_page.py tests\test_skill_sessions.py -q
```

- [ ] **Step 7: Update progress and commit**

```powershell
git add ielts_ai_coach/content ielts_ai_coach/services/listening* ielts_ai_coach/views/listening.py static/audio scripts/generate_listening_audio.ps1 tests docs/plans/desktop-core-learning-flow-v1-progress.md
git commit -m "feat(listening): add original offline mini tests"
```

---

### Task 6: Writing Save-Only Fallback Without Fake Feedback

**Files:**
- Create: `ielts_ai_coach/content/question_banks/writing_v1.json`
- Create: `ielts_ai_coach/services/writing_tasks.py`
- Modify: `ielts_ai_coach/services/writing.py`
- Modify: `ielts_ai_coach/views/writing.py`
- Create: `tests/test_writing_save_only.py`
- Modify: `tests/test_writing_editor.py`
- Modify: `docs/plans/desktop-core-learning-flow-v1-progress.md`

**Interfaces:**
- `save_essay_without_feedback(...) -> Essay`
- `load_writing_tasks() -> tuple[WritingTask, ...]`
- Saved essays use status `saved` and create no `WritingFeedback` or quota use.

- [ ] **Step 1: Write failing no-provider and isolation tests**

Assert a Mock-configured page selects an original task, edits text, confirms
save, persists one owned essay, displays the exact disabled-AI message, reloads
content in history, creates no feedback, and does not increment usage.

- [ ] **Step 2: Run RED**

```powershell
.venv\Scripts\python.exe -m pytest tests\test_writing_save_only.py tests\test_writing_editor.py -q
```

- [ ] **Step 3: Implement original tasks and save-only service**

Validate with existing input limits, create an essay directly as `saved`, and
return it. Do not resolve or call a provider. Add pure local checks for words,
paragraphs, recommended length, and presence of an introduction/conclusion
without producing a band.

- [ ] **Step 4: Update page behavior**

When `provider.is_mock`, label the primary action `保存作文`; after confirmation
call only the save-only service. Any deliberately invoked Mock evaluation is
labeled `Demo feedback` and remains absent from the normal student path.

- [ ] **Step 5: Run GREEN and existing Writing regression**

```powershell
.venv\Scripts\python.exe -m pytest tests\test_writing_save_only.py tests\test_writing.py tests\test_writing_editor.py tests\test_ai_provider.py -q
```

- [ ] **Step 6: Update progress and commit**

```powershell
git add ielts_ai_coach/content/question_banks/writing_v1.json ielts_ai_coach/services/writing* ielts_ai_coach/views/writing.py tests docs/plans/desktop-core-learning-flow-v1-progress.md
git commit -m "feat(writing): save essays when AI scoring is disabled"
```

---

### Task 7: Speaking Microphone Test and Text Fallback

**Files:**
- Modify: `ielts_ai_coach/views/speaking.py`
- Create: `tests/test_speaking_fallback.py`
- Modify: `tests/test_speaking_page.py`
- Modify: `docs/plans/desktop-core-learning-flow-v1-progress.md`

**Interfaces:**
- Session keys remain user/part scoped.
- Completion requires a recording or non-empty text alternative.

- [ ] **Step 1: Write failing microphone, fallback, and timer tests**

Verify first-use guidance, microphone test control, denial/failure instructions,
text fallback activation, Part 2 preparation/response timers, and honest
completion with no score claim.

- [ ] **Step 2: Run RED**

```powershell
.venv\Scripts\python.exe -m pytest tests\test_speaking_fallback.py tests\test_speaking_page.py -q
```

- [ ] **Step 3: Implement the minimal fallback flow**

Add `麦克风测试`, permission copy, `麦克风无法使用` action, browser-settings
guidance, and `文字回答替代` textarea. Keep recording local. Never persist or
score recording/text.

- [ ] **Step 4: Run GREEN**

```powershell
.venv\Scripts\python.exe -m pytest tests\test_speaking_fallback.py tests\test_speaking_page.py tests\test_skill_sessions.py -q
```

- [ ] **Step 5: Update progress and commit**

```powershell
git add ielts_ai_coach/views/speaking.py tests/test_speaking_fallback.py tests/test_speaking_page.py docs/plans/desktop-core-learning-flow-v1-progress.md
git commit -m "feat(speaking): add microphone recovery and text fallback"
```

---

### Task 8: Desktop Core-Flow UI and Responsive Contracts

**Files:**
- Modify: `ielts_ai_coach/views/dashboard.py`
- Modify: `ielts_ai_coach/views/reading.py`
- Modify: `ielts_ai_coach/views/listening.py`
- Modify: `ielts_ai_coach/views/writing.py`
- Modify: `ielts_ai_coach/views/speaking.py`
- Modify: `ielts_ai_coach/ui/design_system.py`
- Modify: `tests/test_navigation_responsive.py`
- Create: `tests/test_desktop_core_flow.py`
- Modify: `docs/plans/desktop-core-learning-flow-v1-progress.md`

**Interfaces:**
- Reuses the existing glass cards and route registry.
- Adds no second dashboard or duplicate primary navigation.

- [ ] **Step 1: Write failing desktop and route-contract tests**

Assert one Home skill-entry group, honest no-plan state, card metadata, no
meaningless Continue labels, and CSS contracts for 1366×768, 1440×900,
1920×1080, 1024×768, 768, 430, and 375 widths.

- [ ] **Step 2: Run RED**

```powershell
.venv\Scripts\python.exe -m pytest tests\test_desktop_core_flow.py tests\test_navigation_responsive.py -q
```

- [ ] **Step 3: Implement focused glass-layout enhancements**

Use minmax grids, `min-width: 0`, wrapping labels, 44-pixel controls, safe
bottom spacing, and desktop density adjustments. Keep four primary entries and
all existing Analytics content.

- [ ] **Step 4: Run GREEN and Home/UI regression**

```powershell
.venv\Scripts\python.exe -m pytest tests\test_desktop_core_flow.py tests\test_navigation_responsive.py tests\test_dashboard.py tests\test_home.py tests\analytics -q
```

- [ ] **Step 5: Update progress and commit**

```powershell
git add ielts_ai_coach/views ielts_ai_coach/ui/design_system.py tests docs/plans/desktop-core-learning-flow-v1-progress.md
git commit -m "fix(ui): strengthen desktop learning flow"
```

---

### Task 9: Browser Acceptance and Complete Verification

**Files:**
- Create ignored output under `.superpowers/sdd/runtime/desktop-core-flow/`
- Modify: `README.md`
- Modify: `README_CN.md`
- Modify: `PROJECT_HANDOVER.md`
- Modify: `.memory.md`
- Modify: `docs/plans/desktop-core-learning-flow-v1-progress.md`

**Interfaces:**
- Consumes the complete feature branch.
- Produces local evidence only; no remote operation.

- [ ] **Step 1: Run focused suites**

```powershell
.venv\Scripts\python.exe -m pytest tests\test_learner_profiles_v2.py tests\test_onboarding_flow.py tests\test_baseline_planning.py tests\test_reading_library_independent.py tests\test_listening_bank.py tests\test_listening_scoring.py tests\test_listening_page.py tests\test_writing_save_only.py tests\test_speaking_fallback.py tests\test_desktop_core_flow.py -q
```

- [ ] **Step 2: Run protected suites and full pytest**

```powershell
.venv\Scripts\python.exe -m pytest tests\analytics tests\exporting tests\test_reading_exam_page.py tests\test_reading_practice.py tests\test_writing.py -q
.venv\Scripts\python.exe -m pytest -q
.venv\Scripts\python.exe -m compileall -q app.py ielts_ai_coach
.venv\Scripts\python.exe -m pip check
git diff --check
```

- [ ] **Step 3: Run browser flows A–E on a temporary database**

Verify registration/onboarding/Home, no-plan Reading submission, Listening
audio and score review, Writing save-only history, and Speaking microphone
fallback. Inspect 375, 430, 768, 1024, 1366×768, 1440×900, and 1920×1080.
Save ignored screenshots and verify no horizontal overflow or console error.

- [ ] **Step 4: Prove additive schema on a real-database copy**

Copy DB/WAL/SHM together, run `create_all` against the copy, and compare old
table names, SQL, row counts, and canonical content hashes. Require exactly
one new empty table.

- [ ] **Step 5: Back up and apply the one approved table to the real database**

Create timestamped byte copies of DB/WAL/SHM. Record pre-state hashes,
definitions, counts, and content fingerprints. Run only
`Base.metadata.create_all(engine)`. Record post-state and require:

```text
new tables == {"learner_profiles_v2"}
all old SQL definitions unchanged
all old row counts unchanged
all old canonical content hashes unchanged
learner_profiles_v2 row count == 0 before any user action
```

Do not checkpoint.

- [ ] **Step 6: Update documentation and progress**

Document actual fields, read priority, `NULL` missing semantics, no old-table
mutation, Listening session-only limitation, Writing save-only behavior, test
count, database evidence, and local start command.

- [ ] **Step 7: Commit final documentation**

```powershell
git add README.md README_CN.md PROJECT_HANDOVER.md .memory.md docs/plans/desktop-core-learning-flow-v1-progress.md
git commit -m "docs(flow): complete desktop learning handover"
```

- [ ] **Step 8: Final local-state verification**

```powershell
git status --porcelain
git branch --show-current
git log --oneline c930662..HEAD
git remote -v
```

Expected: clean `fix/desktop-core-learning-flow-v1`, local commits only, no
merge and no push.
