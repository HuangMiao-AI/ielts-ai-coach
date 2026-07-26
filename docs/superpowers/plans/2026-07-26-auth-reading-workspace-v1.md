# Auth Persistence and Reading Workspace V1 Plan

> **Execution note:** Use the approved local-only branch
> `fix/auth-reading-workspace-v1`. No schema migration, cloud action, real AI
> request, or modification to `archive/enterprise-v0/` is in scope.

## Audit findings

- The active entry point is `app.py`, which imports `ielts_ai_coach.config`.
  Its default SQLite location is the repository-anchored absolute path
  `data/ielts_ai_coach.db`; the root `config.py` and `data/study_coach.db` are
  legacy and are not imported by the active application.
- A temporary database completed registration, V2 profile save, logout/login,
  a new browser session, and a Streamlit process restart successfully. The
  reported persistence failure could not be reproduced with the active default
  configuration.
- A real configuration hazard remains: an externally supplied relative SQLite
  `DATABASE_URL` follows the process working directory. It can therefore point
  to different files when the launch directory changes.
- The existing Reading workspace shows only the current question. It needs a
  presentation-only workspace layer that exposes every question while keeping
  `services/exam_state.py` as the answer/session authority.

## Phase 1: Stable account persistence and honest routing

**Files:**
`ielts_ai_coach/config.py`, `ielts_ai_coach/auth.py`,
`ielts_ai_coach/views/login.py`, `tests/test_auth.py`, and new focused tests.

1. First add failing tests proving a relative SQLite URL resolves against the
   repository base, remains identical across working directories, and never
   changes the default absolute URL.
2. Normalize only configured file-based SQLite paths in `get_database_url`.
   Preserve in-memory and non-SQLite URLs unchanged; do not alter schema or
   existing account rows.
3. Split account-absent and password-mismatch outcomes into explicit internal
   authentication exceptions. The login view will render distinct Simplified
   Chinese messages required by the approved specification.
4. Keep authentication identity limited to `user_id` and username; profile
   absence routes to onboarding rather than being treated as an absent account.
5. Add direct service-level regression tests for trimming/casefolding,
   logout/relogin, a fresh session factory, V2 profile absence, legacy fallback,
   and user isolation.

## Phase 2: Reading workspace composition

**Files:**
`ielts_ai_coach/views/reading_workspace.py`, new small view helper modules if
needed, `ielts_ai_coach/ui/styles.py`, and Reading page tests.

1. Add failing page/state tests for rendering every question in grouped form,
   retaining answers across reruns and mode changes, unanswered count,
   duplicate-submit safety, and the existing result/evidence loop.
2. Keep the existing state machine and repository submission API. Replace the
   single-current-question renderer with a question-pane renderer that creates
   stable per-question widget keys and writes changes through `answer_question`.
3. Add question-number navigation that targets each rendered question without
   exposing answers before submission. Use question type metadata and original
   passage paragraph labels supplied by the question bank.
4. Add semantic workspace hooks for split panes, sticky status headers, and
   submit controls. The divider will be implemented with isolated client-side
   HTML/CSS/JS and local browser storage, not a new framework.

## Phase 3: Responsive and browser validation

**Files:** responsive CSS/tests and concise handover memory updates.

1. Use the split workspace from desktop through iPad landscape; select an
   article/questions mode below the documented breakpoint while preserving
   session answers.
2. Verify the requested desktop and device widths with browser automation.
3. Run focused tests after each phase, then complete pytest, compileall,
   pip check, Streamlit health, privacy scan, and pre/post database fingerprints.
4. Commit coherent local milestones only after their relevant tests pass; do
   not push or merge the branch.
