# Desktop Core Learning Flow V1 Design

## Status

Approved in conversation on 2026-07-25, including the single additive
`learner_profiles_v2` table. Implementation must continue through Phases 1–10
without further approval for that table.

## Goal

Turn the existing desktop application into a usable independent four-skill
learning flow while preserving Reading scoring, Writing history, Analytics,
the premium glass UI, authentication, and Obsidian Exporter behavior.

## Baseline

- Source branch: `feature/ai-learning-analytics-v1`
- Feature branch: `fix/desktop-core-learning-flow-v1`
- Source commit: `c930662`
- Baseline: 204 pytest tests pass
- Existing schema: 11 tables
- Reading catalog: eight original passages and 77 questions
- Listening: transient Demo without bundled audio or scoring
- Writing: fixed Mock feedback when no API key is configured
- Speaking: session timers, notes, and browser recording

## Hard Constraints

- Add only `learner_profiles_v2`; do not alter, drop, rename, or rebuild an
  existing table.
- Do not batch backfill old users.
- Do not write onboarding baselines to `score_records`.
- Do not invent missing dates, bands, trends, scores, streaks, or skill claims.
- Every database read and write is scoped by authenticated `user_id`.
- Do not call a real Qwen, OpenAI, Claude, or external TTS API.
- Do not operate Obsidian, Sync, Feishu, deployment, remotes, or GitHub.
- Do not push or merge to `main`.
- Preserve all existing user records and protected workflows.
- Student-facing copy remains Simplified Chinese.

## Phase 0 Findings

The current application routes a registered user to the profile page, but
saving the profile leaves the user on `/profile`. The profile is one long form,
has no score fields, and requires an exam date. The score page requires all four
bands and defaults new forms to 6.0. Plan generation requires a complete score
record. Reading only lists Reading tasks from an active plan. Listening has no
audio or score. Writing uses fixed Mock feedback when no key is present.
Speaking lacks a first-use microphone test and a text fallback.

The existing `student_profiles.exam_date` and every `score_records` band are
non-null. Honest optional dates and partial baselines therefore require a new
data contract rather than placeholders.

## Data Contract

`learner_profiles_v2` is the only new table:

```text
id                         INTEGER primary key
user_id                    INTEGER not null, unique, FK users.id CASCADE
display_name               VARCHAR(40) not null
current_grade              VARCHAR(30) not null
exam_date                  DATE nullable
daily_study_minutes        INTEGER not null
target_overall_band        FLOAT not null
current_reading_band       FLOAT nullable
current_listening_band     FLOAT nullable
current_writing_band       FLOAT nullable
current_speaking_band      FLOAT nullable
onboarding_completed       BOOLEAN not null
created_at                 DATETIME not null
updated_at                 DATETIME not null
```

Database constraints enforce daily minutes from 15 through 480, target band
from 0 through 9 in half-band increments, and each optional current band from
0 through 9 in half-band increments when present.

Missing bands are stored as SQL `NULL` and represented in Python as `None`.
Zero is a real band and must never mean missing. Target band is not a current
band. No default current band exists.

## Compatibility Read Priority

The application resolves one immutable learner-profile snapshot:

1. If a user-owned `learner_profiles_v2` row exists, use it exclusively.
2. Otherwise, adapt the user-owned legacy `student_profiles` row.
3. For that legacy adapter only, use the newest real `score_records` row when
   it exists; otherwise all current bands are `None`.
4. Never create a V2 row during reads or application startup.
5. A legacy user receives a V2 row only after actively saving Profile.

Legacy profile fields remain untouched. Legacy score records remain historical
complete score records.

## Onboarding and Profile

New users follow four steps in one route:

1. display name and grade;
2. optional Listening, Reading, Writing, and Speaking baselines;
3. target band, optional exam date, and daily study minutes;
4. review and save.

Saving writes one V2 row, marks onboarding complete, shows success feedback,
and switches to Home. Refresh resolves the persisted V2 row and does not return
the user to onboarding.

Profile and Settings expose the same editable learning settings. A legacy user
is shown adapted legacy values; saving creates the first V2 row. Optional bands
remain independently nullable.

## Plan and Skill Independence

The four skill routes are always available. Plans are recommendations and
schedules, never permissions.

Plan generation accepts:

- complete baselines: weight all measured gaps;
- partial baselines: weight known gaps and label unknown skills as missing;
- no baselines: generate a balanced exploration plan;
- no exam date: use the foundation phase without inventing a date.

The UI explicitly identifies missing evidence. It never inserts a synthetic
score record.

## Reading

The Reading route always lists all eight original passages with topic, version,
question count, estimated time, and latest status. Starting an unlinked passage
creates an internal user-owned library task in the existing plan/task tables.
The internal container has a non-active library status and is excluded from
visible study-plan history. This avoids another schema change while retaining
the existing immutable attempt, score, review, study-log, and exporter
contracts.

Existing plan-linked attempts continue to work. Scoring, normalization,
submission locking, explanations, evidence, and user isolation do not change.

## Listening

Listening V1 contains two project-original Academic mini tests. Each test has
two sections and 16 questions. Supported types are Multiple Choice, Form
Completion, and Note/Sentence Completion.

Versioned JSON stores scripts, questions, options, answers, explanations, and
evidence. Two committed WAV files are generated locally with Windows offline
speech synthesis. The player uses bundled static files and requires no network.

Listening answers and deterministic results are session-scoped in this phase
because no second attempt table is approved. The page supports test selection,
audio playback, section/question navigation, unanswered checks, confirmation,
deterministic scoring, and review. It makes no persistence or granular
Analytics claim.

## Writing

Bundled original Task 1 and Task 2 prompts are selectable. The editor retains
word count, timer, user/task-scoped draft state, confirmation, and history.

When the configured provider resolves to Mock, the normal student action saves
the essay without feedback or quota use. Its status is `saved`, and the exact
message is:

```text
作文已保存。AI评分当前未启用。
```

Local checks may report word count, paragraph count, recommended length, and
simple structural observations, but never a band. Fixed Mock feedback remains
available only through explicitly labeled test/demo behavior and is displayed
as `Demo feedback`.

## Speaking

Speaking keeps Part 1/2/3 prompts, Part 2 preparation, response timing, notes,
recording, and playback. First use presents a microphone test and permission
guidance. A visible failure/denial path explains browser settings and enables a
text-answer alternative. Completion accepts either a recording or non-empty
text alternative. No recognition, pronunciation score, band, upload, or AI
claim is added.

## Home and Desktop UI

The existing premium glass design and one navigation model remain. Home shows
four prominent independent skill actions even when no plan or scores exist.
The no-plan state offers plan generation without blocking those actions.

Desktop verification targets 1366×768, 1440×900, and 1920×1080. Responsive
regression targets 375, 430, 768, and 1024 pixels. Cards must not overlap,
overflow horizontally, hide actions, or duplicate the four primary entries.

## Database Protection

All schema work is proven first on a temporary database and a byte-for-byte
copy of the real database family. Before the real `create_all` call:

- copy DB, WAL, and SHM into an ignored timestamped backup directory;
- record sizes and SHA-256 hashes;
- record old table names, SQL definitions, row counts, and canonical row
  fingerprints;
- do not execute `VACUUM`, checkpoint, migration, table rebuild, or data update.

After `create_all`, verify the only new table is `learner_profiles_v2`, all old
definitions/counts/content fingerprints are unchanged, and no V2 user rows
were backfilled. WAL/SHM byte changes caused by the additive DDL are reported
separately from business-data integrity.

## Test and Commit Strategy

Every behavior follows RED → GREEN → REFACTOR. Each phase updates
`docs/plans/desktop-core-learning-flow-v1-progress.md`, runs focused tests, and
ends in a local commit. Final verification includes complete pytest,
compileall, pip check, headless Streamlit health checks, browser flows,
responsive viewports, Git review, privacy scanning, and database comparison.

No remote operation is part of this design.
