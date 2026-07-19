# UI Exam PWA V1 Progress

Last updated: 2026-07-19

## Current Stage

Stage 2 — responsive navigation shell implementation.

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

## Test Results

- Full pytest baseline: 128 passed.
- Compileall baseline: passed.
- Real database, WAL, and backup fingerprints: unchanged after baseline tests.
- External AI calls: none.
- Stage 1 focused pytest: 5 passed.
- Stage 1–2 focused regression: 9 passed.

## Current Commit

`7f1c6d3` (before the pending Stage 1 commit)

## Next Step

Commit Stage 1, finish the shared navigation modules and page shells, then
run the complete navigation/authentication regression before the Stage 2
commit.

## Known Issues

- Reading is embedded inside Today and drafts are session-only.
- Listening and Speaking lack standalone interactive pages.
- Writing drafts are not isolated by task type.
- PWA metadata and install icons do not exist.
- Existing three-passage validator must become a multi-bank catalog without
  breaking v1 tasks.
