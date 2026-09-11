"""Run the registered checks for an exercise and build the result payload."""

from __future__ import annotations

from .context import SubmissionContext
from .models import RunResult
from .registry import checks_for, safe_run


def run_exercise(exercise: str, context: SubmissionContext) -> RunResult:
    """Run every check registered for `exercise` against `context`.

    All checks always run; there is no short-circuit on first failure, because the student
    needs the full picture from one Actions log rather than one failure per push.
    """
    results = []
    for check in checks_for(exercise):
        results.extend(safe_run(check, context))
    return RunResult(
        exercise=exercise,
        repo=context.repo,
        commit=context.commit,
        checks=results,
    )
