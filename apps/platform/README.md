# Quiz and research platform

Django + HTMX app for running the pre/post-lecture quizzes described in
`handover/02-quiz-platform.spec.md`. It also ingests conformance results from the
autograder (`packages/autograder`) via a shared-secret webhook.

Local development needs no services: it runs on SQLite out of the box. Setting
`DATABASE_URL` switches to Postgres for staging and production.

## Running it locally

```bash
cd apps/platform
uv sync --extra dev            # installs Django, DRF-free deps, pytest, ruff, black
cp .env.example .env           # then edit — see "Environment variables" below
uv run python manage.py migrate
uv run python manage.py createsuperuser   # the instructor account
uv run python manage.py runserver
```

Visit `http://127.0.0.1:8000/admin/` as the instructor and `http://127.0.0.1:8000/` as a
student joining with a code.

If `uv sync` isn't available in your environment, create the virtualenv and install from
`pyproject.toml` directly:

```bash
uv venv --python 3.13
uv pip install -e ".[dev]"
```

## Running the tests and linter

```bash
uv run pytest        # 17 tests, one or more per acceptance criterion in the spec
uv run ruff check .
```

Both must be clean before merging a change to this app.

## Environment variables

All of these are documented in `.env.example`; copy it to `.env` and fill in. `.env` is
never committed (see the repo's root `.gitignore`).

| Variable | Purpose | Local default |
|---|---|---|
| `DJANGO_SECRET_KEY` | Django's cryptographic secret key. Generate a real one for anything beyond a laptop: `uv run python -c "import secrets; print(secrets.token_urlsafe(50))"`. | insecure placeholder, fine for local dev only |
| `DJANGO_DEBUG` | `1` for local development, `0` for staging and production. | `1` |
| `DJANGO_ALLOWED_HOSTS` | Comma-separated hostnames Django will serve. Use the real hostname in production, never `*`. | `*` |
| `DJANGO_CSRF_TRUSTED_ORIGINS` | Comma-separated `https://` origins Django trusts for CSRF (needed once the admin and student forms are served over a real domain). | empty |
| `DJANGO_SECURE_SSL_REDIRECT` | Redirect http to https when `DJANGO_DEBUG=0`. Set to `0` only behind a TLS-terminating proxy that already redirects. | `1` |
| `DATABASE_URL` | Unset locally (SQLite at `apps/platform/db.sqlite3`, no services needed). A Postgres URL (`postgres://user:pass@host:5432/platform`) for staging and production. | unset |
| `AUTOGRADER_SHARED_SECRET` | Shared secret the autograder's collector presents in the `X-Autograder-Secret` header. Generate with `uv run python -c "import secrets; print(secrets.token_urlsafe(32))"`. **Never** store it as a repository secret in a student's exercise template — a student-editable workflow can always `echo` a secret it has access to. It lives only in the instructor-owned collector workflow (`packages/autograder/workflows/collect.yml`), which pulls each student's result artifact and delivers it here; student workflows run with no secret at all. See `packages/autograder/README.md` for the full split. | empty (ingest endpoint rejects everything until set) |

### A note on SQLite and concurrency

SQLite allows exactly one writer at a time. A lecture hall of up to 40 phones answering in
the same few seconds can hit `database is locked` if that write pressure isn't tamed. The
mitigations in this codebase (`config/settings.py`: WAL journal mode and a longer busy
timeout; `quiz/sqlite_resilience.py`: a process-wide write lock around the student views,
only active when the backend is SQLite) make that safe for a single-instance deployment on
SQLite. None of this activates on Postgres, which handles concurrent writers natively via
MVCC — that's what staging and production use. If a deployment moves beyond one process on
SQLite (e.g. multiple gunicorn workers behind a load balancer), switch `DATABASE_URL` to
Postgres rather than trying to stretch SQLite further.

## Running the pre-lecture-1 baseline quiz end to end

This is the load-bearing use case: per `CLAUDE.md`, the baseline measurement cannot be
retrofitted, so this path has to work correctly the first time, before lecture 1. All of it
happens through `/admin/` — no shell, no database client.

1. **Deploy and migrate** (or run locally per above). Create a superuser if you haven't:
   `uv run python manage.py createsuperuser`.
2. **Create a cohort.** In `/admin/quiz/cohort/`, add one (e.g. semester `2026/2027-1`,
   name `КСТ`).
3. **Import the roster.** On the cohort list, click "Импорт на списък" and upload a CSV
   with `name,email` columns (university emails). Re-uploading a corrected file later
   updates students in place instead of duplicating them.
4. **Create the topic** for lecture 1 in `/admin/quiz/topic/` (lecture number 1, a title).
5. **Author five items** in `/admin/quiz/item/` against that topic: a stem, an `options`
   JSON list (e.g. `["А", "Б", "В", "Г"]`), and the zero-based `correct_option` index. Since
   this is the very first quiz of the semester there is no previous lecture to repeat items
   from, so all five are new; leave `parallel_form_group` blank or set it if you already
   know which item will reappear as a parallel form in the post-quiz.
6. **Create the quiz.** In `/admin/quiz/quiz/`, add one: lecture number 1, phase `PRE`,
   the cohort from step 2. Add the five items as inline `QuizItem` rows, each with a
   `position` (1–5) and `measurement` — for a first pre-quiz with nothing to measure
   retention on yet, that's `BASELINE` for all five.
7. **Open the quiz.** Select it in the quiz list and run the "Отвори" action. The join
   code appears in the success message and in the quiz's list-page column; the ordering of
   these seven steps is exactly acceptance criterion 1 in the spec, and it fits comfortably
   inside 10 minutes.
8. **Project the code** and open the live view (the "Проекция" link on the quiz row, or
   `/instructor/q/<id>/live/`) on the room's screen. It polls every second and never shows
   an individual answer, only per-option counts.
9. **Students join** at the site root with the code, identify by the email that's in the
   roster, are asked for research consent once (refusing has no effect on taking the quiz
   or on their course standing — it only keeps them out of the CSV export), then answer
   five questions one per screen, then answer the one self-reported agent-usage question,
   then see a confirmation with no score.
10. **Close the quiz** with the "Затвори" admin action once the window ends; the join code
    stops working immediately.
11. **Export.** "CSV" on the quiz row (or `/instructor/q/<id>/export.csv`) downloads the
    research file: `research_id` plus topic, phase, measurement, correctness, latency and
    agent-usage-mode columns, one row per response, and never a name or email. The
    cohort's "Gradebook CSV" link is the separate, identifiable file for course-participation
    bookkeeping — it lists every student whether or not they consented to research, and it
    is not the file that goes anywhere near the ethics application or a paper.

Withdrawal (spec: "withdrawal deletes responses on request") is a `Student` admin action,
"Изтрий изследователските данни" — it deletes the student's `Response` rows and withdraws
consent without touching anyone else's data, so the live aggregate and later exports
recompute correctly with that student simply absent.

## Autograder ingest

`POST /api/autograder/results/` accepts one conformance run per request, authenticated by
the `X-Autograder-Secret` header (compared to `AUTOGRADER_SHARED_SECRET` in constant time)
and idempotent on `(repo, commit)`: retrying a failed post safely upserts the same row
rather than creating a duplicate or erroring. See `packages/autograder/models.py` for the
sending side of this contract.

## What is intentionally not here

Per the spec's non-goals: no dashboards, no student-visible scores, no final-grade
calculation. Those are out of scope for v1 by design, not because they were forgotten.
