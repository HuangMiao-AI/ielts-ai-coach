# UI Exam PWA V1 Progress

Last updated: 2026-07-19

## Current Stage

Stage 0 — read-only audit and implementation planning.

## Completed

- Confirmed clean source branch `feature/obsidian-exporter-v1`.
- Created local branch `feature/ui-exam-pwa-v1`.
- Recorded source HEAD `bfbd45fbde3262f8a639cad40bdc60b8f3368bba`.
- Audited navigation, Reading persistence, Writing, Listening, Speaking,
  responsive CSS, Streamlit 1.59.2 capabilities, tests, and startup.
- Confirmed no database schema change is required.
- Confirmed existing bank has 3 original passages and 27 questions.

## Test Results

- Full pytest baseline: 128 passed.
- Compileall baseline: passed.
- Real database, WAL, and backup fingerprints: unchanged after baseline tests.
- External AI calls: none.

## Current Commit

`bfbd45fbde3262f8a639cad40bdc60b8f3368bba`

## Next Step

Commit the approved design, implementation plan, and this progress record.
Then begin Stage 1 with failing tests for design tokens and responsive rules.

## Known Issues

- Mobile navigation duplicates the full primary menu.
- Reading is embedded inside Today and drafts are session-only.
- Listening and Speaking lack standalone interactive pages.
- Writing drafts are not isolated by task type.
- Current CSS lacks safe-area and reduced-motion behavior.
- PWA metadata and install icons do not exist.
- Existing three-passage validator must become a multi-bank catalog without
  breaking v1 tasks.
