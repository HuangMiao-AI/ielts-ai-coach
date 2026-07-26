# Live Timer, Question Navigation and Mobile Login V1 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Make the Reading workspace clock continuously and accurately count down, keep question navigation in sync, and centre the public authentication flow on mobile widths.

**Architecture:** The immutable `ReadingExamSession.started_at` and passage-specific duration remain the server-side source for every Streamlit rerun. A small, client-only Reading workspace helper renders the elapsed wall-clock difference every second and persists only the UI timer/navigation cursor in browser local storage to survive layout changes. No user data, score, answer, or schema is added. The authentication page removes its layout-only side columns and uses a keyed centred shell with responsive CSS.

**Tech Stack:** Python 3.12, Streamlit, embedded Streamlit component JavaScript, pytest, Streamlit AppTest, local browser verification.

## Global Constraints

- Do not alter SQLite schema, create tables, modify real user data, merge to main, push, call real AI APIs, or modify `archive/enterprise-v0/`.
- Keep existing Reading scoring and duplicate-submission protection unchanged.
- Keep authenticated `user_id` server-owned; browser helpers may use only user/task-scoped opaque UI keys.
- Use Simplified Chinese for new user-facing copy and preserve the Apple glass design system.
- Add a test before each behaviour-changing implementation and record the red-to-green result.

---

### Task 1: Reproduce and lock the timer and duration contracts

**Files:**
- Modify: `tests/test_reading_exam_state.py`
- Modify: `tests/test_reading_exam_page.py`
- Modify: `ielts_ai_coach/services/question_bank.py`
- Modify: `ielts_ai_coach/content/question_banks/reading_v1.json`
- Modify: `ielts_ai_coach/content/question_banks/reading_v2.json`

**Interfaces:**
- Produces `ReadingPassage.recommended_minutes: int` and a tested per-passage duration source.
- Retains `ReadingExamSession.duration_seconds` and `remaining_seconds()` as the authoritative server-side arithmetic.

- [ ] **Step 1: Write failing catalog and session tests**

```python
def test_each_original_reading_passage_has_a_valid_recommended_duration() -> None:
    passages = load_reading_catalog()
    assert len(passages) == 8
    assert all(10 <= passage.recommended_minutes <= 40 for passage in passages)
    assert load_reading_catalog()[0].recommended_minutes != 60

def test_session_duration_is_passage_specific_and_never_negative() -> None:
    session = create_exam_session(..., duration_seconds=24 * 60)
    started = start_exam(session, now=STARTED_AT)
    assert remaining_seconds(started, now=STARTED_AT + timedelta(minutes=25)) == 0
```

- [ ] **Step 2: Run the focused tests and verify they fail because `recommended_minutes` is absent.**

Run: `pytest tests/test_reading_exam_state.py tests/test_reading_exam_page.py -q`

- [ ] **Step 3: Add validated author-specified durations and route them to `load_exam_session`.**

```python
@dataclass(frozen=True)
class ReadingPassage:
    recommended_minutes: int

def _recommended_minutes(payload: dict[str, Any]) -> int:
    value = payload.get("recommended_minutes")
    if not isinstance(value, int) or not 10 <= value <= 40:
        raise ValueError("invalid_recommended_minutes")
    return value
```

Use 24 minutes for each 9-question V1 passage and 26 minutes for each 10-question V2 passage. Pass `state.passage.recommended_minutes * 60` whenever the workspace creates or reloads its exam state. Display `推荐时间：X 分钟` in the instruction and library-facing Reading copy.

- [ ] **Step 4: Re-run the focused tests and commit the duration milestone.**

Run: `pytest tests/test_reading_exam_state.py tests/test_reading_exam_page.py -q`

Commit: `fix(reading): use passage-specific recommended duration`

### Task 2: Add a continuous, resilient Reading countdown

**Files:**
- Create: `ielts_ai_coach/views/reading_workspace_client.py`
- Modify: `ielts_ai_coach/views/reading_workspace.py`
- Modify: `ielts_ai_coach/ui/responsive_css.py`
- Test: `tests/test_reading_exam_page.py`
- Test: `tests/test_navigation_responsive.py`

**Interfaces:**
- Produces `render_reading_workspace_client(*, user_id: int, task_id: int, started_at: datetime, duration_seconds: int, current_question_id: str) -> None`.
- Consumes the immutable session time; it never submits, scores, changes answers, or reads arbitrary user data.

- [ ] **Step 1: Write failing rendering contracts.**

```python
def test_workspace_renders_client_clock_from_stable_start_and_duration() -> None:
    source = WORKSPACE_SOURCE.read_text(encoding="utf-8")
    assert "data-reading-timer" in source
    assert "render_reading_workspace_client" in source
    assert "remaining_seconds(session)" not in source

def test_client_clock_script_uses_wall_clock_and_visibility_change() -> None:
    source = CLIENT_SOURCE.read_text(encoding="utf-8")
    assert "Date.now()" in source
    assert "visibilitychange" in source
    assert "Math.max(0" in source
```

- [ ] **Step 2: Run those tests and verify the expected red failure.**

Run: `pytest tests/test_reading_exam_page.py tests/test_navigation_responsive.py -q`

- [ ] **Step 3: Implement the zero-height client helper and timer marker.**

The helper must find only the user/task-scoped marker, compute `durationSeconds - floor((Date.now() - startedAtMs) / 1000)`, clamp it at zero, update every second, and immediately recompute on `visibilitychange`. The marker receives the existing server `started_at` and duration on every rerun. At zero it displays `00:00` and `时间已到，请提交`; the existing explicit submission rule remains unchanged.

- [ ] **Step 4: Re-run focused tests and perform a local 30-second idle browser check.**

Run: `pytest tests/test_reading_exam_page.py tests/test_navigation_responsive.py -q`

Expected browser evidence: elapsed display decreases by approximately 30 seconds without interaction or Streamlit rerun.

- [ ] **Step 5: Commit the timer milestone.**

Commit: `fix(reading): add continuous resilient countdown`

### Task 3: Synchronize in-page question navigation without reruns on scroll

**Files:**
- Modify: `ielts_ai_coach/views/reading_workspace.py`
- Modify: `ielts_ai_coach/views/reading_workspace_client.py`
- Modify: `ielts_ai_coach/ui/responsive_css.py`
- Test: `tests/test_navigation_responsive.py`

**Interfaces:**
- Navigation links use `data-reading-question-id` and question anchors use the same stable ID.
- The client helper applies exactly one `.current` and `aria-current="true"`, preserves `.answered`/`.unanswered`, and stores only the last active ID under a user/task-scoped local key.

- [ ] **Step 1: Write failing navigation markup and behaviour contracts.**

```python
def test_question_navigation_exposes_stable_client_sync_contract() -> None:
    assert "data-reading-question-id" in WORKSPACE_SOURCE.read_text(encoding="utf-8")
    assert "IntersectionObserver" in CLIENT_SOURCE.read_text(encoding="utf-8")
    assert "scrollIntoView" in CLIENT_SOURCE.read_text(encoding="utf-8")
```

- [ ] **Step 2: Run the focused navigation test and verify red.**

Run: `pytest tests/test_navigation_responsive.py -q`

- [ ] **Step 3: Implement immediate click and observed-scroll synchronization.**

Clicking a numbered link must prevent the default hash jump, scroll the matching anchor within its nearest scrollable container, and update its class immediately. An `IntersectionObserver` rooted at that container updates active state while users scroll. A rerun initializes from stored active ID only when it belongs to the current session; answer widgets remain the sole source of answer status.

- [ ] **Step 4: Re-run focused tests and browser-check question 2, question 5, scroll, and mode switching.**

Run: `pytest tests/test_navigation_responsive.py -q`

- [ ] **Step 5: Commit the navigation milestone.**

Commit: `fix(reading): synchronize active question navigation`

### Task 4: Centre the public mobile authentication layout

**Files:**
- Modify: `ielts_ai_coach/views/login.py`
- Modify: `ielts_ai_coach/ui/design_system.py`
- Test: `tests/test_navigation_responsive.py`
- Test: `tests/test_auth_persistence.py`

**Interfaces:**
- `auth_form_shell` is a presentation-only keyed Streamlit container.
- No authentication business rule, password handling, or user session contract changes.

- [ ] **Step 1: Write failing layout contracts.**

```python
def test_auth_page_has_one_centered_responsive_form_shell() -> None:
    source = LOGIN_SOURCE.read_text(encoding="utf-8")
    assert 'key="auth_form_shell"' in source
    assert "st.columns([1, 1.35, 1])" not in source
    assert ".st-key-auth_form_shell" in APP_CSS
    assert "max-width: 420px" in APP_CSS
```

- [ ] **Step 2: Run the layout/auth tests and verify red.**

Run: `pytest tests/test_navigation_responsive.py tests/test_auth_persistence.py -q`

- [ ] **Step 3: Replace desktop spacer columns with one centred shell and mobile-safe CSS.**

The form shell uses `width: min(100%, 420px)` and `margin-inline: auto`; within 768px it has a 16px practical side gutter, tab controls and form fields remain full-width, and no transform/grid spacer is introduced. Keep the hero, tabs, registration form, password reveal control, errors, and success flow intact.

- [ ] **Step 4: Re-run focused tests and local responsive browser checks.**

Run: `pytest tests/test_navigation_responsive.py tests/test_auth_persistence.py -q`

Test 375, 390, and 430px when browser viewport support is available; otherwise record the browser limitation and retain source/AppTest responsive contracts.

- [ ] **Step 5: Commit the mobile authentication milestone.**

Commit: `fix(auth-ui): center mobile authentication layout`

### Task 5: Full regression, database protection, and handover

**Files:**
- Modify: `.memory.md`
- Modify: `docs/superpowers/plans/2026-07-26-timer-nav-mobile-login-v1.md`
- Test: all suites

- [ ] **Step 1: Run focused Reading, navigation, auth, and duplicate-submission tests.**

Run: `pytest tests/test_reading_exam_state.py tests/test_reading_exam_page.py tests/test_navigation_responsive.py tests/test_auth_persistence.py -q`

- [ ] **Step 2: Run full verification.**

Run: `pytest -q`, `python -m compileall ielts_ai_coach`, and `pip check`.

- [ ] **Step 3: Verify a temporary-DB Streamlit health endpoint, inspect git diff, scan tracked files for credentials, and compare real DB/WAL/SHM size and SHA-256 with the recorded baseline.**

- [ ] **Step 4: Update plan checkboxes and `.memory.md`, re-run the relevant tests, and create the final test/documentation commit.**

Commit: `test(ui): cover timer navigation and mobile login`

## Coverage Review

- Continuous timer, background wall-clock reconciliation, non-negative zero, and stable server source: Task 2.
- Passage-specific durations for all eight original passages: Task 1.
- Click/scroll active navigation and preserved answer status: Task 3.
- Centred 375/390/430 public login and unchanged registration/auth behaviour: Task 4.
- Existing Reading scoring, duplicate submission, full pytest, health check, privacy scan, and database integrity: Task 5.
