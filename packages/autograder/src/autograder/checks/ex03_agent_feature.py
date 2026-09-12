"""Exercise 3: agent-directed feature.

Per handover/04-autograder.spec.md: "Their tests pass. Prompt log present and covers the
period of the commits." Where the agent was checked in and redirected is a defense
question; the harness only checks that the tests are green and that a log exists whose
dates plausibly bracket the work.
"""

from __future__ import annotations

from .common import Check, command_succeeds, prompt_log_covers_commits

PROMPT_LOG_CANDIDATES = ("PROMPT_LOG.md", "docs/PROMPT_LOG.md", "prompts/", "prompt-log/")

_HINT = (
    "See apps/examples/04-autonomy/README.md: keep PROMPT_LOG.md (or prompts/*.md) with one "
    "`## <date>` (or `### <date>`) heading per session, written as you went."
)

tests_pass: Check = command_succeeds(
    "tests_pass",
    "make test",
    skip_if_missing=("Makefile", "package.json", "pyproject.toml"),
    hint="The feature must ship with a passing test suite, runnable via `make test`.",
)

prompt_log_present: Check = prompt_log_covers_commits(
    "prompt_log_covers_commits",
    PROMPT_LOG_CANDIDATES,
    min_entries=1,
    hint=_HINT,
)


def register_all() -> tuple[Check, ...]:
    return (tests_pass, prompt_log_present)
