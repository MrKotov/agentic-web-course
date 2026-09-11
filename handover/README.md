# Handover: Agentic Web Development course, TU-Sofia

Redesign of "Програмиране в Internet" for the coming academic year. Agentic-first
sequencing: students build with agents from lecture 2, and lectures 5 to 6 take apart
what they already built. Web fundamentals are the material for that teardown, not a
separate block at the front.

Format: 10 lectures, 5 lab exercises, paper exam as the second grading path.

## What these documents are

Specs written to be handed to a coding agent. Each one states a goal, explicit
non-goals, constraints, and acceptance criteria. Read `CLAUDE.md` first, then the spec
for whatever you are building. `05-build-order.md` says what has to exist by when and
why.

| File | Covers |
|---|---|
| `CLAUDE.md` | Project context and working agreements. Copy into each repo you create. |
| `01-course-site.spec.md` | Static site: notes, interactive widgets, what you present from |
| `02-quiz-platform.spec.md` | Own app: roster, timed quizzes, research data export |
| `03-examples-repo.spec.md` | Demos for each lecture, exercise templates, the two flawed repos |
| `04-autograder.spec.md` | GitHub Actions checks and the webhook into the platform |
| `05-build-order.md` | Sequence, what gates what, effort estimates |
| `06-decisions-and-constraints.md` | Settled decisions, open questions, non-goals |

## Four things get built

1. **Course site**, static and public, no login. Astro + Starlight on GitHub Pages.
2. **Quiz and research platform**, own app with login. Django + HTMX + Postgres.
3. **Examples repo**, per-lecture demos and exercise templates.
4. **Autograder**, GitHub Actions in the exercise templates, results posted to the platform.

## Not being built

- Slide decks. The site is presented full screen. Two copies of the content diverge by
  the third lecture.
- An agent framework. VoltAgent and LangGraph.js are both used as-is.
- An LMS. The quiz platform covers what is needed.
- Plagiarism detection. Meaningless when AI use is allowed; the oral defense replaces it.
- An agent-loop visualiser, **pending a check** on whether VoltAgent's console already
  covers it. Verify before writing any of it.

## Background this rests on

- Stanford CS146S, The Modern Software Developer (Fall 2025), for assignment design.
- Syllabus analysis of 23 AI-assisted SE courses (arXiv 2608.05898) for assessment weights
  and topic coverage.
- Anthropic RCT on skill formation: 17% lower comprehension scores with AI assistance when
  learning unfamiliar material, with interaction style the deciding variable, not tool use
  itself. This is why explanation and defense carry so much weight in the grading.
- MCP was donated to the Linux Foundation's Agentic AI Foundation in December 2025, so it
  is taught as a vendor-neutral standard.
