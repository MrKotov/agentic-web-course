# Agentic Web Development — course infrastructure

Course infrastructure for **Програмиране в Internet** (Programming for the Internet),
Technical University of Sofia, Faculty of Computer Systems and Technologies.

Specs live in [`handover/`](handover/) and are the source of truth. Read
[`CLAUDE.md`](CLAUDE.md) first, then the spec for whatever you are changing.

## Layout

| Path | Deliverable | Spec | Stack |
|---|---|---|---|
| `apps/platform/` | Quiz and research platform | `handover/02-quiz-platform.spec.md` | Django + HTMX + Postgres |
| `apps/site/` | Static course site | `handover/01-course-site.spec.md` | Astro + Starlight |
| `apps/examples/` | Examples and exercise templates | `handover/03-examples-repo.spec.md` | Polyglot + devcontainer |
| `packages/autograder/` | Conformance harness and workflows | `handover/04-autograder.spec.md` | Python + GitHub Actions |

`apps/examples/` and `apps/site/` are developed here but published as separate public
repos — students fork the examples repo, and the site deploys to GitHub Pages. See
[`docs/splitting-repos.md`](docs/splitting-repos.md).

## Priority

`05-build-order.md` orders this by what cannot be recovered if it slips. The quiz
platform through CSV export is load-bearing: the study's baseline measurement must be
collected before lecture 1 and cannot be reconstructed afterwards. Everything else can
slip a week.

## Getting started

Requires Node 24 (`.nvmrc`) and Python 3.13.

```bash
make setup     # install both toolchains
make platform  # run the Django dev server
make site      # run the Astro dev server
make test      # run everything
```

## Working agreements

Spec first, free tier only, no vendor lock-in in student-facing material, Bulgarian for
student-facing text and English for code. The full set is in [`CLAUDE.md`](CLAUDE.md).
