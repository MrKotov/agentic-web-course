# Project context

University course infrastructure for "Програмиране в Internet" (Programming for the
Internet) at the Technical University of Sofia, Faculty of Computer Systems and
Technologies. The course teaches agentic software engineering to undergraduate web
developers.

Four deliverables: a static course site, a quiz and research platform, an examples repo,
and an autograder. Specs are in the sibling `.spec.md` files.

## Audience

Undergraduates who do not yet know backend or frontend architecture. They learn to build
with agents first, then take apart what they built. Assume no prior knowledge of HTTP,
REST, ORMs, or deployment when writing anything student-facing.

## Working agreements

- **Spec first.** Every non-trivial change starts from a written spec or an update to one.
  The course teaches spec-driven development; the course's own code follows it. If a spec
  is missing or wrong, fix the spec before the code.
- **Keep prompt logs.** Commit the prompts used to build this. They become teaching
  material, and the platform itself is intended to be the legacy codebase students inherit
  in lecture 9.
- **Free tier only.** Nothing in the student path may require payment. If a dependency has
  no free tier, say so instead of adding it.
- **No vendor lock in student-facing material.** Course content names capabilities
  ("an agent with tool calling"), never products. Concrete tools appear only in lab
  instructions, where they can be swapped per semester.
- **Bulgarian for student-facing text, English for code.** UI strings, quiz questions and
  lecture content are Bulgarian. Identifiers, comments, commit messages, and these specs
  are English.

## Stack decisions, already settled

| Component | Choice | Why |
|---|---|---|
| Course site | Astro + Starlight | MDX content, React islands, free on GitHub Pages |
| Diagrams and chains | React Flow (xyflow, MIT) | Animated node/edge graphs for agent loops |
| Platform | Django + HTMX + Postgres | Admin panel removes weeks of CRUD; analysis is Python |
| Agent frameworks taught | VoltAgent and LangGraph.js | Both TypeScript; used after the loop is hand-rolled |
| Model access | OpenRouter (BYO key), GitHub Copilot via Student Pack | No card needed; Ollama as offline fallback |
| Submission | Template repos + GitHub Actions | GitHub Classroom shut down 28 Aug 2026 |

## Constraints that are not negotiable

- **GitHub Classroom does not exist.** It shut down on 28 August 2026 and data was deleted
  on 4 September. Never suggest it.
- **The baseline measurement cannot be retrofitted.** The quiz platform must be able to run
  a pre-lecture test before lecture 1. Everything else in the platform can wait.
- **Research data stays inside the university.** No student data to third-party SaaS. Where
  the platform is hosted determines who the data controller is, which goes into the ethics
  application.
- **Rate limits are a classroom risk.** Free-tier limits that look fine for one developer
  fail when 30 students run agents simultaneously. Any tool in the student path must be
  load-tested with a real group before it is written into the requirements.

## Conventions

- Python: ruff, black, type hints on anything public. Pytest.
- TypeScript: strict mode, no `any` in committed code.
- Commits: imperative subject, body explains why. Reference the spec section when the
  change implements one.
- Secrets never in the repo. `.env.example` documents every variable.
- Every student-facing repo ships a devcontainer so "works on my machine" is not a class
  of support request.
