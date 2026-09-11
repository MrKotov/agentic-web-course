"""The result contract shared with the quiz platform.

The JSON shape is fixed by handover/04-autograder.spec.md, section "Result format".
Nothing may be added to the wire format without updating that spec first.
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from datetime import UTC, datetime
from typing import Any


@dataclass(frozen=True, slots=True)
class CheckResult:
    """The outcome of a single check. A check passes or it does not; there is no partial credit.

    `detail` must be actionable by a student when the check fails: say what was expected,
    what was observed, and where to look.
    """

    name: str
    passed: bool
    detail: str | None = None

    def to_dict(self) -> dict[str, Any]:
        payload: dict[str, Any] = {"name": self.name, "passed": self.passed}
        if self.detail:
            payload["detail"] = self.detail
        return payload


@dataclass(frozen=True, slots=True)
class RunResult:
    """The full submission payload posted to the platform."""

    exercise: str
    repo: str
    commit: str
    checks: list[CheckResult] = field(default_factory=list)
    completed_at: datetime = field(default_factory=lambda: datetime.now(UTC))

    @property
    def passed(self) -> bool:
        return all(check.passed for check in self.checks)

    def to_dict(self) -> dict[str, Any]:
        return {
            "exercise": self.exercise,
            "repo": self.repo,
            "commit": self.commit,
            "checks": [check.to_dict() for check in self.checks],
            "completed_at": _iso_z(self.completed_at),
        }

    def to_json(self, *, indent: int | None = 2) -> str:
        return json.dumps(self.to_dict(), indent=indent, sort_keys=False)


def _iso_z(moment: datetime) -> str:
    """Render as RFC 3339 in UTC with a trailing Z, second precision, as in the spec."""
    return moment.astimezone(UTC).replace(microsecond=0).isoformat().replace("+00:00", "Z")
