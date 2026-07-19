# Obsidian Exporter V1 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build a privacy-preserving, user-scoped, deterministic one-way exporter from IELTS AI Coach SQLite records to Miao OS AI Feedback Markdown.

**Architecture:** A read-only repository selects one user's finalized reading attempts and writing feedback. Explicit allowlist transforms create strict Pydantic `FeedbackExportRecord` values, which adapters render deterministically; a service coordinates dry-run/apply, fingerprints, state, conflict detection, logging, and atomic writes without modifying the source database.

**Tech Stack:** Python 3.12, SQLAlchemy 2.0, SQLite WAL, Pydantic 2, pytest 8, UTF-8 Markdown, JSON state.

## Global Constraints

- The active project is `<PROJECT_ROOT>`; use only root `app.py` and `ielts_ai_coach/`.
- Never import or modify `archive/enterprise-v0/`, `data/study_coach.db`, or inactive root legacy modules.
- Never modify the real SQLite database, schema, WAL, or SHM; never run a checkpoint.
- Every business query requires one explicit `user_id`; no all-users export path exists.
- Reading and writing are the only V1 export sources.
- Never export passwords, tokens, API keys, identity/profile details, essays, prompts, complete answers, coach conversations, raw metadata, errors, quotas, or absolute database paths.
- Dry-run is the default; only `--apply` may write Markdown, state, or logs.
- This implementation must not run `--apply` against the real Miao OS Vault.
- Session dates use `Asia/Shanghai`; historical `coach_version` remains empty when it was not persisted at generation time.
- Generated Markdown is deterministic and contains no export-run timestamp.
- Existing user-modified or missing output is a conflict and is never overwritten or recreated automatically.
- No `--force-overwrite`, external AI call, Feishu connection, Sync change, Obsidian plugin change, or Git push.

---

## Target File Map

### Project files

- Create `ielts_ai_coach/exporting/contracts.py`: strict versioned DTOs and result summaries.
- Create `ielts_ai_coach/exporting/enums.py`: source, skill, method, status, action, and exit-code enums.
- Create `ielts_ai_coach/exporting/errors.py`: safe typed exporter errors.
- Create `ielts_ai_coach/exporting/privacy.py`: immutable export allowlists and forbidden-name checks.
- Create `ielts_ai_coach/exporting/source_repository.py`: read-only SQLite/SQLAlchemy user-scoped queries and minimal user listing.
- Create `ielts_ai_coach/exporting/transform.py`: explicit reading/writing source-to-DTO mapping and deterministic text rules.
- Create `ielts_ai_coach/exporting/fingerprint.py`: canonical JSON and SHA-256 helpers over allowlisted DTO fields.
- Create `ielts_ai_coach/exporting/filename.py`: stable safe relative output paths.
- Create `ielts_ai_coach/exporting/obsidian_renderer.py`: fixed-order YAML and Markdown rendering.
- Create `ielts_ai_coach/exporting/state.py`: versioned per-user JSON state and atomic persistence.
- Create `ielts_ai_coach/exporting/atomic_writer.py`: same-directory temporary file and `os.replace`.
- Create `ielts_ai_coach/exporting/service.py`: planning state machine and export orchestration.
- Create `ielts_ai_coach/exporting/cli.py`: `list-users`, `validate-config`, `show-state`, and `export`.
- Create `ielts_ai_coach/exporting/adapters/base.py`: `ExportAdapter` protocol/ABC.
- Create `ielts_ai_coach/exporting/adapters/feishu_stub.py`: no-network unsupported adapter.
- Modify `.gitignore`: ignore `data/export_state/` and `data/export_logs/`.
- Modify `.memory.md`: record the final architecture, safety boundary, and verified test count.

### Vault files

- Modify `99 Templates/README.md`: register `ai-coach-feedback` schema and enums.
- Create `99 Templates/AI Coach Feedback Template.md`: field reference template.
- Create `02 IELTS/AI Feedback/README.md`: managed-directory and conflict guidance.
- Create `05 IELTS AI Coach/Architecture/Data Contract.md`: full contract and privacy/version rules.
- Modify `00 Dashboard/Dashboard.md`: one bounded ordinary Dataview DQL query.

## Data Contract

`FeedbackExportRecord` uses `ConfigDict(extra="forbid", frozen=True)` and contains:

```python
schema_version: Literal[1]
type: Literal["ai-coach-feedback"]
source_system: Literal["ielts-ai-coach"]
source_entity: SourceEntity
source_record_id: int
session_date: date
generated_at: datetime
coach_version: str | None
exporter_version: Literal["1.0.0"]
skill: Skill
feedback_method: FeedbackMethod
provider: str | None
model_name: str | None
feedback_status: FeedbackStatus
overall_summary: tuple[str, ...]
strengths: tuple[str, ...]
weaknesses: tuple[str, ...]
recommendations: tuple[str, ...]
detailed_feedback: tuple[FeedbackDetail, ...]
rewrite_example: str | None
disclaimer: str | None
source_note: str | None
test: bool
tags: tuple[str, ...]
```

Only the short metadata fields are serialized to YAML. Narrative fields render under fixed Markdown headings.

## CLI Design

```text
python -m ielts_ai_coach.exporting.cli list-users --database <path>
python -m ielts_ai_coach.exporting.cli validate-config --database <path> --vault <path>
python -m ielts_ai_coach.exporting.cli show-state --state-path <path> --user-id <id>
python -m ielts_ai_coach.exporting.cli export --database <path> --vault <path>
  --user-id <id> --source reading|writing|all --limit <n>
  --timezone Asia/Shanghai --dry-run|--apply --test
  --state-path <path> --log-path <path>
```

Dry-run is implicit unless `--apply` is supplied. `--dry-run` and `--apply` are mutually exclusive. `--test` is rejected for the configured real database path.

## State and Conflict Model

State uses `data/export_state/obsidian-user-<id>.json` by default, with a versioned root object and entries keyed by `<source_entity>:<source_record_id>`. Each entry stores only the source key, allowlist fingerprint, relative path, last exported file hash, and state-only export timestamp.

The service implements:

- `CREATE`: no state and no target.
- `SKIP_UNCHANGED`: unchanged source and unchanged target.
- `SAFE_UPDATE`: changed source, target still matches last generated bytes.
- `CONFLICT_USER_MODIFIED`: target differs from last generated hash.
- `CONFLICT_OUTPUT_MISSING`: state exists but target is missing.
- `CONFLICT_SOURCE_KEY`: existing target frontmatter identifies another source.
- `WRITE_FAILED`: atomic write failed; state remains unchanged.

## Rollback

- Project changes live only on local branch `feature/obsidian-exporter-v1`; no push occurs.
- Commits are small and can be reverted independently.
- Vault Markdown is backed up under `10 Archive/System Backups/<timestamp>/Phase 3 Exporter V1/` with a SHA-256 manifest before modification.
- No real exported feedback note is created, so Vault rollback only restores the five integration/documentation Markdown files.
- State and logs are runtime ignored files; deleting test copies does not affect source data.

## Feishu Boundary

`ExportAdapter` consumes only `FeedbackExportRecord`. `FeishuAdapterStub` validates the record and raises a safe unsupported error for preview/apply; it imports no HTTP client, reads no token, and never accesses ORM or SQLite. A future adapter may send summaries and recommendations, not essays or complete answers.

---

### Task 1: Freeze contracts, enums, privacy rules, and source repository

**Files:**
- Create: `ielts_ai_coach/exporting/__init__.py`
- Create: `ielts_ai_coach/exporting/contracts.py`
- Create: `ielts_ai_coach/exporting/enums.py`
- Create: `ielts_ai_coach/exporting/errors.py`
- Create: `ielts_ai_coach/exporting/privacy.py`
- Create: `ielts_ai_coach/exporting/source_repository.py`
- Test: `tests/exporting/test_contracts.py`
- Test: `tests/exporting/test_privacy.py`
- Test: `tests/exporting/test_source_repository.py`
- Test: `tests/exporting/test_real_schema_compatibility.py`

**Interfaces:**
- Produces: `FeedbackExportRecord`, `FeedbackDetail`, `ReadingSourceRecord`, `WritingSourceRecord`, `ExportUserSummary`.
- Produces: `list_exportable_reading_attempts(...)`, `list_exportable_writing_feedback(...)`, `list_export_users(...)`.
- Consumes: existing SQLAlchemy models and a supplied `sessionmaker[Session]`.

- [ ] Write failing contract tests for literals, enums, `extra="forbid"`, integer IDs, UTC-aware timestamps, and boolean `test`.
- [ ] Write failing privacy tests that inspect DTO fields and rendered source records for every forbidden name.
- [ ] Write failing repository tests proving user isolation, starting ID, source limit, and minimal user summaries.
- [ ] Implement the strict DTOs, enums, safe errors, and explicit source-record dataclasses.
- [ ] Implement repository queries with `user_id` predicates and no unrestricted export function.
- [ ] Configure SQLite export engines with URI `mode=ro`, `PRAGMA query_only=ON`, five-second busy timeout, and bounded connect retry without WAL checkpoint.
- [ ] Run `pytest tests/exporting/test_contracts.py tests/exporting/test_privacy.py tests/exporting/test_source_repository.py tests/exporting/test_real_schema_compatibility.py -v`.
- [ ] Commit as `feat: add exporter contracts and read-only sources`.

### Task 2: Transform and render deterministic feedback

**Files:**
- Create: `ielts_ai_coach/exporting/transform.py`
- Create: `ielts_ai_coach/exporting/fingerprint.py`
- Create: `ielts_ai_coach/exporting/filename.py`
- Create: `ielts_ai_coach/exporting/obsidian_renderer.py`
- Create: `ielts_ai_coach/exporting/adapters/__init__.py`
- Create: `ielts_ai_coach/exporting/adapters/base.py`
- Create: `ielts_ai_coach/exporting/adapters/feishu_stub.py`
- Test: `tests/exporting/test_transform_reading.py`
- Test: `tests/exporting/test_transform_writing.py`
- Test: `tests/exporting/test_filename.py`
- Test: `tests/exporting/test_renderer.py`

**Interfaces:**
- Consumes: source dataclasses from Task 1.
- Produces: `transform_reading(...)`, `transform_writing(...)`, `source_fingerprint(...)`, `output_relative_path(...)`, `ObsidianMarkdownAdapter`.

- [ ] Write failing reading tests for Shanghai date conversion, type-grouped weaknesses, deterministic recommendations, perfect-score wording, and omission of user answers.
- [ ] Write failing writing tests for rubric scores, strengths/issues/suggestions, rewrite example, empty historical coach version, and omission of essay/prompt.
- [ ] Write failing filename and renderer tests for fixed YAML order, true booleans, integer IDs, ISO values, UTF-8, stable bytes, and source-key parsing.
- [ ] Implement explicit transforms that select only allowlisted source fields.
- [ ] Implement canonical JSON fingerprints over `FeedbackExportRecord` source content, excluding run time and output path.
- [ ] Implement Windows/iOS-safe stable relative paths, preferring an existing state path.
- [ ] Implement the fixed-order YAML serializer and Markdown sections without adding a general YAML parser.
- [ ] Implement the adapter interface and no-network Feishu stub.
- [ ] Run the focused transform/renderer tests.
- [ ] Commit as `feat: render deterministic Obsidian feedback`.

### Task 3: State, atomic writer, idempotency, and conflict protection

**Files:**
- Create: `ielts_ai_coach/exporting/state.py`
- Create: `ielts_ai_coach/exporting/atomic_writer.py`
- Create: `ielts_ai_coach/exporting/service.py`
- Test: `tests/exporting/test_state.py`
- Test: `tests/exporting/test_atomic_writer.py`
- Test: `tests/exporting/test_idempotency.py`
- Test: `tests/exporting/test_conflicts.py`
- Test: `tests/exporting/test_end_to_end_export.py`

**Interfaces:**
- Consumes: records, renderer, fingerprint, relative paths.
- Produces: `load_state(...)`, `save_state(...)`, `atomic_write_text(...)`, `ExportService.plan(...)`, `ExportService.execute(...)`.

- [ ] Write failing tests for stable JSON, per-user isolation, corrupt-state refusal, and atomic state replacement.
- [ ] Write failing tests for all seven state-machine outcomes and temp cleanup.
- [ ] Write a failing end-to-end test using a temporary SQLite database and temporary Miao-shaped Vault.
- [ ] Implement state models and atomic JSON persistence.
- [ ] Implement same-directory Markdown temporary writes with flush, fsync, close, and `os.replace`.
- [ ] Implement Vault marker validation for `00 Dashboard`, `02 IELTS`, and `99 Templates`.
- [ ] Implement dry-run planning with zero filesystem mutations.
- [ ] Implement apply execution that updates state only after successful Markdown writes and continues after conflicts.
- [ ] Run state, conflict, and end-to-end tests.
- [ ] Commit as `feat: add safe exporter state and conflict handling`.

### Task 4: CLI, safe logs, and runtime configuration

**Files:**
- Create: `ielts_ai_coach/exporting/cli.py`
- Modify: `.gitignore`
- Test: `tests/exporting/test_cli.py`

**Interfaces:**
- Consumes: repository factories and `ExportService`.
- Produces: executable `python -m ielts_ai_coach.exporting.cli`.

- [ ] Write failing CLI tests for help, subcommands, missing user ID, no all-users option, default dry-run, flag conflicts, real-database test rejection, safe summaries, and exit codes.
- [ ] Write failing log tests that reject forbidden content and absolute database paths.
- [ ] Implement argparse subcommands and explicit exit-code mapping.
- [ ] Implement minimal rotating logging with safe structured fields only.
- [ ] Add `data/export_state/` and `data/export_logs/` to `.gitignore`.
- [ ] Run CLI tests and `python -m ielts_ai_coach.exporting.cli --help`.
- [ ] Commit as `feat: add safe Obsidian exporter CLI`.

### Task 5: Obsidian documentation and bounded Dashboard integration

**Files:**
- Create backup copies and `BACKUP-MANIFEST.md` under the required timestamped Vault backup directory.
- Modify: `E:\Miao OS\99 Templates\README.md`
- Create: `E:\Miao OS\99 Templates\AI Coach Feedback Template.md`
- Create: `E:\Miao OS\02 IELTS\AI Feedback\README.md`
- Create: `E:\Miao OS\05 IELTS AI Coach\Architecture\Data Contract.md`
- Modify: `E:\Miao OS\00 Dashboard\Dashboard.md`

- [ ] Hash and back up every existing Vault Markdown file that will be modified.
- [ ] Add the exact short-field schema, enums, types, and version policy to the field registry.
- [ ] Create the reference template with fixed YAML fields and empty narrative headings.
- [ ] Create managed-directory and data-contract documentation.
- [ ] Append one ordinary Dataview query scoped to `02 IELTS/AI Feedback`, excluding `test = true`, limited to five rows.
- [ ] Verify Markdown links, fenced blocks, YAML, backup hashes, and that no other Vault file changed.

### Task 6: Complete test matrix and real read-only verification

**Files:**
- Add or refine the full `tests/exporting/` suite required by the specification.
- Modify: `docs/plans/obsidian-exporter-v1-plan.md` only to mark executed checkboxes if useful.
- Modify: `.memory.md`

- [ ] Run all exporting tests with a writable external `--basetemp`.
- [ ] Run related existing database, reading, writing, security, and backup tests.
- [ ] Run the complete pytest suite with cache disabled and external `--basetemp`.
- [ ] Run `python -m compileall ielts_ai_coach`.
- [ ] Run CLI help, config validation, and temporary end-to-end export.
- [ ] Scan generated test Markdown and logs for forbidden fields and sensitive patterns.
- [ ] Hash the real DB/WAL/SHM before and after `list-users` and aggregate counts.
- [ ] Run real `list-users`; report only ID, minimum account label, profile presence, exportable counts, and recent activity date.
- [ ] Do not select a user and do not run real Vault `--apply`.
- [ ] Update `.memory.md` with durable decisions and fresh verification status.
- [ ] Commit tests as `test: cover Obsidian exporter safety`.
- [ ] Commit documentation and memory as `docs: document Obsidian exporter integration`.

## Test Matrix

The completed suite must cover all 30 behaviors in the approved execution specification: user isolation; mandatory user ID; no all-users mode; reading/writing transforms; forbidden-field and content omission; timezone, YAML, UTF-8, filename, and renderer determinism; create/skip/update/conflict/missing/source-key outcomes; dry-run/apply behavior; real-source hash protection; atomic cleanup; corrupt state; allowed-directory-only creation; Vault identity validation; Feishu no-network behavior; and Mock/deterministic full flow.

## Plan Self-Review

- Scope is limited to Reading and Writing V1.
- No task requires a business database schema change.
- The only real Vault writes are the five approved Markdown integration files and their required backup.
- No implementation path exports all users or writes to the real Vault during this task.
- The adapter boundary consumes `FeedbackExportRecord`, not ORM or SQLite.
- State timestamps remain outside Markdown; generated bytes are deterministic.
- Every implementation task has focused tests and a local commit checkpoint.
- No placeholders, force-overwrite path, external API, Sync operation, plugin operation, scheduled task, or Git push is included.
