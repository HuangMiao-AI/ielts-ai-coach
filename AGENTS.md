# IELTS AI Coach Project Agent Rules

These rules apply to every Codex task in this repository.

## Required Task Workflow

Before starting any task:

1. Read `.memory.md` completely.
2. Inspect the relevant active files and confirm the repository's current
   state. Treat the repository as the source of truth when it differs from
   memory.
3. Execute only the scope approved by the user.
4. Follow all technical, security, and quality constraints in this file.

After completing any task:

1. Verify the result in proportion to the change, including pytest for core
   behavior.
2. Update `.memory.md` with material project information:
   - completed work;
   - important design decisions;
   - meaningful problems and causes;
   - durable solutions;
   - current test status;
   - the next approved or proposed step.
3. Keep `.memory.md` concise and current. Replace stale information instead of
   appending a chronological debug log.

If a higher-priority instruction explicitly forbids all file changes, do not
update `.memory.md`; report that the update was deferred.

## Memory Content Rules

Record decisions and facts that will affect future implementation. Do not
record:

- command transcripts or routine debug output;
- temporary failed attempts with no lasting effect;
- secrets, API keys, passwords, password hashes, or personal user data;
- speculative features that have not been approved;
- duplicated information already clear from active configuration.

## Active Technical Constraints

- Use Python 3.12.x and do not use features introduced after Python 3.12.
- Use Streamlit for the student-facing application.
- Use Simplified Chinese for all user-facing labels, buttons, messages, errors,
  and dashboard content.
- Use English for source files, identifiers, database fields, docstrings, and
  `README.md`. Maintain `README_CN.md` as the Chinese guide.
- Use SQLite with SQLAlchemy during local V1 development.
- Store passwords only as Argon2id hashes.
- Keep authentication logic in `ielts_ai_coach/auth.py`.
- Keep Streamlit pages limited to presentation and flow control.
- Put SQL in the database layer and business rules in services.
- Put external AI HTTP calls behind the provider interface.
- Keep Python files under 300 lines when practical.
- Add pytest coverage for every core behavior.
- Read secrets only from environment variables or Streamlit Secrets.
- Never commit `.env`, `.streamlit/secrets.toml`, real databases, backups,
  virtual environments, logs, or personal user data.

## Current Scope Boundaries

The approved complete V1 includes student profiles, IELTS score diagnosis,
deterministic seven-day plans, task completion, Qwen-compatible AI coaching,
Mock AI mode, Level 2 writing feedback, dashboard/history, and user-owned data
controls.

Do not add the following without new explicit approval:

- PostgreSQL deployment or real-data migration;
- React, Next.js, FastAPI, Redis, Celery, or enterprise infrastructure;
- phone verification, payments, school tenancy, or speaking audio analysis;
- public deployment, GitHub publishing, or use of external accounts.

`archive/enterprise-v0/` is historical and read-only. Never import it into the
active application, include it in dependencies or tests, or modify its
contents.

Legacy root modules from the original Streamlit MVP must not be deleted until
their useful logic has been migrated, tested, and separately approved for
archival.
