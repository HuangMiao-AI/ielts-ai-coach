# Premium Exam UI and Mobile PWA V1 Design

## Status

This design is approved by the attached product specification dated
2026-07-19. The specification explicitly authorizes continuous execution after
the read-only audit, so no additional per-phase approval gate is required.

## Baseline

- Source branch: `feature/obsidian-exporter-v1`
- Feature branch: `feature/ui-exam-pwa-v1`
- Baseline commit: `bfbd45fbde3262f8a639cad40bdc60b8f3368bba`
- Baseline verification: 128 pytest tests and compileall pass
- Streamlit: 1.59.2
- Database: unchanged 11-table SQLite schema
- Existing reading content: 3 original passages, 27 questions
- Exporter: preserved as a one-way, manual, read-only-source workflow

## Audit Findings

1. The authenticated app exposes nine top routes and repeats the full route
   list in a mobile expander.
2. Reading is functional but embedded in Today; it lacks a practice library,
   explicit instructions screen, question navigator, timer, and dedicated
   history review route.
3. Reading drafts are session-only. Final answers, score, accuracy, wrong
   questions, explanations, and evidence are already persisted safely in
   `task_question_attempts`.
4. Listening and Speaking are honest task cards, not interactive practice
   pages.
5. Writing submits essays and supports Mock feedback, but its word count is not
   live and Task 1/Task 2 drafts share state.
6. The CSS is centralized but lacks tokens, glass surfaces, safe-area support,
   reduced-motion handling, and targeted phone/tablet breakpoints.
7. Streamlit 1.59.2 provides session state, forms, dialogs, fragments,
   `audio_input`, components, navigation, and static-file serving.
8. Static metadata and install assets are feasible. Full offline PWA behavior
   is not feasible without a deployment-specific service worker and will not
   be claimed.

## Considered Approaches

### A. CSS-only facelift

Keep the current route and page structure and restyle existing widgets.

- Lowest implementation risk.
- Does not solve duplicate navigation, Reading exam hierarchy, resilient
  editors, or four-skill discoverability.
- Rejected because it misses core product behavior.

### B. Modular Streamlit exam shell (selected)

Keep Streamlit, repositories, database schema, scoring, authentication, and
Exporter. Add pure state helpers, dedicated skill pages, one custom navigation
shell, shared UI components, additive original content, and static PWA assets.

- Preserves proven business rules and user isolation.
- Supports TDD around state transitions without testing CSS strings alone.
- Avoids database migration and framework rewrite.
- Selected as the safest complete approach.

### C. Separate frontend or schema-heavy redesign

Introduce React or persist every draft and timer in new tables.

- Could provide deeper offline and cross-device behavior.
- Violates the approved framework and migration boundaries.
- Rejected.

## Information Architecture

The sole visible primary navigation is:

- Home
- Reading
- Listening
- Writing
- Speaking
- Study Plan
- History
- Profile / Settings

Streamlit's built-in navigation registry remains hidden. Context-only pages
such as Today, Scores, and AI Coach remain registered and reachable from Home,
Study Plan, or Profile without appearing as a second primary menu.

Desktop uses one compact glass sidebar. Phone layouts use one fixed bottom bar
with Home, Reading, Writing, and More. More exposes Listening, Speaking, Study
Plan, History, Profile, and Settings. The bar includes the iPhone safe-area
inset and never overlays submit controls.

## Design System

The UI uses project-owned CSS and vector assets:

- warm neutral canvas with a restrained teal accent;
- readable opaque content inside semi-transparent glass shells;
- one elevation hierarchy instead of floating every card;
- 16–24 px radii, subtle borders, and low-cost shadows;
- shared page headers, metric cards, pills, alerts, empty states, and action
  rows;
- minimum 44 px touch targets;
- explicit selected text/icons, not color-only state;
- reduced blur and animation on narrow or reduced-motion devices.

No Apple, IELTS, or Cambridge trademarks or copyrighted visual assets are
copied.

## Reading State Machine

Pure helpers define:

```text
LIBRARY
→ INSTRUCTIONS
→ IN_PROGRESS
→ SUBMIT_CONFIRMATION
→ SUBMITTED
→ REVIEW
```

Per-user, per-task session keys store the current question, article/question
view, draft answers, start timestamp, duration, and confirmation state. A
normal Streamlit rerun keeps the state. A new browser session, server restart,
or different device can lose the draft; the UI states this limitation.

Final submission continues through `submit_reading_practice()`. The UI never
implements scoring. Existing ownership checks, deterministic scoring,
`task_question_attempts`, Task completion, StudyLog synchronization, and
history are reused. No database schema change is required.

## Other Skill Pages

- Listening V1 is an honest Demo state machine with section selection, local
  player boundary, answer controls, progress, timer, confirmation, and result
  skeleton. No official audio or scoring claim.
- Writing keeps the existing essay/feedback service while separating Task 1
  and Task 2 drafts, adding live word count, timers, clear/submit confirmation,
  and duplicate-click protection.
- Speaking provides Part 1/2/3 state, prompts, timers, notes, completion, and
  local `st.audio_input` recording/playback. Recording is not externally
  uploaded and no speech score is claimed.

## Home

Home aggregates only real user-owned data: today's completion, study streak
from StudyLogs, latest Reading attempt, latest Writing submission, latest
score weaknesses, recommended next action, plan preview, recent activity, and
four skill shortcuts. Missing data renders zero or guidance, never fabricated
rankings or streaks.

## Reading Content

`reading_v1.json` remains unchanged for task compatibility. A new versioned
`reading_v2.json` adds five original passages:

1. Urban shade mapping — Cities / Environment
2. Repairable modular electronics — Technology / Business
3. Productive uncertainty in classrooms — Education / Psychology
4. Mycelium-based acoustic materials — Engineering / Science
5. Night-shift light design — Psychology / Engineering

Each new passage contains 750–950 original words and 10 questions. Across the
five passages, all three supported types are represented with unambiguous
answers, explanations, and exact evidence. The combined catalog contains eight
passages and 77 questions.

## PWA Boundary

Static serving exposes a manifest and original 192, 512, maskable, Apple touch,
and favicon assets. A small metadata component installs manifest/theme/mobile
meta tags into the host document. No service worker is registered, so the
documentation promises “Add to Home Screen” only, not offline operation or a
native application.

## Testing and Rollback

Every behavior change follows red-green-refactor. Tests cover state helpers,
page behavior, navigation uniqueness, content structure, manifest and image
dimensions, privacy, exporter preservation, compileall, and the full suite.
Visual acceptance uses a temporary database, Mock mode, and browser viewport
checks at 375, 430, 768, 1024, and desktop width.

Each phase creates a local commit. Rollback is phase-scoped with
`git revert <commit>`; destructive reset, clean, force push, and database
rollback are not used.
