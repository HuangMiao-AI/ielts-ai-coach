# Premium Exam UI and Mobile PWA V1 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use
> superpowers:executing-plans to implement this plan task-by-task. Steps use
> checkbox (`- [ ]`) syntax for tracking.

**Goal:** Upgrade IELTS AI Coach into a polished, responsive Streamlit exam
experience with one navigation system, complete Reading interaction, honest
Listening/Speaking boundaries, resilient Writing drafts, real Home data, and
installable mobile metadata.

**Architecture:** Preserve authentication, repositories, SQLite schema,
deterministic scoring, Writing feedback, History, and Obsidian Exporter. Add
pure state helpers and dedicated views above existing services, a centralized
UI system, an additive reading bank catalog, and static PWA assets.

**Tech Stack:** Python 3.12, Streamlit 1.59.2, SQLAlchemy 2.0, SQLite,
Pydantic 2, pytest 8, Pillow from the installed Streamlit environment.

## Global Constraints

- Do not read or modify real user rows during implementation or testing.
- Do not change the database schema unless a separately documented hard need
  is proven; this plan requires no schema change.
- Do not call Qwen, OpenAI, external TTS, Obsidian Sync, Feishu, or any other
  external AI/network workflow.
- Keep all student-facing copy in Simplified Chinese.
- Preserve the complete Obsidian Exporter and its tests.
- Do not push, merge to main, force-push, hard-reset, or clean user files.
- Write a failing behavioral test before each production behavior.
- Update the progress file, run phase tests, and create a local commit after
  every task.

---

### Task 1: Establish the premium design system

**Files:**
- Create: `ielts_ai_coach/ui/design_system.py`
- Create: `ielts_ai_coach/ui/components.py`
- Modify: `ielts_ai_coach/ui/styles.py`
- Modify: `app.py`
- Test: `tests/test_design_system.py`
- Test: `tests/test_navigation_responsive.py`

**Interfaces:**
- Produces `render_page_header(title, description, eyebrow=None, progress=None)`.
- Produces `render_status_pill(label, tone)` and `render_metric_card(...)`.
- Produces `DESIGN_TOKENS` and `build_app_css() -> str`.

- [ ] Write tests that assert semantic token values, 44 px touch targets,
  `prefers-reduced-motion`, safe-area support, and the 375/430/768/1024/1366
  breakpoints.
- [ ] Run the focused tests and confirm they fail because the new modules and
  selectors do not exist.
- [ ] Implement immutable design tokens, shared components, and scoped glass
  CSS with readable surfaces and reduced mobile blur.
- [ ] Run design and existing responsive tests until green.
- [ ] Update progress and commit:
  `feat(ui): establish premium glass design system`.

### Task 2: Replace duplicate navigation with one route shell

**Files:**
- Modify: `ielts_ai_coach/views/navigation.py`
- Create: `ielts_ai_coach/ui/navigation.py`
- Create: `ielts_ai_coach/ui/layout.py`
- Create: `ielts_ai_coach/views/reading.py`
- Create: `ielts_ai_coach/views/listening.py`
- Create: `ielts_ai_coach/views/speaking.py`
- Test: `tests/test_navigation_responsive.py`

**Interfaces:**
- Produces `PRIMARY_ROUTE_TITLES` with exactly Home, Reading, Listening,
  Writing, Speaking, Study Plan, History, Profile.
- Produces `build_navigation_pages(user)`, one hidden Streamlit registry,
  desktop sidebar links, phone bottom links, and one More panel.

- [ ] Write failing tests for unique route titles, four skill routes, no
  repeated Home/History, hidden built-in navigation, and safe bottom spacing.
- [ ] Add minimal page shells and a single custom navigation renderer.
- [ ] Keep Today, Scores, AI Coach, and Settings as contextual hidden routes.
- [ ] Run navigation, app, authentication, and Streamlit flow tests.
- [ ] Update progress and commit:
  `feat(navigation): unify desktop and mobile navigation`.

### Task 3: Add a dedicated Reading exam state machine

**Files:**
- Create: `ielts_ai_coach/services/exam_state.py`
- Create: `ielts_ai_coach/services/reading_exam.py`
- Modify: `ielts_ai_coach/views/reading.py`
- Modify: `ielts_ai_coach/views/task_cards.py`
- Modify: `ielts_ai_coach/views/today.py`
- Modify: `ielts_ai_coach/views/history.py`
- Test: `tests/test_reading_exam_state.py`
- Test: `tests/test_reading_exam_page.py`
- Extend: `tests/test_reading_practice.py`
- Extend: `tests/test_reading_page_flow.py`

**Interfaces:**
- Produces `ReadingExamPhase` and `ReadingExamSession`.
- Produces user/task-scoped key helpers, answer/progress navigation, elapsed and
  remaining time calculations, and explicit confirmation state.
- Consumes existing `get_reading_practice_state()` and
  `submit_reading_practice()` without duplicating scoring.

- [ ] Write failing pure-state tests for start, answer, jump, previous/next,
  unanswered count, timer stability, confirmation, and submitted lock.
- [ ] Implement the minimal immutable state transitions and session adapters.
- [ ] Write failing page tests proving answers/explanations are absent before
  submit and present after submit.
- [ ] Implement library, instructions, split exam, mobile article/question
  toggle, question strip, timer, submit dialog, result summary, type weakness,
  and review rendering.
- [ ] Keep session-only drafts and label the recovery boundary honestly.
- [ ] Reuse existing attempt persistence and add a History review entry using
  the stored result snapshot.
- [ ] Run all Reading, ownership, task/log, and page-flow tests.
- [ ] Update progress and commit:
  `feat(reading): add full interactive exam experience`.

### Task 4: Add five original Academic Reading passages

**Files:**
- Create: `ielts_ai_coach/content/question_banks/reading_v2.json`
- Modify: `ielts_ai_coach/services/question_bank.py`
- Modify: `ielts_ai_coach/services/task_templates.py`
- Test: `tests/test_question_bank.py`
- Create: `tests/test_reading_content_quality.py`
- Modify: `README.md`
- Modify: `README_CN.md`

**Interfaces:**
- Produces `load_reading_catalog() -> tuple[ReadingPassage, ...]`.
- Keeps v1 passage lookup compatible for existing `task-content-v1` rows.
- Adds globally unique IDs `AR-V2-001` through `AR-V2-005`.

- [ ] Write failing catalog tests for eight passages, 77 total questions,
  global ID uniqueness, 750–950 new-passage words, 10 questions per new
  passage, valid answers, non-empty evidence, and all three type coverage.
- [ ] Add the five original passages and 50 questions defined in the design.
- [ ] Implement multi-bank loading without changing v1 content or schema.
- [ ] Run source-quality, scoring, compatibility, and full Reading tests.
- [ ] Update copyright documentation and progress.
- [ ] Commit:
  `content(reading): expand original academic practice bank`.

### Task 5: Add honest Listening, resilient Writing, and Speaking flows

**Files:**
- Create: `ielts_ai_coach/services/skill_sessions.py`
- Modify: `ielts_ai_coach/views/listening.py`
- Modify: `ielts_ai_coach/views/writing.py`
- Modify: `ielts_ai_coach/views/speaking.py`
- Test: `tests/test_skill_sessions.py`
- Create: `tests/test_listening_page.py`
- Create: `tests/test_writing_editor.py`
- Create: `tests/test_speaking_page.py`

**Interfaces:**
- Produces user/skill/task scoped draft keys and pure timer/navigation helpers.
- Listening returns Demo completion state only; it does not persist a score.
- Writing continues to call the existing `submit_essay()` service once.
- Speaking keeps recordings in the Streamlit session only.

- [ ] Write failing tests for Listening section/progress/timer and honest Demo
  labels.
- [ ] Implement Listening test/section selection, local player boundary,
  answers, confirmation, and result skeleton without a scoring claim.
- [ ] Write failing tests for live word count, isolated Task 1/Task 2 drafts,
  clear confirmation, timer stability, and duplicate-click protection.
- [ ] Refactor Writing outside one blocking form while preserving feedback and
  history.
- [ ] Write failing tests for Speaking Part navigation, preparation/response
  timers, notes, completion, and recording capability copy.
- [ ] Implement `st.audio_input` with local playback and explicit no-scoring
  copy; handle no recording without a fake success state.
- [ ] Run Writing, provider, quota, privacy, and new skill-flow tests.
- [ ] Update progress and commit:
  `feat(skills): improve listening writing and speaking flows`.

### Task 6: Upgrade Home with real learning data

**Files:**
- Create: `ielts_ai_coach/services/home.py`
- Modify: `ielts_ai_coach/views/dashboard.py`
- Test: `tests/test_home.py`
- Extend: `tests/test_dashboard.py`
- Extend: `tests/test_user_isolation.py`

**Interfaces:**
- Produces `HomeSnapshot` containing real streak, latest Reading, latest
  Writing, weak sections, plan preview, activity, and recommended route.
- Every query consumes one authenticated `user_id`.

- [ ] Write failing tests for zero-data behavior, streak calculation from
  StudyLogs, latest records, recommendation priority, and cross-user isolation.
- [ ] Implement read-only aggregation through existing repositories.
- [ ] Render four skill shortcuts, real progress, recent activity, plan preview,
  and lightweight completion feedback without fabricated values.
- [ ] Run Home, dashboard, ownership, and database tests.
- [ ] Update progress and commit:
  `feat(home): add interactive student progress experience`.

### Task 7: Add responsive acceptance rules and PWA assets

**Files:**
- Create: `ielts_ai_coach/ui/pwa.py`
- Create: `static/manifest.webmanifest`
- Create: `static/icons/ielts-coach.svg`
- Create: `scripts/generate_pwa_icons.py`
- Generate: `static/icons/icon-192.png`
- Generate: `static/icons/icon-512.png`
- Generate: `static/icons/icon-maskable-512.png`
- Generate: `static/icons/apple-touch-icon.png`
- Generate: `static/icons/favicon-32.png`
- Modify: `.streamlit/config.toml`
- Modify: `app.py`
- Create: `docs/mobile-pwa.md`
- Test: `tests/test_pwa_assets.py`
- Extend: `tests/test_navigation_responsive.py`

**Interfaces:**
- Produces `build_pwa_head_markup() -> str` and `install_pwa_metadata()`.
- Enables Streamlit static serving only; registers no service worker.

- [ ] Write failing tests for required manifest fields, standalone display,
  neutral colors, every icon path and exact image dimensions.
- [ ] Add original vector source and deterministic Pillow generator; generate
  all PNG assets.
- [ ] Inject manifest, viewport, mobile-web-app, Apple, theme, and favicon
  metadata.
- [ ] Add targeted 375, 430, 768, 1024, and 1366 rules with safe-area spacing
  and reduced blur/animation.
- [ ] Document Windows startup, local-network conditions, iPhone/iPad/Android
  installation, HTTPS, and no-offline/native-app limitations.
- [ ] Run PWA, responsive, app, and privacy tests.
- [ ] Update progress and commit:
  `feat(pwa): add mobile install assets and metadata`.

### Task 8: Complete automated regression coverage

**Files:**
- Modify: new and existing files under `tests/`
- Modify: `.memory.md`
- Modify: `docs/plans/ui-exam-pwa-v1-progress.md`

**Interfaces:**
- No production interface changes.

- [ ] Add or strengthen behavioral tests for all 25 required categories,
  avoiding assertions that only check arbitrary source strings.
- [ ] Run each new focused test file, the 54 exporter tests, compileall, privacy
  scans, and full pytest.
- [ ] Verify database and backup fingerprints against the Stage 0 baseline.
- [ ] Update progress and memory with durable facts only.
- [ ] Commit:
  `test(ui): add interaction and responsive tests`.

### Task 9: Run Streamlit and visual acceptance

**Files:**
- Modify only if a failing behavioral or visual check requires a tested fix.
- Update: `docs/plans/ui-exam-pwa-v1-progress.md`

**Interfaces:**
- Uses a temporary SQLite database and forced Mock mode.

- [ ] Start headless Streamlit with a temporary database; verify health and root
  HTTP 200.
- [ ] Use browser automation to inspect login, Home, Reading library/exam/result,
  Listening, Writing, Speaking, and History.
- [ ] Inspect 375, 430, 768, 1024, and desktop widths for overflow, touch
  targets, bottom-bar overlap, article readability, dialogs, and landscape.
- [ ] For every discovered bug, write a failing regression test before the fix.
- [ ] Run full pytest and compileall again.
- [ ] Update progress and commit:
  `docs(ui): record responsive visual acceptance`.

### Task 10: Finish the local feature branch

**Files:**
- Update: `README.md`
- Update: `README_CN.md`
- Update: `.memory.md`
- Update: `docs/plans/ui-exam-pwa-v1-progress.md`

**Interfaces:**
- No new runtime interfaces.

- [ ] Verify every final requirement against code, tests, and browser evidence.
- [ ] Record exact content counts, test counts, limitations, startup command,
  PWA instructions, and no-push status.
- [ ] Run full pytest, exporter tests, compileall, pip check, Git privacy scan,
  database fingerprint comparison, and `git diff --check`.
- [ ] Commit final documentation:
  `docs(ui): complete premium exam and PWA handover`.
- [ ] Confirm the branch is `feature/ui-exam-pwa-v1`, all local commits are
  present, no remote push occurred, and the worktree is clean.
