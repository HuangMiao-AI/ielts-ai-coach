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
- [ ] Phase 1: additive schema and compatibility layer
- [ ] Phase 2: onboarding and editable profile/settings
- [ ] Phase 3: baseline-aware plans and independent skill actions
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
- No production code changed before design and schema approval
- No real AI or external TTS call made
