# Resume state — where each deliverable stopped

All four build agents were terminated mid-task by an API spend limit (HTTP 429), not by
any failure in the work. What is on disk is partial but coherent. This file records the
exact resume point for each so no one re-derives it.

**Nothing below has been tested.** No test suite was written or run before the agents
stopped. Treat every "done" as "written, unverified".

## apps/platform — furthest along

Written: `config/` settings and URLs, `quiz/` models + admin + services + views + urls,
roster CSV import management command, `autograder/` ingest app with `Submission` model,
migrations for both apps, all templates (join, identify, consent, question, done, closed,
usage_mode, instructor live view + HTMX partial), `static/` with vendored htmx,
`.env.example`, `pyproject.toml`.

Data model verified by inspection against `02-quiz-platform.spec.md`: field names match,
and `Item` is administered through `QuizItem` rather than owned by `Quiz` — the one
modelling decision the spec calls out explicitly.

**Stopped at:** about to write tests, one per acceptance criterion.

**Resume with:** tests for all 6 acceptance criteria, especially the two that are easy to
get wrong and expensive to get wrong — exports must contain `research_id` and never a name
or email, and a non-consenting student must appear in the gradebook but not in the export.
Then `uv run pytest` and `uv run ruff check .`, then `README.md`.

## apps/site — scaffolded, no content

Written: `astro.config.mjs`, `package.json` (+ lockfile), `tsconfig.json`,
`PromptVarianceRunner.tsx`, `lib/json-shape.ts`, `lib/live-provider.ts`,
`lib/use-api-key.ts`, `data/prompt-variance.ts`, `styles/course.css`.

**Stopped at:** writing the recorded fixture data for the variance runner.

**Missing entirely:** `src/content/docs/` — no lecture pages, no exercise pages, no
`reference/conspectus.mdx` or `reference/tooling.mdx`. No GitHub Pages workflow. No
`README.md`. The build has never been run.

**Resume with:** fixtures first (the schema drift across the 10 runs *is* the lecture 1
teaching point, so they must be realistic), then the content tree, then `npm run build`,
then verify the output opens from `file://` with no network.

## apps/examples — two folders of eleven

Written: `.devcontainer/` (config + post-create + README), `00-setup/` complete
(README, demo + recording, exercise check, src, tsconfig, package.json, .env.example),
`01-variance/` complete (demo + recording, src report/runs/schema).

**Stopped at:** about to run `00-setup` for the first time.

**Missing:** `02-mcp-server/` entirely — this is Exercise 1, issued at lecture 2, and is
the highest-priority remaining item in this directory. Folders `03` through `10` not
started. Devcontainer cannot be verified on this machine: Docker is not installed.

**Resume with:** run `00-setup` and `01-variance`'s recorded path and fix what breaks,
then build `02-mcp-server` with its failing-by-default test suite.

## packages/autograder — core written, unwired

Written: `pyproject.toml`, `models.py`, `context.py`, `registry.py`, `runner.py`,
`mcp/client.py`, `checks/common.py`, `checks/ex01_mcp.py`, `checks/ex05_security.py`.

**Stopped at:** the shared check helpers.

**Missing:** the webhook client (with the retry behaviour acceptance criterion 4 demands —
a failed post must retry and never silently lose a submission), the reusable GitHub Actions
workflows, checks for exercises 2-4, the correct and deliberately-broken reference MCP
servers used as test fixtures, all tests, and `README.md`. The secret-handling approach
that keeps a shared secret out of the student's fork is undecided and is the one genuine
design question left here.

## Cross-cutting, closed

- **`make check` now runs clean end to end** (34 tests, both `ruff check` runs, site
  `npm run lint`). Running it surfaced a real gap: `make setup` used plain `uv sync`,
  which skips the `dev` extra (ruff, black, pytest), so a fresh clone couldn't lint.
  Fixed to `uv sync --extra dev` in both `apps/platform` and `packages/autograder`.
- **CI added**: `.github/workflows/ci-platform.yml`, `ci-autograder.yml`, `ci-site.yml`,
  each path-scoped like `deploy-site.yml` so an unrelated commit doesn't trigger it.
- The `02-mcp-server` exercise's tool contract (`word_count`) was checked directly
  against `packages/autograder/checks/ex01_mcp.py` and matches with no changes needed —
  see the commit history for that folder.

## Cross-cutting, still open

- The autograder result contract exists on both sides (`packages/autograder/models.py`
  and `apps/platform/autograder/`) but CI does not yet test them against each other —
  `ci-platform.yml` and `ci-autograder.yml` run independently. A change to the shared
  JSON contract on one side would not currently fail the other side's CI.
- `apps/examples/03-context` through `10-economics` are skeleton only (README + folder
  shape); `08-security` and `09-brownfield` are README build-briefs with no code at all,
  deliberately, per `handover/05-build-order.md`.
