# IELTS AI Coach

IELTS AI Coach is a local, Chinese-language IELTS learning application built
with Python, Streamlit, SQLAlchemy, and SQLite. It provides deterministic
practice workflows and optional provider-based AI features for learning use.

## Current features

- Argon2id authentication and authenticated user-data isolation.
- A four-step onboarding and editable learner profile. Scores may be missing;
  the application does not invent a baseline.
- Deterministic score diagnosis and a seven-day study plan.
- Eight original IELTS-style Academic Reading passages, deterministic scoring,
  evidence-based review, and saved Reading history.
- Two original local Listening mini tests with bundled offline audio and
  deterministic answer review. Listening results are session-only in this V1.
- Four original Writing prompts. When AI scoring is unavailable, essays are
  saved without a score or fabricated feedback.
- Speaking Part 1/2/3 prompts, timers, browser microphone guidance, and a
  session-only text fallback. Speaking is not automatically scored.
- A user-isolated Home dashboard, analytics, history, study logs, and an
  optional local Mock AI explanation.
- Responsive Streamlit UI for phone, tablet, and desktop; PWA metadata is
  included, but offline operation is not claimed.

## Technology

- Python 3.12
- Streamlit
- SQLAlchemy 2 and SQLite
- Argon2id via `argon2-cffi`
- Pydantic 2
- pytest

## Install and run locally

```powershell
py -3.12 -m venv .venv
.venv\Scripts\python.exe -m pip install --upgrade pip
.venv\Scripts\python.exe -m pip install -r requirements.txt
.venv\Scripts\python.exe -m streamlit run app.py
```

Open [http://127.0.0.1:8501](http://127.0.0.1:8501).

For a trusted home or classroom LAN, run:

```powershell
.venv\Scripts\python.exe -m streamlit run app.py --server.address 0.0.0.0
```

Then open `http://<private-IPv4-address>:8501` from a device on the same Wi-Fi.
Do not expose this local development server directly to the public internet.

## AI modes

Without configured credentials, the application uses its deterministic local
Mock provider. No real AI API is called in this mode. A Qwen-compatible
provider is available only when private configuration is supplied through
environment variables or `.streamlit/secrets.toml`.

AI feedback and any estimated Writing band are educational aids only. They
are not official IELTS results and do not replace an IELTS examiner.

## Database

The default local database is `data/ielts_ai_coach.db`, excluded from Git.
`create_all` is used only for additive local schema creation. The current
learner profile model adds `learner_profiles_v2` without altering old tables:

- one unique `user_id` per profile;
- display name, grade, optional exam date, daily minutes, and target band;
- optional Reading, Listening, Writing, and Speaking baseline bands;
- onboarding state and timestamps.

Optional scores are stored as SQL `NULL` when unknown. A real `0` remains a
real score. The app reads `learner_profiles_v2` first and falls back to the
legacy `student_profiles` record only when no V2 profile exists. Legacy users
receive no startup backfill; a V2 record is created only after they save their
profile. `score_records` remains reserved for complete, real scores.

Databases, WAL/SHM files, backups, private secrets, uploads, logs, and virtual
environments must never be committed.

## Original-content and copyright notice

**原创IELTS风格练习，非官方IELTS或Cambridge试题。**

The Reading, Listening, and Writing materials bundled in this project are
project-original practice materials. They are not official IELTS or Cambridge
test papers.

## Tests

```powershell
.venv\Scripts\python.exe -m pytest -q
.venv\Scripts\python.exe -m compileall -q ielts_ai_coach
.venv\Scripts\python.exe -m pip check
```

Current baseline: **247 pytest tests pass**. Tests use isolated temporary
SQLite files and Mock/fake providers; they do not call a real AI API.

## Current limitations

- SQLite is intended for local single-instance development, not public
  multi-instance deployment.
- Listening answers and scores are session-only and have no analytics history.
- Speaking audio and text fallback are session-only; there is no speech
  recognition, pronunciation analysis, or automatic band score.
- Writing saved in no-key/Mock mode is deliberately unscored.
- PWA metadata does not provide a service worker or offline support.
- This repository does not include public deployment, user uploads, mobile
  native apps, payments, or cloud database migration.
