# UI Exam PWA V1 Progress

Last updated: 2026-07-19

## Current Stage

Stage 8–9 — automated regression and visual acceptance.

## Completed

- Confirmed clean source branch `feature/obsidian-exporter-v1`.
- Created local branch `feature/ui-exam-pwa-v1`.
- Recorded source HEAD `bfbd45fbde3262f8a639cad40bdc60b8f3368bba`.
- Audited navigation, Reading persistence, Writing, Listening, Speaking,
  responsive CSS, Streamlit 1.59.2 capabilities, tests, and startup.
- Confirmed no database schema change is required.
- Confirmed existing bank has 3 original passages and 27 questions.
- Completed Stage 1 shared design tokens, glass surfaces, safe-area spacing,
  reduced-motion support, and escaped UI components.
- Replaced `overflow-x: clip` with explicit page containment and scrollable
  data surfaces.
- Completed Stage 2 with one hidden route registry, desktop sidebar, mobile
  bottom bar, one More panel, and dedicated Reading/Listening/Speaking shells.
- Kept Scores, Today, AI Coach, and Settings available as contextual routes.
- Preserved the existing Today-to-Writing handoff.
- Completed Stage 3 with an immutable Reading state machine, stable timer,
  user/task-scoped session draft, numbered navigation, article/question modes,
  explicit confirmation, persisted deterministic result, and locked review.
- Today now hands structured Reading tasks to the dedicated exam route.
- History can reopen complete explanations from the stored result snapshot.
- Kept the recovery boundary explicit: unfinished drafts remain session-only.
- Completed Stage 4 with five new project-original Academic passages and 50
  new questions across Cities, Technology, Education, Materials, and
  night-shift design topics.
- Added a stable eight-passage catalog with 77 globally unique questions.
- Preserved v1 lookup for stored tasks while new plans rotate through v1/v2
  and generate accurate 9/10-question instructions.
- Updated both README files with the expanded bank and non-official copyright
  boundary.
- Completed Stage 5 with an honest Listening Demo flow that never persists or
  claims a score.
- Writing now uses live word count, user/Task-scoped drafts, stable edit time,
  clear/submit confirmation, and duplicate-click protection while preserving
  the existing provider, quota, feedback, and history services.
- Speaking now provides Part 1/2/3 prompts, preparation/response timers,
  session notes, browser-local recording/playback, and explicit no-score copy.
- Completed Stage 6 with one read-only Home snapshot for streak, latest
  Reading/Writing, weak sections, today's tasks, plan preview, activity, and
  deterministic recommended route.
- Home now shows four skill shortcuts and honest empty states using only
  current-user records.
- Completed Stage 7 with a local manifest, deterministic SVG/PNG icons,
  mobile metadata, safe-area-aware shell, and Streamlit static serving.
- No service worker is registered; this release does not claim offline use.

## Test Results

- Full pytest baseline: 128 passed.
- Compileall baseline: passed.
- Real database, WAL, and backup fingerprints: unchanged after baseline tests.
- External AI calls: none.
- Stage 1 focused pytest: 5 passed.
- Stage 1–2 focused regression: 9 passed.
- Stage 2 navigation/app/auth regression: 19 passed.
- Full pytest after Stage 2: 135 passed.
- Compileall after Stage 2: passed.
- Real database, WAL, and backup fingerprints: unchanged.
- Stage 3 Reading/task/history regression: 26 passed.
- Full pytest after Stage 3: 140 passed.
- Compileall after Stage 3: passed.
- Real database, WAL, and backup fingerprints: unchanged after Stage 3.
- Stage 4 content/compatibility regression: 27 passed.
- Full pytest after Stage 4: 144 passed.
- Compileall after Stage 4: passed.
- Real database, WAL, and backup fingerprints: unchanged after Stage 4.
- Stage 5 route/provider/privacy regression: 21 passed.
- Full pytest after Stage 5: 150 passed.
- Compileall after Stage 5: passed.
- Real database, WAL, and backup fingerprints: unchanged after Stage 5.
- Stage 6 Home/dashboard/ownership regression: 12 passed.
- Full pytest after Stage 6: 153 passed.
- Compileall after Stage 6: passed.
- Real database, WAL, and backup fingerprints: unchanged after Stage 6.
- Stage 7 PWA/app/config regression: 10 passed.
- Full pytest after Stage 7: 157 passed.
- Compileall after Stage 7: passed.
- Real database, WAL, and backup fingerprints: unchanged after Stage 7.

## Current Commit

`abfd153` (before the pending Stage 7 commit)

## Next Step

Commit Stage 7, then run the complete automated matrix, browser viewport
acceptance, headless startup, HTTP health, pip check, and asset verification.

## Known Issues

- Reading drafts are session-only and are lost when the browser session ends.
