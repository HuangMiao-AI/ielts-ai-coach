# IELTS AI Coach

IELTS AI Coach is a modular Streamlit learning application for Chinese IELTS
students. It combines deterministic score diagnosis and study planning with an
optional AI study coach, Level 2 writing feedback, and a deterministic original
academic-reading practice loop.

The project is built as a Computer Science / AI university application
portfolio and as a local V1 that can be tested by a small group of students.
The student interface is in Simplified Chinese; source code and engineering
documentation use English.

> **AI scoring disclaimer:** all writing scores are AI estimates for learning
> purposes. They are not official IELTS results and no accuracy guarantee is
> claimed.

## Project Background

IELTS students often know their target score but do not know how to turn score
gaps into a practical daily routine. IELTS AI Coach closes that loop:

```text
Register → Profile → Scores → Diagnosis → Seven-day plan → Daily tasks
         → Reading practice / AI coach / Writing feedback → History
```

V1 is intentionally a modular monolith. It is small enough for an individual
student developer to understand and maintain while still demonstrating
authentication, data modeling, deterministic algorithms, AI integration,
privacy controls, automated tests, and product-oriented UI design.

## Features

- Username/password registration and login
- Argon2id password hashing and Streamlit session isolation
- One user-owned student profile with target score, exam date, and study time
- Historical IELTS listening, reading, writing, and speaking scores
- Deterministic IELTS overall calculation and tied-weakness detection
- Rule-based Chinese recommendations for weak sections
- Deterministic seven-day plans with exact daily minute allocation
- Concrete copyright-safe tasks with objectives, material, steps, expected
  outputs, and completion criteria
- Eight versioned project-original Academic reading passages with 77
  Multiple Choice, True/False/Not Given, and Matching Heading questions
- Start, pause, continue, submit, deterministic score, and evidence-based
  answer review for reading tasks
- Persisted user-owned reading results with score, accuracy, wrong-question
  identifiers, answers, explanations, and task/study-log synchronization
- Three exam stages: foundation, targeted improvement, and exam simulation
- One-click task completion, optional actual-time editing, and synchronized
  study logs
- User-owned plan history; regeneration archives previous plans
- Qwen-compatible AI provider plus automatic offline Mock mode
- Personalized AI study coach with a 20-success daily limit
- Level 2 writing feedback with four IELTS dimensions and a 3-success limit
- Pydantic validation and one repair attempt for invalid AI JSON
- Home metrics, four skill shortcuts, task progress, study time, weak-section
  guidance, recent activity, and deterministic next-step recommendations
- Consolidated score, plan, essay, and coach history
- One route registry with a desktop sidebar and 56-pixel mobile bottom
  navigation
- Premium glass-style responsive UI for phone, iPad, and desktop widths
- Listening Demo workflow with honest no-score messaging
- Writing editor with live word count, session draft isolation, edit timer,
  and protected submission
- Speaking Part 1/2/3 practice with timers, notes, and session-local browser
  recording without automatic scoring
- Installable PWA metadata and local app icons without an offline claim
- Two-step deletion controls for the current user's optional data
- Daily SQLite online backup with seven-backup retention

## Screenshots

Sanitized screenshots will be added before any portfolio publication:

- `docs/screenshots/dashboard.png` — dashboard and progress overview
- `docs/screenshots/diagnosis.png` — deterministic IELTS diagnosis
- `docs/screenshots/plan.png` — seven-day plan and daily tasks
- `docs/screenshots/writing.png` — structured writing feedback

The current local captures are deliberately excluded from Git because they
include browser and desktop chrome. Published screenshots must be cropped and
must use fictional student data.

## Architecture

```text
Browser
  │
  ▼
Streamlit app.py
  │
  ├── views/         Chinese UI and flow control
  ├── services/      Validation and business rules
  │     ├── deterministic scoring/planning
  │     └── AI coach/writing orchestration
  ├── ai/            Provider interface, Qwen, Mock, schemas
  └── database/      SQLAlchemy models, repositories, sessions, backup
          │
          ▼
        SQLite
```

`app.py` initializes the database, performs the daily backup check, and routes
the authenticated session. Views never perform SQL or password verification.
Repositories are the only database-access layer. Every business query and
mutation is scoped by the authenticated `user_id`.

The connection URL is configurable through `DATABASE_URL`. Local V1 defaults
to SQLite, while the repository/service boundaries leave room for a later
managed PostgreSQL deployment.

## Technology Stack

- Python 3.12
- Streamlit 1.59 for the student-facing application
- SQLAlchemy 2.0 with local SQLite storage
- Argon2id password hashing through `argon2-cffi`
- Pydantic 2 for validated AI response schemas
- `requests` behind a provider interface for optional Qwen-compatible calls
- pytest 8 for automated testing

## Database Design

| Table | Purpose |
|---|---|
| `users` | Username, normalized username, Argon2id hash, active status |
| `student_profiles` | Nickname, grade, target, exam date, daily minutes |
| `score_records` | Historical section scores and deterministic overall |
| `study_plans` | Versioned active or archived seven-day plans |
| `plan_tasks` | Dated tasks; versioned structured content uses `description` |
| `study_logs` | Actual minutes recorded for completed tasks |
| `coach_messages` | User and assistant messages with visibility state |
| `ai_usage_daily` | Successful daily coach and writing counters |
| `essays` | IELTS writing submissions and processing status |
| `writing_feedback` | Validated four-dimension AI feedback |
| `task_question_attempts` | Final reading answers, score, review snapshot, and wrong questions |

All user-owned business tables contain `user_id`. Audio and binary files are
outside the current reading-practice phase.
SQLite data lives in `data/ielts_ai_coach.db` and is excluded from Git.

## Deterministic Rules vs AI

Deterministic Python code is responsible for facts and constraints:

- IELTS scores must be from 0 to 9 in 0.5 increments.
- Overall is the four-section average rounded to the nearest half band using
  deterministic half-up rounding.
- All tied lowest sections are identified.
- The seven-day plan uses the exam date, target, scores, daily minutes, weak
  sections, and recent completion rate.
- Every plan day sums exactly to the configured study minutes.
- Listening, reading, writing, and speaking task templates are generated
  locally without an AI call.
- Reading answers are normalized for Unicode, repeated whitespace, and case,
  then scored against the versioned answer key without AI.
- The eight bundled reading passages and all questions, explanations, and
  evidence are project-original; copyrighted test material is not copied.
- Exam stages use fixed boundaries: over 90 days, 31–90 days, and 30 days or
  fewer.

**Copyright statement:** 原创IELTS风格练习，非官方IELTS或Cambridge试题。

AI is used only for natural-language coaching and writing feedback. The app
still supports profiles, diagnosis, plans, tasks, history, and dashboards when
no API key is configured.

## AI Provider Design

`ielts_ai_coach.ai.base.AIProvider` defines the provider-neutral `generate`
method. V1 includes:

- `QwenAIProvider`: Alibaba Cloud Model Studio's OpenAI-compatible chat API
- `MockAIProvider`: deterministic local responses with no network access

The factory selects Mock mode whenever no API key is configured. Qwen settings
include API key, base URL, model name, timeout, and bounded retry count. A future
DeepSeek provider can implement the same interface without changing business
services.

Writing responses are validated by Pydantic. Invalid JSON is repaired or
requested again once. Only a valid persisted result consumes quota. Provider
errors expose safe codes instead of credentials or low-level response bodies.

See Alibaba Cloud's
[OpenAI-compatible Qwen documentation](https://help.aliyun.com/en/model-studio/qwen-api-via-openai-chat-completions)
for account- and region-specific configuration.

## Security and Privacy

- Passwords are stored only as Argon2id hashes.
- Session state stores authentication status, user ID, and username only.
- Pages derive `user_id` from the authenticated session, never form input.
- Repository reads, writes, and deletes require an owning `user_id`.
- AI context contains only the current user's approved minimum data.
- Passwords, API keys, and full essays are not written to application logs.
- Failed AI calls do not consume successful-call quota.
- `.env`, private Streamlit Secrets, databases, backups, logs, and archives are
  ignored by Git.
- Deletion controls remove only the current user's optional records and require
  a second confirmation.

Do not use real student data in a public repository, screenshots, demo
databases, issues, or test fixtures.

## Local Installation

Requirements:

- Python 3.12.x
- Windows PowerShell commands below, or equivalent shell commands

```powershell
py -3.12 -m venv .venv
.venv\Scripts\python.exe -m pip install --upgrade pip
.venv\Scripts\python.exe -m pip install -r requirements.txt
.venv\Scripts\python.exe -m streamlit run app.py
```

Open the local URL printed by Streamlit. On first run the app creates
`data/ielts_ai_coach.db`. Without an API key, all AI pages clearly run in Mock
demonstration mode.

### Access from a phone on the same local network

Start Streamlit on all local interfaces:

```powershell
.venv\Scripts\python.exe -m streamlit run app.py --server.address 0.0.0.0
```

Find the computer's private IPv4 address with `ipconfig`, then open
`http://<private-ip>:8501` on a phone connected to the same trusted Wi-Fi
network. Windows Firewall may ask for local-network permission. Do not expose
this development server directly to the public internet.

### Install on a phone

The computer must keep Streamlit running and the phone must be able to reach
its local-network address.

- iPhone/iPad: open the site in Safari, tap **Share**, choose **Add to Home
  Screen**, then confirm **Add**.
- Android: open the site in Chrome, open the browser menu, choose **Install
  app** or **Add to Home screen**, then confirm. Plain LAN HTTP may offer only
  a home-screen shortcut; full browser installability normally requires a
  trusted HTTPS origin.

This release provides a manifest, theme metadata, and local icons. It does not
register a service worker or provide offline access. Unsubmitted Reading,
Writing, Listening, and Speaking state is session-only and may be lost when
the browser session ends.

## Configuration

Configuration is read from environment variables or Streamlit Secrets.
`.env.example` is a reference file; the project does not automatically load a
local `.env` file.

For local Streamlit Secrets:

```powershell
Copy-Item .streamlit\secrets.example.toml .streamlit\secrets.toml
```

Then edit the private `secrets.toml`:

```toml
DATABASE_URL = "sqlite:///data/ielts_ai_coach.db"
BACKUP_DIR = "data/backups"
QWEN_API_KEY = "replace-with-your-private-key"
QWEN_BASE_URL = "https://dashscope.aliyuncs.com/compatible-mode/v1"
QWEN_MODEL = "qwen-plus"
AI_TIMEOUT_SECONDS = "30"
AI_MAX_RETRIES = "2"
```

The base URL may differ by Alibaba Cloud region or workspace. Keep
`.streamlit/secrets.toml` private.

## Testing

```powershell
.venv\Scripts\python.exe -m pytest
```

Tests use temporary SQLite databases and local fake providers. They never call
a real AI API and never write test records to the production `data/` database.
The current suite contains 160 tests. Coverage includes authentication,
isolation, backups, profiles, score diagnosis, planning, reading-bank loading,
deterministic answer scoring, duplicate submission, reading ownership,
interactive Reading/Listening/Writing/Speaking page flows, responsive
navigation, PWA assets, quotas, provider failures, writing feedback, deletion,
Home aggregation, and the complete Streamlit student flow.

## Project Structure

```text
.
├── app.py
├── ielts_ai_coach/
│   ├── auth.py
│   ├── config.py
│   ├── content/
│   ├── ai/
│   ├── database/
│   ├── services/
│   ├── ui/
│   └── views/
├── tests/
├── data/                       # private runtime data, ignored
├── .streamlit/
│   └── secrets.example.toml
├── .env.example
├── requirements.txt
├── README.md
├── README_CN.md
├── AGENTS.md
└── archive/enterprise-v0/      # historical, ignored and never imported
```

Legacy root MVP modules remain inactive references during V1 migration. The
active application imports only the `ielts_ai_coach/` package.

## Engineering Decisions

- A modular Streamlit monolith is more maintainable for one student developer
  and approximately 20 testers than an early microservice stack.
- SQLite is appropriate for local V1; public testing should move to managed
  PostgreSQL so data does not depend on an ephemeral local file.
- SQLAlchemy isolates database access and reduces future migration work.
- Planning is deterministic so core learning functionality never depends on AI.
- AI providers are replaceable and Mock mode makes the project demoable offline.
- Quotas count successful outcomes rather than raw network attempts.
- Plan regeneration archives history instead of overwriting it.
- No Alembic workflow is introduced in local V1; schema evolution must be
  planned before public deployment.

## Known Limitations

- SQLite is the local default and is not the final public multi-user database.
- The Streamlit process performs AI calls synchronously.
- Mock writing feedback is a fixed demonstration, not real evaluation.
- AI feedback quality has not been calibrated against official examiners.
- Speaking recordings and all unfinished practice drafts are session-only;
  there is no server-side audio archive or automatic speaking score.
- V1 has no image input, payments, teacher/parent portals, account
  self-deletion, or password-change flow.
- Daily quotas use the application server's current date.
- Reading contains eight passages and permits one final submission per task;
  it does not yet support retry attempts.
- Listening still requires student-owned material and has no bundled original
  audio practice loop.
- PWA support is an installable shell only; authenticated pages are not
  available offline.
- There is no production monitoring, managed backup, or migration system yet.

## Future Roadmap

1. Run usability tests on the reading loop with synthetic or consented data.
2. Evaluate whether controlled Reading retries are pedagogically useful.
3. Add project-original listening scripts and audio in a separately approved
   phase.
4. Build an AI evaluation set and improve prompt/version tracking.
5. Add screenshots and a short portfolio demo video using fictional students.
6. Migrate to managed PostgreSQL only before separately approved public tests.

For the Chinese guide, see [README_CN.md](README_CN.md).
