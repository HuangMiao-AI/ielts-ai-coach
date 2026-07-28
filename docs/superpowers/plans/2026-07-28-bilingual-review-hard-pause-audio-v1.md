# Bilingual Review, Hard Pause, and Controlled Audio Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Give every existing Reading and Listening item a Chinese-first, evidence-backed review, and make all practice sessions genuinely unviewable and non-interactive while paused.

**Architecture:** Extend immutable content models with validated static bilingual review and vocabulary records; deterministic scoring snapshots keep those records for durable Reading results. A shared Streamlit presentation layer creates the pause lock. Listening uses a local Components v1 HTML5 audio component rather than `st.audio`, exchanging explicit commands and state records with the Python view.

**Tech Stack:** Python 3.12, Streamlit 1.59 Components v1, static JSON content, pytest, browser acceptance on an isolated SQLite database.

## Global Constraints

- All student-visible copy is Simplified Chinese; English is retained only for source material, answers, vocabulary, and necessary language notes.
- Do not alter the SQLite schema, live database, WAL, SHM, backups, external APIs, or user-owned data.
- All Reading and Listening review content is static, bank-owned, and traceable to the original passage or verified listening script.
- The custom player must be a local HTML5 Audio Components v1 component; never control Streamlit's built-in player through DOM selectors.
- Keep active Python modules under 300 lines where practical and add pytest coverage before each production behavior.

---

### Task 1: Baseline and review-content contracts

**Files:**
- Modify: `ielts_ai_coach/services/question_bank.py`, `ielts_ai_coach/services/listening_bank.py`, `ielts_ai_coach/services/reading_scoring.py`, `ielts_ai_coach/services/listening_scoring.py`
- Modify: `ielts_ai_coach/content/question_banks/reading_v1.json`, `ielts_ai_coach/content/question_banks/reading_v2.json`, `ielts_ai_coach/content/question_banks/listening_v1.json`
- Test: `tests/test_question_bank.py`, `tests/test_listening_bank.py`, `tests/test_review_content.py`

**Interfaces:**
- Produces immutable question-review and vocabulary records with Chinese explanation, evidence translation, tested skill, common mistake, synonym pairs, and vocabulary entries.
- Scoring snapshots expose those fields for submitted Reading and Listening results without database migration.

- [ ] Write failing tests that load every current bank item and require non-empty Chinese explanation, evidence translation, source-backed evidence, and 8–15 deduplicated bilingual vocabulary entries per Reading passage and verified Listening section.
- [ ] Run the focused tests and verify that the missing review contract fails.
- [ ] Add the smallest validated dataclasses/loaders and bank-owned static content that make the tests pass; preserve each existing identifier, answer, source text, and scoring rule.
- [ ] Run the focused content and scoring tests.

### Task 2: Chinese-first result views

**Files:**
- Create: `ielts_ai_coach/views/review_components.py`
- Modify: `ielts_ai_coach/views/task_cards.py`, `ielts_ai_coach/views/reading_result_view.py`, `ielts_ai_coach/views/listening_sections.py`, `ielts_ai_coach/views/writing_feedback_view.py`, `ielts_ai_coach/ui/responsive_css.py`
- Test: `tests/test_review_views.py`, `tests/test_reading_exam_page.py`, `tests/test_listening_page.py`, `tests/test_writing_editor.py`

**Interfaces:**
- Produces one shared score summary, question-status strip, type analysis, tabbed Reading/Listening review, bilingual vocabulary table/card list, and Chinese-first Writing feedback renderer.

- [ ] Write failing view/source tests for Chinese-first labels, answer status, per-type totals and accuracy, evidence translation, reasoning, mistakes, vocabulary, and responsive no-overflow classes.
- [ ] Run the focused tests and verify failure before implementation.
- [ ] Implement reusable renderers and wire them into existing results; retain existing persisted score flows instead of creating a second result system.
- [ ] Run the focused view tests and Streamlit AppTests.

### Task 3: Shared hard pause layer

**Files:**
- Create: `ielts_ai_coach/views/exam_hard_pause.py`
- Modify: `ielts_ai_coach/views/exam_control_panel.py`, `ielts_ai_coach/views/reading_workspace.py`, `ielts_ai_coach/views/listening.py`, `ielts_ai_coach/views/writing.py`, `ielts_ai_coach/ui/responsive_css.py`
- Test: `tests/test_exam_hard_pause.py`, `tests/test_reading_exam_page.py`, `tests/test_listening_page.py`, `tests/test_writing_editor.py`

**Interfaces:**
- `render_hard_pause_overlay(session, subject, root_key) -> bool` renders only remaining time and resume action while suspended; it applies inert state, focus/scroll capture and restoration, and returns whether a resume transition was requested.

- [ ] Write failing tests for paused overlay markup, inert exam root, body/pane scroll lock, blocked keyboard/pointer input, rerun persistence, and answer/draft preservation.
- [ ] Run the focused pause tests and verify the current disabled-input-only behavior fails the hard-pause contract.
- [ ] Implement the shared overlay and integrate it before skill-specific examination content renders.
- [ ] Run focused pause and existing control tests.

### Task 4: Controlled Listening audio and start confirmation

**Files:**
- Create: `ielts_ai_coach/components/exam_audio/frontend/index.html`
- Create: `ielts_ai_coach/ui/exam_audio.py`
- Modify: `ielts_ai_coach/views/listening.py`, `ielts_ai_coach/services/listening_session.py`
- Test: `tests/test_exam_audio.py`, `tests/test_listening_page.py`

**Interfaces:**
- `render_exam_audio(source_bytes, command, locked, key) -> AudioPlaybackState` sends `load`, `play`, `pause`, `resume`, `stop`, `seek_to`, and `set_locked` to a local Components v1 iframe and returns current time, duration, playback state, ended, ready, and error.
- Listening introduces an instruction/sound-check stage and starts the official timer only after explicit confirmation.

- [ ] Write failing component-contract tests for command protocol, state events, stop-on-timeout/submit, no duplicate players, and hard-pause synchronization.
- [ ] Run them to verify `st.audio` cannot meet the command contract.
- [ ] Implement the local component and session state, replace `st.audio`, then integrate audio state with the shared controller and start confirmation.
- [ ] Run focused tests and the Listening UI test suite.

### Task 5: Verification and handoff

**Files:**
- Modify: `.memory.md`
- Test: entire `tests/` suite

- [ ] Capture real database/WAL/SHM/backup fingerprints without opening the live database for writing.
- [ ] Run `pytest -q`, `python -m compileall .`, `pip check`, and `git diff --check`.
- [ ] Run a temporary-database Streamlit health check and browser acceptance for 375, 390, 430, 768, 1024, 1440, and 1920px; record any unavailable iPad/Safari evidence honestly.
- [ ] Recheck fingerprints, update `.memory.md`, stage only source/test/documentation files, and create one local commit on `fix/bilingual-review-hard-pause-audio-v1`.
