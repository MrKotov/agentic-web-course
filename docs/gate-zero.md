# Gate zero — blockers outside the codebase

From `handover/05-build-order.md`: *"Ordered by what cannot be recovered if it slips, not
by what is most interesting."*

Nothing here is code. All of it blocks code, and two items cannot be recovered at all if
they slip. Owner is the course instructor in every case — an agent cannot close any of
these. Status is tracked here so the build does not quietly proceed on unverified
assumptions.

## Cannot be recovered if late

| # | Item | Blocks | Status |
|---|---|---|---|
| 1 | **Ethics approval** for the pre/post study | The baseline measurement, therefore the study | ☐ Not started |
| 2 | **Hosting decision** for the platform | The ethics application (decides the data controller) | ☐ Not started |

**These two are ordered.** Hosting determines who the data controller is, and that goes
*into* the ethics application — so hosting is settled first, not after. University
infrastructure is the clean answer; a personal VPS makes the instructor personally the
controller and complicates the application.

If ethics approval is late: lecture 1 happens without a baseline, and the study is dead
for this cohort. The course still runs; the paper does not. There is no retroactive fix —
the baseline measures what students knew *before* being taught, and that state is gone
once the lecture happens.

## Can invalidate a design — check before building on them

| # | Check | If it fails | Status |
|---|---|---|---|
| 3 | **Load-test the free tier** with 30 concurrent agent runs | The lab plan changes. OpenRouter free models are best-effort, rate-limited around 20 req/min. Ollama is the offline fallback | ☐ Not started |
| 4 | **VoltAgent console** — are its execution traces presentable? | If yes, the agent-loop stepper is never built. It is the most expensive component on the site | ☐ Not started |
| 5 | **Browser-origin API calls** from a clean browser | If CORS blocks them, the playground needs a thin proxy — which changes who holds the keys and what students are told | ☐ Not started |
| 6 | **Devcontainer on locked-down lab machines** | Decides whether the primary tool is a CLI agent or browser-based | ☐ Not started |

Items 4 and 5 are load-bearing for `apps/site/`. The site has been built with the
agent-loop stepper deliberately **not** implemented (item 4 unresolved) and with the
browser-direct key design flagged rather than assumed (item 5 unresolved). Resolve them
before either is treated as settled.

Item 3 is in the risk register as "lab session collapses". One developer's experience of
a free tier tells you nothing about 30 simultaneous students; test with a real group.

## Open questions from `06-decisions-and-constraints.md`

| # | Question | Decides | Status |
|---|---|---|---|
| 7 | Lab machine policy — can students install Node and Python? | CLI agent vs browser-based as the primary tool | ☐ Open |
| 8 | Exam weighting vs department rules | Whether the continuous-assessment path survives contact with regulation | ☐ Open |
| 9 | Group size and teaming | Project assumes teams of 2-3; confirm against cohort size | ☐ Open |

## Standing constraints

These are settled and not revisited:

- **GitHub Classroom is gone.** Shut down 28 August 2026, data deleted 4 September. Never
  suggested, never referenced as an option.
- **Nothing in the student path costs money.** If a dependency has no free tier, say so
  instead of adding it.
- **No student data leaves university control.** No third-party SaaS.
- **Every demo works from a recording with no network.** The hall wifi is expected to fail;
  recorded mode is a hard requirement, not a nice-to-have.
- **The baseline happens before lecture 1** or the study does not happen.
