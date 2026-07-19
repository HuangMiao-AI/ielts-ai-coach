# UI Exam PWA V1 Progress

Last updated: 2026-07-19

## Current Stage

Stage 3 — dedicated Reading exam state machine.

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

## Current Commit

`0eac9cb` (before the pending Stage 2 commit)

## Next Step

Commit Stage 2, then begin the Reading exam state machine with pure failing
tests before changing the current reading flow.

## Known Issues

- Reading is embedded inside Today and drafts are session-only.
- Listening and Speaking lack standalone interactive pages.
- Writing drafts are not isolated by task type.
- PWA metadata and install icons do not exist.
- Existing three-passage validator must become a multi-bank catalog without
  breaking v1 tasks.
