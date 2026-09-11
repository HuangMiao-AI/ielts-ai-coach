# IELTS AI Coach

A game-based bilingual IELTS learning prototype designed for Chinese learners.

[Live Demo](https://ielts-ai-coach.up.railway.app) · **Version: v1.0.0** · [GitHub Release](https://github.com/HuangMiao-AI/ielts-ai-coach/releases/tag/v1.0.0)

Independent student project. Not affiliated with or endorsed by IELTS, Cambridge University Press & Assessment, British Council, or IDP.

## Overview

IELTS AI Coach combines short vocabulary challenges, exam-style practice, bilingual review, and account-based learning history in a publicly deployed web application. The interface is primarily Simplified Chinese, with English practice content and English–Chinese explanations where provided.

Choose the guest entry option to explore the Training Arena, Reading, Listening Vocabulary Lab, and Writing without registration. Long-term learning records require an account.

Despite the project name, the deployed V1.0.0 does **not** use a live LLM API. Answer checking is deterministic, explanations are locally authored, and Writing submissions are not graded by an AI model.

## The problem and product direction

The design began with a practical observation: preparation can feel repetitive and fragmented, and starting a long practice session can be difficult. Chinese learners may want an explanation of *why* an answer works, not just a correct/incorrect label. These are design motivations, not research findings or claims of improved exam results.

The project evolved toward smaller skill-training loops rather than attempting to reproduce a large commercial question bank:

**Learn → practice → immediate feedback → review.**

The Training Arena keeps interactions short and easy to start, while Reading and Writing provide longer, structured workspaces.

## What I built

### Game-based Training Arena

Five-question rounds mix synonym and word-form challenges. Each answer receives immediate bilingual feedback, followed by points, accuracy, and vocabulary review. Answer locking and exact-once round recording prevent repeated clicks from adding extra points. Battle-style results are lightweight motivation, not IELTS Band scores; accumulated points are session-only.

### Reading

Eight project-original Academic Reading passages support a split passage/question workspace, question navigation, a live countdown, pause/resume, and submission confirmation. Answers are preserved through supported practice navigation; signed-in practice state and submitted results use database-backed storage. Review provides deterministic answer checking and bilingual explanations with passage evidence.

Guest Reading remains in the current session rather than creating persistent learning records.

### Listening Vocabulary Lab

A project-curated bank of 300 words supplies ten-word learning rounds and spelling challenges. Learners can hear a word through the browser Web Speech API, view its Chinese meaning, practise spelling, and review mistakes. Checks ignore case and surrounding whitespace, but do not silently accept other spelling differences.

This is vocabulary listening/spelling training, **not a full IELTS Listening simulation**. The dataset is not an official IELTS word list, and synthesized pronunciation is not official exam audio. Progress is session-only for both guests and registered users.

### Academic Writing

Task 1 includes six project-original SVG prompts: line graph, bar chart, pie charts, table, process, and map. Task 2 provides essay prompts. The workspace includes word counts, local structural checks, exam controls, and separate session drafts for different prompts.

In the deployed no-key mode, signed-in users save essays without a score or fabricated feedback. Guest completion reports basic counts and whether the recommended length was reached, without writing an essay to the database. Draft preservation across page or prompt changes does not guarantee recovery after closing the browser or losing the session.

### Accounts, history, and analytics

Registration/login uses Argon2id password hashing. User-scoped services support Reading history, saved essays, study records, and analytics based on available evidence. Missing evidence is not treated as demonstrated improvement. Guest practice creates no persistent user-owned records; Arena and Listening scores are not long-term analytics.

Responsive navigation and layouts support desktop, tablet, and phone-sized screens.

## Technology and architecture

The active application uses **Python 3.12, Streamlit, SQLAlchemy 2 with SQLite, Argon2id through `argon2-cffi`, Pydantic 2, and pytest**. Packaged HTML/CSS/JavaScript components handle browser interactions, including countdowns and `speechSynthesis`. Git/GitHub provide version control; Railway hosts the application.

```text
Browser
  ├─ Streamlit interface
  └─ Browser components: countdown, pause controls, speechSynthesis
           ↕
Streamlit application (Python)
  ├─ Views → services → local practice content
  ├─ Guest/session state (temporary)
  └─ User-scoped repositories → SQLAlchemy → SQLite (persistent)
```

This is one application, not a distributed microservice system. Entry points include [app.py](app.py), [views](ielts_ai_coach/views/), [services](ielts_ai_coach/services/), [database](ielts_ai_coach/database/), [browser components](ielts_ai_coach/components/), and [question banks](ielts_ai_coach/content/question_banks/).

## Engineering challenges

**1. A countdown that continues without interaction.** Streamlit reruns Python in response to events; a Python-rendered time label could remain visually unchanged on an idle page. A browser component now updates against the server-owned deadline, corrects its display when the tab becomes visible, and sends a single timeout event. The lesson was to separate continuous display updates from authoritative exam state. See [timer regression tests](tests/test_exam_timer_component.py).

**2. Pause without losing the workspace.** Freezing the number was insufficient: the interface needed to block interaction while preserving answers and drafts. Shared exam-state transitions and a browser-side hard-pause overlay coordinate the countdown, interaction lock, and resume action. This reinforced the value of explicit states and transition tests. See [pause tests](tests/test_exam_hard_pause.py).

**3. Writing drafts lost on prompt changes.** A selector change could trigger a rerun before the outgoing editor value was preserved. The fix captures that value in the selection callback and stores it under the corresponding visual prompt. A regression test edits and switches in the same rerun, matching the actual failure. The lesson was to test event ordering, not just the final screen. See [draft and guest tests](tests/test_guest_score_visuals.py).

**4. Guest access without persistent guest data.** Reusing signed-in workflows risked calling services that create user-owned records. Dedicated guest routes and completion actions keep practice state in the session; tests check that guest workflows leave persistent tables empty. The lesson was to enforce isolation at service boundaries, not merely hide account controls.

**5. SQLite surviving deployment replacement.** An application filesystem alone is not durable storage on Railway. The deployment uses a persistent Volume, an environment-configured SQLite path, and one replica. Restart and same-version redeploy acceptance checks confirmed that the same test account and prior Reading history remained available. Storage persistence needed operational verification, separately from application tests.

## Development journey

The Git history shows successive changes in scope and reliability:

- Account persistence and an independent Reading library developed into a split workspace (`665cbbd`, `d996e8d`, `7e31e2d`).
- User-scoped analytics and the growth dashboard connected practice records to review (`291274d`, `057bfce`).
- Shared exam controls, bilingual review, and a browser-owned countdown improved exam interactions (`3fd60c3`, `ea07fb7`, `c32965c`).
- The Arena, guest access, original Writing visuals, and Vocabulary Lab shifted emphasis toward low-friction practice (`a43a93d`, `23ed713`, `a74ce1f`).
- The pre-deployment audit fixed confirmed bugs (`6c2729c`). Railway deployment and persistence acceptance then established Application Demo V1.0.0; these operational checks are not additional application commits.

## Testing and reliability

At the V1.0.0 freeze, **334 automated tests passed**. The [test suite](tests/) covers authentication, user isolation, practice rules, exam state, guest behavior, and regressions. Database tests use isolated temporary SQLite files rather than the real development database.

Recorded release acceptance included a pre-deployment bug audit, browser smoke tests, responsive checks at 390/768/1440-pixel widths, guest database isolation, public HTTPS access, and Railway restart/redeploy persistence checks. These are release-time results, not continuous monitoring. Browser checks do not replace listening on real devices. Testing reduces regression risk; it does not prove the absence of defects.

## Deployment

The verified V1.0.0 deployment follows:

**GitHub release branch → Railway/Railpack → Streamlit → persistent Volume → SQLite.**

- Region: Singapore; replicas: **1**.
- Volume mount: `/data`.
- `DATABASE_URL=sqlite:////data/study_coach.db`.
- `BACKUP_DIR=/data/backups`.
- Healthcheck: `/_stcore/health`.
- Production source: `release/v1-deployment-candidate`.

Start command configured in Railway:

```sh
python -m streamlit run app.py --server.address 0.0.0.0 --server.port $PORT --server.headless true
```

These are deployment settings, not a claim that the repository contains a Railway configuration manifest. Backups on the same Volume are not independent off-site disaster recovery. Visit the [hosted demo](https://ielts-ai-coach.up.railway.app).

## AI-assisted development disclosure

ChatGPT and Codex were used as AI-assisted development tools. My contribution involved identifying the product problem, defining requirements and feature behavior, choosing product direction, specifying acceptance criteria, testing, finding bugs, evaluating solutions, directing iterations, and making deployment decisions. Learning and explaining the underlying technical concepts is part of that work.

AI-assisted tools supported implementation, refactoring, debugging, test generation and execution, and code review. This describes an AI-assisted student engineering process, not a claim that every implementation line was written unaided. Development assistance is separate from runtime functionality: the public V1.0.0 does not call a live LLM.

## Known limitations

- No live LLM API or automatic essay grading is enabled in the deployed demo. Provider-related code remains in the repository, but is not evidence of a live integration in this release.
- Web Speech voices vary by browser/device; Listening is vocabulary practice, not a complete exam simulation.
- Guest practice, Arena points, Listening progress, and unsaved Writing drafts are session-scoped.
- Speaking is outside the featured V1.0.0 scope. Automated speech recognition, pronunciation analysis, and Speaking scoring are not implemented.
- SQLite with one instance fits the prototype scope; it is not designed here as a large-scale, multi-instance service.
- This independent educational prototype provides no official IELTS results or demonstrated claims of score improvement.

## Run locally

Install **Python 3.12.x** and open a terminal in the repository root. No API key is required for the demonstrated no-key behavior; leave provider credentials unset in the environment and Streamlit Secrets.

Windows PowerShell:

```powershell
py -3.12 -m venv .venv
.venv\Scripts\python.exe -m pip install -r requirements.txt
.venv\Scripts\python.exe -m streamlit run app.py
```

macOS/Linux:

```sh
python3.12 -m venv .venv
.venv/bin/python -m pip install -r requirements.txt
.venv/bin/python -m streamlit run app.py
```

Open [localhost:8501](http://localhost:8501). The default local database is `data/ielts_ai_coach.db`, with backups under `data/backups`; startup creates database infrastructure. `DATABASE_URL` and `BACKUP_DIR` can override these defaults. Keep databases, backups, credentials, and personal data out of Git.

Run tests with `.venv\Scripts\python.exe -m pytest -q` on Windows or `.venv/bin/python -m pytest -q` on macOS/Linux. Dependencies are in [requirements.txt](requirements.txt); the supported interpreter is recorded in [.python-version](.python-version).

## Version

**[Application Demo V1.0.0](https://github.com/HuangMiao-AI/ielts-ai-coach/releases/tag/v1.0.0)** is the frozen university-application demo, tagged at `6c2729cd828de26632807fb02d4f51a261f772b0`. This README documents that version; later documentation commits do not move the application tag. Future development can continue separately.
