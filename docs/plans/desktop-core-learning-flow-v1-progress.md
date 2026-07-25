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
- [x] Phase 4: plan-independent Reading library
- [x] Phase 5: original Listening mini tests and offline audio
- [x] Phase 6: Writing save-only fallback
- [x] Phase 7: Speaking microphone recovery and text fallback
- [ ] Phase 8: desktop UI and responsive contracts
- [ ] Phase 9: browser flows and full verification
- [ ] Phase 10: real database additive apply and final handover

## Current Evidence

- Targeted Phase 0 tests: 10 passed
- Baseline complete pytest: passed
- Phase 1 focused schema/compatibility regression: 21 passed
- Phase 2 onboarding/profile/navigation regression: 28 passed
- Phase 3 planning/Home/Analytics/end-to-end regression: 59 passed
- Phase 4 Reading library and plan regression: 19 passed
- Phase 4 question bank, scoring, exam state, and exporter regression:
  67 passed
- All 8 versioned original Reading passages are visible without an active
  seven-day plan
- Starting a passage creates or reuses a user-owned internal library task;
  internal library containers are excluded from plan history
- Reading task lookup and saved state remain strictly scoped by `user_id`
- Phase 5 Listening bank, scoring, page, and shared-session regression:
  10 passed
- Listening V1 contains 2 project-original tests, 2 sections and 16 questions
  per test, covering multiple choice, form completion, and note completion
- Local Windows SAPI generated 2 committed PCM WAV files without network TTS:
  131.2 seconds and 126.2 seconds
- Listening submission enforces complete answers and shows deterministic
  per-question explanations and script evidence only after confirmation
- Listening answers and scores are user/test-scoped Streamlit session state;
  no database or Analytics persistence is claimed
- Phase 6 save-only, editor, existing evaluation, and provider regression:
  14 passed
- Writing offers 4 project-original prompts covering Academic/General Task 1
  and Task 2, with timing and minimum-word metadata
- Mock/no-key student submissions persist as `Essay(status="saved")` without
  `WritingFeedback`, provider calls, or `AIUsageDaily` quota changes
- Local word/paragraph/structure observations are explicitly non-scoring;
  any separately rendered Mock feedback is labeled `Demo feedback`
- Phase 7 microphone fallback, Speaking page, and shared-session regression:
  7 passed
- Speaking provides first-use microphone guidance, a browser-permission
  recovery path, and a session-only text-answer alternative
- Completion accepts a local recording or a non-empty text answer and never
  claims recognition, pronunciation analysis, or an IELTS score
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
