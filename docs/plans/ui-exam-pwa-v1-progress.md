# UI Exam PWA V1 Progress

Last updated: 2026-07-19

## Current Stage

Stage 4 — expand the original Academic Reading bank.

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

## Current Commit

`e112c3c` (before the pending Stage 3 commit)

## Next Step

Commit Stage 3, then write failing multi-bank catalog and content-quality
tests before adding the five new original passages.

## Known Issues

- Reading drafts are session-only and are lost when the browser session ends.
- Listening and Speaking lack standalone interactive pages.
- Writing drafts are not isolated by task type.
- PWA metadata and install icons do not exist.
- Existing three-passage validator must become a multi-bank catalog without
  breaking v1 tasks.
