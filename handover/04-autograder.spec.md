# Spec: autograder

GitHub Actions workflows living inside the exercise templates, posting results to the quiz
platform. No third-party service.

GitHub Classroom shut down on 28 August 2026 and its data was deleted on 4 September. This
replaces it.

## Principle

**Grade behaviour, not code.** With agents in the loop, code volume and style carry no
signal. What a machine can decide is whether the thing conforms and runs. Everything about
quality goes to the oral defense.

This split has to be explicit to students from week one, or they will optimise for the
grader.

## Flow

1. Student forks the exercise template into their own repo.
2. Push triggers the workflow.
3. Workflow runs the conformance suite and writes a result JSON.
4. Workflow posts it to the platform with a shared secret.
5. Platform records submission, timestamp, pass/fail per check.

Student sees their result in the Actions log. Instructor sees the roll-up.

## What gets checked, per exercise

**Exercise 1, MCP server.** The substantive one. A test harness speaks MCP to their server:
does it respond to `tools/list` with a valid schema, does it invoke the named tool with the
right arguments, does it handle an unknown tool without crashing. Fully deterministic and a
genuine test of understanding.

**Exercise 2, spec-driven.** Design doc exists and is non-trivial. Build runs. Both runs
(with and without the doc) are present for the diff.

**Exercise 3, agent-directed feature.** Their tests pass. Prompt log present and covers the
period of the commits.

**Exercise 4, deployment.** Deployed URL returns 200, smoke test passes, CI is green,
production-gap report present. Secrets not in the repo, checked by scan.

**Exercise 5, adversarial review.** Findings file present in the required format, fixes
applied, the flawed repo's test suite passes, planted vulnerabilities no longer reachable.

## Result format

```json
{
  "exercise": "01-mcp-server",
  "repo": "student/agentic-ex1",
  "commit": "abc123",
  "checks": [
    {"name": "tools_list_responds", "passed": true},
    {"name": "tool_invocation_matches_spec", "passed": false, "detail": "..."}
  ],
  "completed_at": "2026-10-14T09:12:00Z"
}
```

Platform endpoint accepts this, authenticates by shared secret, and is idempotent on
`(repo, commit)`.

## Explicitly not doing

- No plagiarism detection. AI use is permitted; similarity means nothing here.
- No style or complexity scoring. An agent will optimise straight past it.
- No partial credit heuristics. A check passes or it does not; nuance is the defense's job.

## Acceptance criteria

1. A correct solution passes all checks on a clean fork with no manual steps.
2. A deliberately broken solution fails with a message a student can act on.
3. The workflow completes within 5 minutes on free runners.
4. A failed webhook post retries and never silently loses a submission.
5. No secret needed by the student appears in the template repo.
