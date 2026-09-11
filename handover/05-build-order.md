# Build order

Ordered by what cannot be recovered if it slips, not by what is most interesting.

## Gate zero, before anything is written

Two things that are outside your control and block work downstream. Start both this week.

- **Ethics approval** for the pre/post study. If it is late, lecture 1 happens without a
  baseline and the study is dead for this cohort. The course still runs; the paper does not.
- **Hosting decision** for the platform. University infrastructure or personal VPS. This
  determines who the data controller is and it goes into the ethics application, so it has
  to be settled first, not after.

Also worth doing early because it can invalidate a design:

- **Load-test the free tier** with 30 concurrent agent runs. OpenRouter's free models are
  best-effort and rate-limited at around 20 requests per minute. If that fails, the lab
  plan changes.
- **Check VoltAgent's console.** If its execution traces are presentable, the agent-loop
  stepper never gets built, which is the most expensive component on the site.
- **Test browser-origin API calls** from a clean browser. If CORS blocks them, the
  playground needs a proxy and the key-handling story changes.

## Before lecture 1

| Item | Effort | Why now |
|---|---|---|
| Quiz platform MVP through CSV export | ~2 weeks | Baseline cannot be collected retroactively |
| Consent flow | included above | Must be in place before the first item is answered |
| Lecture 1 and 2 content on the site | ~3 days scaffold + 2 days content | Two lectures of runway |
| Prompt variance component, recorded mode | ~2 days | It is the lecture 1 demo |
| Exercise 1 template + MCP conformance grader | ~2 days | Issued at lecture 2 |

## Rolling through the semester

Stay two lectures ahead on content, roughly a day per lecture page. Issue each exercise
template a week before it is needed.

## Fixed later deadlines

| By | Item | Effort |
|---|---|---|
| Lecture 5 | Backend teardown material, which depends on real student code from exercise 3 | 1 day, but only after exercise 3 is marked |
| Lecture 6 | Deployment exercise template | 1 day |
| **Lecture 8** | **`08-security/` flawed repo** | **3-4 days, cannot be rushed** |
| Lecture 9 | `09-brownfield/` repo, or use the platform itself | 1 day if reusing the platform |
| Lecture 10 | Cost calculator | 1 day |

The security repo is the one to start early during a quiet week. Planted defects that are
too obvious make the lecture worthless, and realism takes iteration.

## Deferred until after three lectures have run

Dashboards, retention curves, autograder result roll-ups, per-student progress views. Build
them when you know what you actually look at, not what you imagine now.

## Risk register

| Risk | Impact | Mitigation |
|---|---|---|
| Ethics approval late | Study lost for this cohort | Submit now; course proceeds regardless |
| Free tier fails under 30 students | Lab session collapses | Load test early; Ollama offline fallback |
| Hall network unreliable | Demos fail live | Recorded mode is a hard requirement, not optional |
| Security repo rushed | Two lectures lose their point | Schedule it in a quiet week, not the week before |
| Platform scope creep | Nothing ready for lecture 1 | v1 is roster, quiz, live view, export. Nothing else. |
