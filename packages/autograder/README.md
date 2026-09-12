# autograder

Conformance harness for the agentic web development course exercises. Implements
`handover/04-autograder.spec.md`. Read that spec first; this README explains how the code
here implements it, not why the design choices in it were made.

## Grade behaviour, not code

Every check in this package answers a yes/no, mechanically decidable question: does the
file exist and is it substantive, does the command exit zero, does the server answer the
protocol correctly, does the URL return 200. **There is no partial credit, no style score,
no complexity score, and no plagiarism detection** — those are explicitly out of scope per
the spec, because an agent will optimise straight past any of them if they count.

What a check *cannot* decide — whether a design doc's reasoning is any good, whether a
finding in an adversarial review is real, whether the prompt log tells the truth, which
production gaps actually matter — goes to the oral defense. Tell students this in week one:
if they don't know the split exists, they will spend their effort satisfying the checker
instead of doing the work the checker cannot see.

## What's checked, per exercise

| Exercise id | What is checked | Module |
|---|---|---|
| `01-mcp-server` | `tools/list` returns a valid schema, the declared tool is invoked correctly, an unknown tool is rejected without crashing the server, the server survives to answer again afterwards. | `checks/ex01_mcp.py` |
| `02-spec-driven` | A non-trivial design doc exists (word count + required sections), a recorded run exists for both the with-doc and without-doc conditions, the repository still builds. | `checks/ex02_spec_driven.py` |
| `03-agent-feature` | The test suite passes, a prompt log exists whose dated entries bracket the commit history. | `checks/ex03_agent_feature.py` |
| `04-deployment` | The deployed URL returns 200, a smoke test script exits zero, GitHub Actions check runs on the commit are all green, a substantive production-gap report exists, no committed secrets (working tree or history). | `checks/ex04_deployment.py` |
| `05-security-review` | `FINDINGS.md` parses in the required format with at least 3 findings, each with severity/location/impact/fix. The other two checks (flawed repo's own tests still pass, planted vulnerabilities unreachable) are stubbed and fail loudly: they depend on `apps/examples/08-security/`, which does not exist yet (see `checks/ex05_security.py` for the tracking TODOs). A stub check never passes vacuously. | `checks/ex05_security.py` |

Exercise ids and file-name candidates (`DESIGN.md`, `PROMPT_LOG.md`, `PRODUCTION_GAPS.md`,
...) are an instructor convention documented here and in each exercise's own README in
`apps/examples/`; they are not fixed by the spec itself, so an exercise brief and this
package's candidate lists must be updated together if either changes.

## Result JSON contract

Fixed by `handover/04-autograder.spec.md`, "Result format", and mirrored in
`apps/platform/autograder/views.py`'s validation — this package must not edit that file,
only match it:

```json
{
  "exercise": "01-mcp-server",
  "repo": "student/agentic-ex1",
  "commit": "abc123",
  "checks": [
    { "name": "tools_list_responds", "passed": true },
    { "name": "tool_invocation_matches_spec", "passed": false, "detail": "..." }
  ],
  "completed_at": "2026-10-14T09:12:00Z"
}
```

`models.RunResult`/`models.CheckResult` produce exactly this shape (`to_dict`/`to_json`).
`detail` is omitted when empty (the platform does not require it, and a passing check
usually has nothing actionable to add). The platform is idempotent on `(repo, commit)`: an
upsert, not an error, on the second POST for the same commit — which is exactly what makes
webhook retries safe.

## How the pieces fit together

```
context.py     SubmissionContext: the repo path + repo/commit/deployed_url a check may read
registry.py    per-exercise ordered list of checks; safe_run() turns a crash into a failed check
runner.py      run_exercise(): runs every registered check, always all of them, builds RunResult
exercises.py   the one place that registers all five exercises' checks
checks/        one module per exercise, built from checks/common.py's reusable builders
mcp/client.py  dependency-free MCP-over-stdio client used only by checks/ex01_mcp.py
webhook.py     WebhookClient: POST a RunResult to the platform, retry, recover to disk
gh_artifacts.py  read-only GitHub API client used only by the instructor-side collector
cli.py         `autograder run|submit|collect`
```

### CLI

```
autograder run --exercise 01-mcp-server [--repo-path .] [--deployed-url URL] --out result.json
autograder submit --result result.json --platform-url URL --secret SECRET
autograder collect --roster roster.json --platform-url URL --secret SECRET --github-token TOKEN
```

`run` is the only verb a student's workflow calls. `submit` and `collect` are instructor-side
only — see below for why.

## Secret handling and trust model

**The one open design question this package had to resolve.** The platform's ingest
endpoint (`apps/platform/autograder/views.py`, which this package does not edit) authenticates
with one static shared secret in an `X-Autograder-Secret` header, compared with
`hmac.compare_digest`. That contract is fixed, so the question is entirely: how does that
secret reach a workflow run triggered by a student's push, without ever being readable by
the student?

**It can't, and the honest answer is to not try.** A student who can edit their fork's
workflow YAML can always add `run: echo "$ANY_SECRET_IN_SCOPE"` to any job that has one in
scope — that is true of *any* GitHub Actions mechanism for handing a value to a job
(repository secret, environment secret, or `secrets: inherit` from a reusable-workflow
caller), because the runner executing the job is fully under the student's control. GitHub's
own docs warn about exactly this class of problem (the "pwn request" pattern) for workflows
that combine untrusted code with a secret in scope. So instead of looking for a clever way
to smuggle a static, long-lived secret into student-controlled compute, this design keeps
the secret out of student-controlled compute entirely:

1. **The student's workflow (`templates/exercise-workflow.yml`) runs with zero secrets.** It
   installs this package, runs `autograder run`, prints the result to the Actions log (so
   "student sees their result in the Actions log" from the spec's Flow section holds), and
   uploads `result.json` as a workflow artifact (`actions/upload-artifact`). That's the
   entire footprint in the student's repository. Read that file: there is nothing in it a
   student could turn into a leaked credential, because there is no credential in it.

2. **A separate, instructor-owned collector (`workflows/collect.yml`, `autograder collect`)
   holds the shared secret and a read-only GitHub token.** On a schedule, it lists the
   roster's repositories via the GitHub REST API, finds each one's latest `autograder-result`
   artifact, downloads it, and POSTs it to the platform with the secret — using
   `WebhookClient`, the same retry-and-recover code path `submit` uses. This workflow lives
   in instructor-controlled infrastructure that students never fork or push to, so the
   secret is never in scope for a workflow a student can edit.

This is a deliberate, documented departure from a literal reading of the spec's Flow step 4
("workflow posts it to the platform with a shared secret") as *one* workflow doing both the
checking and the posting: with the platform's ingest endpoint fixed to a static shared
secret, no single workflow can do both without putting that secret in reach of student-edited
YAML. Splitting "run the checks" (student-side, secretless) from "deliver the result"
(instructor-side, holds the secret) is what satisfies acceptance criterion 5 honestly rather
than by omission. If the platform's ingest endpoint is ever extended to accept GitHub's own
OIDC-issued, short-lived, run-scoped ID tokens (`permissions: id-token: write`, verified
against `https://token.actions.githubusercontent.com`'s published keys) instead of a static
secret, the split collapses back into one workflow with no long-lived credential anywhere —
that is the standard fix for this exact problem, but it requires a platform-side change this
package is explicitly not allowed to make.

`workflows/reusable-check.yml` is the DRY version of the student-side workflow, callable via
`workflow_call` — see the next section for why it isn't wired up yet.

## How a template wires up the workflow

Today: copy `templates/exercise-workflow.yml` into the exercise template's
`.github/workflows/autograder.yml` and set `AUTOGRADER_EXERCISE` to the right id. That file
installs this package straight from this monorepo with:

```
pip install "autograder @ git+https://github.com/ORG/university-web-development@main#subdirectory=packages/autograder"
```

(pip/uv support installing a package from a subdirectory of a git repo natively — no publish
step needed.) Replace `ORG` once the monorepo has a public home.

Once `workflows/reusable-check.yml` is published at `.github/workflows/reusable-check.yml`
at the root of this monorepo (out of scope for `packages/autograder/` — flagged here as a
handoff item for whoever owns the root of the repo), every template's workflow collapses to:

```yaml
jobs:
  check:
    uses: ORG/university-web-development/.github/workflows/reusable-check.yml@main
    with:
      exercise: "01-mcp-server"
```

`GitHub` only resolves `uses:` reusable-workflow paths under `.github/workflows/` of the
referenced repository, which is why `workflows/reusable-check.yml` cannot be called directly
from where it lives in `packages/autograder/` today.

`workflows/collect.yml` is the instructor-side counterpart: deploy it to a private,
instructor-owned repository (not a template, not forked by students) with
`AUTOGRADER_PLATFORM_URL`, `AUTOGRADER_SHARED_SECRET` and `COLLECTOR_GITHUB_TOKEN` as
repository secrets, and a `roster.json` (see `roster.json.example`) listing the repos to
poll.

## Retry and recovery (acceptance criterion 4)

`webhook.WebhookClient.post()`:

- retries network errors, timeouts and 5xx responses up to `max_attempts` (default 5) with
  exponential backoff (`backoff_seconds * backoff_multiplier ** (attempt - 1)`, default
  1s/2s/4s/8s).
- does **not** retry a 4xx: that means the payload or the secret is wrong, and an identical
  retry would fail identically — it raises `WebhookError` instead so the caller can
  distinguish "will never succeed" from "may succeed later."
- on exhausting all attempts, writes the exact JSON that would have been posted to
  `autograder-recovery/<repo>_<commit>.json` (configurable via `recovery_dir`) and returns
  rather than raising, so **a submission is never dropped without a trace**. `workflows/collect.yml`
  uploads that directory as a workflow artifact (`autograder-undelivered`) on every run, so an
  instructor can `autograder submit --result <file>` it manually once the platform is reachable
  again. The recovery filename is keyed by `(repo, commit)` — the platform's own idempotency
  key — so re-submitting it later is always safe even if part of it already landed.

## Reference fixtures

`tests/fixtures/mcp_good/` and `tests/fixtures/mcp_broken/` are small, dependency-free
Python MCP servers implementing the same `word_count` contract as
`apps/examples/02-mcp-server/exercise/`, built independently so this package's test suite
does not depend on `apps/examples/` at test time. `mcp_broken/` has three independent,
deliberately planted defects (invalid tool schema, wrong invocation result, crashes on an
unknown tool) so the test suite proves each failure mode is actually caught, not just that
*some* check fails.

## Development

```bash
uv venv --python 3.13
uv pip install -e ".[dev]"
uv run pytest
uv run ruff check .
uv run black --check .
```

`pyproject.toml` pins `httpx`, `pytest`, `ruff` and `black` versions so a semester-old clone
still builds (per the examples-repo spec's acceptance criterion 4, which this package
follows even though it isn't itself in `apps/examples/`).

## Known gaps

- `checks/ex05_security.py`'s `flawed_repo_tests_pass` and
  `planted_vulnerabilities_unreachable` are stubs: they fail loudly and explain why, rather
  than passing vacuously, until `apps/examples/08-security/` exists (scheduled for lecture 8
  per `handover/05-build-order.md`).
- `workflows/reusable-check.yml` cannot be `uses:`-called from where it lives in this
  package; it needs to be mirrored to `.github/workflows/` at a repo root (this monorepo's,
  or a dedicated infra repo). `templates/exercise-workflow.yml` is the working alternative
  in the meantime and is what should actually be copied into exercise templates today.
- Exercise 2's "both runs present" and exercise 3/4's file-name conventions
  (`DESIGN.md`, `PROMPT_LOG.md`, `PRODUCTION_GAPS.md`, `runs/with-doc.md`, ...) are this
  package's own convention, not yet cross-checked against `apps/examples/03-context/`,
  `04-autonomy/` or `06-ship/`, none of which exist yet (see `docs/resume-state.md`). When
  those folders are written, either match these candidate lists or update both together.
- `checks/ex04_deployment.py`'s `ci_is_green` excludes the currently-running job by matching
  `GITHUB_JOB`, which is a heuristic (GitHub's check-runs API does not expose "the run that
  is asking" directly); if a template names its own check-run job identically to another
  workflow's job, this could under- or over-exclude. Fine for a single-workflow-per-repo
  template, worth revisiting if a template grows a second workflow.
