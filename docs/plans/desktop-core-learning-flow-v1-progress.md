# Desktop Core Learning Flow V1 Progress

Updated: 2026-07-25

## Branch

- Source: `feature/ai-learning-analytics-v1`
- Source commit: `c930662`
- Active: `fix/desktop-core-learning-flow-v1`
- Remote operations: none

## Baseline

- Full pytest: 204 passed
- Real DB/WAL/SHM and backup hashes recorded before Phase 0
- Phase 0 used a fictional account and isolated temporary database
- Real database family remained byte-identical after Phase 0

## Approved Schema Boundary

- Only new table: `learner_profiles_v2`
- No ALTER, DROP, RENAME, table rebuild, or startup backfill
- Missing optional bands: SQL `NULL` / Python `None`
- Existing `score_records`: complete real score sets only

## Phase Status

- [x] Phase 0: read-only audit and reproduction
- [x] Phase 1: additive schema and compatibility layer
- [x] Phase 2: onboarding and editable profile/settings
- [x] Phase 3: baseline-aware plans and independent skill actions
- [ ] Phase 4: plan-independent Reading library
- [ ] Phase 5: original Listening mini tests and offline audio
- [ ] Phase 6: Writing save-only fallback
- [ ] Phase 7: Speaking microphone recovery and text fallback
- [ ] Phase 8: desktop UI and responsive contracts
- [ ] Phase 9: browser flows and full verification
- [ ] Phase 10: real database additive apply and final handover

## Current Evidence

- Targeted Phase 0 tests: 10 passed
- Baseline complete pytest: passed
- Phase 1 focused schema/compatibility regression: 21 passed
- Phase 2 onboarding/profile/navigation regression: 28 passed
- Phase 3 planning/Home/Analytics/end-to-end regression: 59 passed
- Complete, partial, and empty baselines generate deterministic plans without
  creating synthetic `score_records`
- Partial baselines appear as latest values without fabricated trends or an
  incomplete overall band
- Home recommends plan generation without making score entry a prerequisite
- New users complete four explicit steps, may omit date and every band, and
  are switched to Home after an explicit save
- Profile and Settings share the same user-scoped optional-band editor
- Repeated `create_all` on temporary SQLite: idempotent
- Real DB/WAL/SHM byte-copy rehearsal: exactly one new empty table
- Copy rehearsal preserved all 11 old table definitions, row counts, and
  canonical content hashes
- No production code changed before design and schema approval
- No real AI or external TTS call made
