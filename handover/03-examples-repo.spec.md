# Spec: examples repo

The code students clone, run and are graded on. One public repo, forkable, with a folder
per lecture.

## Structure

```
agentic-web-course/
  .devcontainer/            identical environment for everyone
  00-setup/                 keys, access check, hello-world call
  01-variance/              one prompt, ten runs, schema diff
  02-mcp-server/            EXERCISE 1: MCP server from scratch
  03-context/               EXERCISE 2: same task with and without a design doc
  04-autonomy/              EXERCISE 3: feature shipped by directing an agent
  05-backend-reveal/        annotated teardown of generated backend
  06-ship/                  EXERCISE 4: containerise, CI, deploy, production-gap report
  07-eval/                  scanning output, real vs false positives
  08-security/              EXERCISE 5: repo with planted vulnerabilities
  09-brownfield/            unfamiliar legacy repo
  10-economics/            token cost calculator
```

Every folder contains the same four things: `README.md` with goal and expected result,
`demo/` for what the instructor runs in the hall, `exercise/` with the assignment, and
`solution/` held on a branch that merges after the deadline.

## The two repos that must be written by hand

These cannot be generated the week before. They are the most expensive part of the whole
build and the quality of two lectures depends entirely on them.

**`08-security/`** A small working application with planted vulnerabilities that look like
what an agent actually produces: correct locally, wrong at trust boundaries. Authorisation
checked on the wrong object. Validation on the client only. A SQL string built by
concatenation in exactly one forgotten place. Secrets read from a config file committed
three commits ago. The defects must survive a casual read; obvious bugs teach nothing.

**`09-brownfield/`** An unfamiliar codebase with real archaeology in it: inconsistent
naming from two authors, a dead abstraction someone half-migrated away from, a comment that
contradicts the code, a test that passes for the wrong reason. Students point an agent at it
and have to explain what they found.

Cheapest honest source for `09`: the quiz platform itself, if it was built with agents and
the prompt logs were kept. Genuinely inherited code, written under exactly the conditions
the lecture is about.

## Exercise definitions

| # | Deliverable | Machine-checkable | Goes to defense |
|---|---|---|---|
| 1 | MCP server, no framework | responds to `tools/list`, invokes a tool per spec | why these tool boundaries |
| 2 | Design doc, then agent builds from it | doc present, build runs, outputs diffed | what the doc prevented |
| 3 | Feature shipped by directing an agent | tests pass, prompt log present | where checkpoints were placed |
| 4 | Deployed app + production-gap report | URL returns 200, CI green, report present | which gaps matter and why |
| 5 | Adversarial review of flawed repo | findings file present, fixes pass tests | which findings are real |

## Acceptance criteria

1. A student clones, opens the devcontainer, and completes `00-setup` in under 15 minutes
   on a lab machine.
2. Every `demo/` runs from a recording with no key and no network.
3. Every exercise has a failing test suite that passes when the work is done correctly.
4. Dependency versions are pinned. A semester-old clone still builds.
5. No secrets anywhere in history.
