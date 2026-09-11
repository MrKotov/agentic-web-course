# Decisions and constraints

## Settled

**Sequencing is agentic-first.** Students build with agents from lecture 2. Lectures 5 and 6
take apart what they built, using it as the worked example for HTTP, REST, data modelling,
ORMs, rendering and deployment. Web fundamentals are not a separate block at the front.

The evidence says this ordering is fine but not free. Anthropic's RCT found 17% lower
comprehension scores among developers using AI on unfamiliar material, with no significant
speed gain, and found that *how* people interact decides the outcome: wholesale delegation
correlates with poor skill acquisition, explanation-seeking use shows no penalty. So the
safeguard is not front-loading fundamentals, it is requiring explanatory-mode interaction in
early exercises and making defense carry 25% of the continuous-assessment grade.

**Cut from the old conspectus.** CGI and ASP history, legacy DHTML and XHTML, IE-era
features, manual prototype wiring, raw event-bubbling mechanics, deep closure drilling. The
event loop survives as a single sentence explaining why you await, not as a topic.

**Kept.** REST vs GraphQL, HTTP methods, data modelling, ORM and repository pattern, the
security block (CSRF, injection, phishing, DDoS), now framed around vulnerabilities in
generated code.

**Two grading paths.** Continuous assessment is project 50%, five exercises 25%, defense
25%, and clearing it exempts from the exam. Admission requires all five exercises, a
deployed project, and attendance at the defense. Missing any of the three means sitting the
paper exam.

**Paper exam.** 40% annotating a printed listing of generated code with planted defects,
20% diagnosing where an agent went wrong from a spec and transcript, 20% short questions
from the conspectus, 20% hand-writing a one-page spec. Paper is an advantage here:
comprehension is the one thing that cannot be delegated in the room.

**Project bar has moved.** The old CRUD-plus-integration project is no longer a measure of
anything, since an agent produces it in an afternoon. Minimum is now a deployed app with one
tool-calling feature over the student's own data model exposed through MCP, plus the spec
written before the code and a prompt log. Higher marks come from an eval harness for the
agent feature, a review report of what the agent got wrong, a brownfield extension, and a
cost report. Code volume carries no marks.

**Frameworks come after the hand-rolled loop.** Lecture 2 builds the loop and an MCP server
by hand. VoltAgent and LangGraph.js appear from lecture 4. Starting from a framework hides
the mechanism the course exists to teach.

## Open

1. **Lab machine policy.** Can students install CLI tools, Node and Python, or are the
   machines locked down? Decides whether the primary tool is a CLI agent or browser-based.
2. **Platform hosting.** University infrastructure or personal VPS. Determines the data
   controller. Blocks the ethics application.
3. **Exam weighting versus department rules.** The department may mandate a minimum exam
   weight that conflicts with the continuous-assessment path.
4. **Group size and teaming.** Project assumes teams of two or three. Confirm against
   cohort size.

## Non-negotiable

- GitHub Classroom is gone. Shut down 28 August 2026, data deleted 4 September.
- Nothing in the student path costs money.
- No student data leaves university control.
- Every demo works from a recording with no network.
- The baseline measurement happens before lecture 1 or the study does not happen.

## Things to verify before building on them

- Does VoltAgent's console remove the need for a custom agent-loop visualiser?
- Do browser-origin API calls work with the chosen provider, or is a proxy needed?
- Does the free tier survive 30 simultaneous student agent runs?
- Do exercise repos need a devcontainer that works on locked-down lab machines?
