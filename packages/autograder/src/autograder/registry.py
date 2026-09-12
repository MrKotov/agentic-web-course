"""Per-exercise check registry.

A check is a callable `(SubmissionContext) -> CheckResult | list[CheckResult]`. Returning a
list lets one expensive probe (starting a student's server, say) answer several questions
without being repeated. Exercises own an ordered list of checks; adding an exercise means
registering a list and nothing else in the harness changes.
"""

from __future__ import annotations

from collections.abc import Callable, Iterable, Sequence

from .context import SubmissionContext
from .models import CheckResult

Check = Callable[[SubmissionContext], "CheckResult | Sequence[CheckResult]"]

_REGISTRY: dict[str, list[Check]] = {}


def register(exercise: str, checks: Iterable[Check]) -> None:
    """Register the ordered check list for an exercise id (e.g. `01-mcp-server`)."""
    _REGISTRY[exercise] = list(checks)


def checks_for(exercise: str) -> list[Check]:
    try:
        return _REGISTRY[exercise]
    except KeyError:
        raise UnknownExercise(exercise) from None


def known_exercises() -> list[str]:
    return sorted(_REGISTRY)


def declared_names(check: Check) -> list[str]:
    """The check names a callable promises to emit.

    Grouped checks declare `check_names` so that a crash still produces the same rows, and
    the platform roll-up keeps a stable column set across runs.
    """
    names = getattr(check, "check_names", None)
    if names:
        return list(names)
    return [getattr(check, "check_name", getattr(check, "__name__", "unnamed_check"))]


class UnknownExercise(KeyError):
    """Raised when an exercise id has no registered checks."""

    def __init__(self, exercise: str) -> None:
        super().__init__(exercise)
        self.exercise = exercise

    def __str__(self) -> str:
        return f"no checks registered for exercise {self.exercise!r}; known: {known_exercises()}"


def safe_run(check: Check, context: SubmissionContext) -> list[CheckResult]:
    """Run one check, converting an unexpected exception into failed checks.

    A crashing check must never take the run down: the other checks still carry information
    and the submission must still reach the platform.
    """
    try:
        outcome = check(context)
    except Exception as exc:
        detail = (
            f"The check crashed: {type(exc).__name__}: {exc}. "
            "This usually means the submission behaved in a way the harness did not expect. "
            "If your repository looks correct, report this to the instructor."
        )
        return [
            CheckResult(name=name, passed=False, detail=detail) for name in declared_names(check)
        ]
    if isinstance(outcome, CheckResult):
        return [outcome]
    return list(outcome)
