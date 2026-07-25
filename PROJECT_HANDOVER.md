# IELTS AI Coach Handover

Updated: 2026-07-25

## Active branch

`fix/desktop-core-learning-flow-v1` is based on
`feature/ai-learning-analytics-v1`. It remains local: do not merge to `main`
or push without separate approval.

## Completed desktop core learning flow

- New users complete a persistent four-step onboarding flow and may leave the
  exam date and all current bands empty.
- Profile and Settings use the same user-scoped learner-profile editor.
- Plans handle complete, partial, and empty baselines without writing synthetic
  score records.
- Reading is available as an independent original-content library, even before
  a plan exists. Submission creates a user-owned internal library task only
  when necessary.
- Listening offers two original, offline mini tests with two sections and
  deterministic post-submit review. It is session-only by design.
- Writing offers four original prompts. In no-key/Mock mode it saves an essay
  with `status="saved"` and does not create feedback, consume AI quota, or
  display an estimated band.
- Speaking provides microphone guidance and a text fallback. Audio/text is
  session-only and no automatic score, recognition, or pronunciation claim is
  made.
- Home has one four-skill entry group with no-plan guidance that does not block
  practice. Responsive contracts cover phone through wide desktop widths.

## Learner profile V2 data contract

Only one table was added: `learner_profiles_v2`.

- `user_id` is unique and foreign-keyed to `users`.
- Other fields are `display_name`, `current_grade`, nullable `exam_date`,
  `daily_study_minutes`, `target_overall_band`, nullable current Reading,
  Listening, Writing, and Speaking bands, `onboarding_completed`,
  `created_at`, and `updated_at`.
- Present bands are constrained to 0–9 in 0.5 increments. All four may be
  null, partially supplied, or fully supplied.
- `NULL` / `None` is the only missing-band representation. A real `0` is
  never treated as missing.
- The compatibility service reads V2 first, then the legacy
  `student_profiles` row only if V2 is absent. It never turns targets or
  placeholder values into achieved scores.
- No startup backfill exists. Saving an old user's profile is the only path
  that creates that user's V2 row.
- `score_records` remains for complete real scores only.

No old table or field was altered, dropped, renamed, rebuilt, or bulk-updated.

## Database application record

The application database is `data/ielts_ai_coach.db`. Before the additive
operation, its DB, WAL, and SHM files were copied into the ignored runtime
backup directory. A copied database rehearsal added exactly one empty table
and preserved every old table's schema, row count, and canonical content hash.

The real additive apply then produced the same result:

- old tables before/after: 11 / 11, with schema, row count, and canonical
  content hashes unchanged;
- new table: `learner_profiles_v2`, with zero rows;
- no `ALTER`, `DROP`, `RENAME`, rebuild, bulk backfill, or explicit
  `wal_checkpoint` command was executed.

The SQLite main-file hash changed because the new table was added. SQLite
consolidated pre-existing WAL contents into the main file while the schema
connection closed; this is visible in the DB/WAL size changes. It did not
change logical old-table contents, which were verified from before/after
inventories. The original DB/WAL/SHM triplet is retained in the ignored backup
directory.

## Verification

- Full pytest: 247 passed.
- `compileall`: passed.
- `pip check`: passed.
- Streamlit temporary-database smoke run: health endpoint returned `ok`.
- Browser smoke run: registration, onboarding, Home, Reading library, local
  Listening audio element, Writing save-only confirmation, and Speaking
  microphone-failure fallback were checked using a fictional account.
- Responsive browser checks at 375, 430, 768, 1024, 1366, 1440, and 1920 px
  found no horizontal overflow.
- No real AI API, external TTS, Obsidian operation, remote push, or deployment
  was performed.

## Known limitations and next sensible step

Listening and Speaking practice remains session-only. Speaking has no scoring
or transcript analysis. The next approved feature should be persistence and
analytics for Listening/Speaking only after a separate privacy and data-model
approval; do not infer those skills from plan completion.
