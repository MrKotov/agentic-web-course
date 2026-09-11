"""Exercise 5: adversarial review of the flawed repository.

Two of the four checks here are deterministic today. The other two depend on
`apps/examples/08-security/`, which handover/05-build-order.md schedules for lecture 8 and
which deliberately does not exist yet. They are stubbed and fail loudly rather than passing
vacuously: a check that cannot run must never look like a check that passed.
"""

from __future__ import annotations

import re
from collections.abc import Sequence
from dataclasses import dataclass

from ..context import SubmissionContext
from ..models import CheckResult
from .common import named

FINDINGS_CANDIDATES = ("FINDINGS.md", "findings.md", "docs/FINDINGS.md")

REQUIRED_FIELDS = ("Severity", "Location", "Impact", "Fix")
ALLOWED_SEVERITIES = ("critical", "high", "medium", "low")
MIN_FINDINGS = 3

_HEADING = re.compile(r"^##\s+Finding\s+(\d+)\s*[:.\-—]\s*(.+?)\s*$", re.IGNORECASE | re.MULTILINE)


@dataclass(frozen=True, slots=True)
class _Finding:
    number: str
    title: str
    body: str


def findings_file_format(context: SubmissionContext) -> CheckResult:
    """Pass when FINDINGS.md parses as the required structure.

    Format only. Whether a finding is real is exactly what the defense is for, and the spec
    forbids the grader from guessing.
    """
    name = "findings_file_format"
    path = next((context.path(c) for c in FINDINGS_CANDIDATES if context.exists(c)), None)
    if path is None:
        return CheckResult(
            name,
            False,
            f"No findings file at any of {list(FINDINGS_CANDIDATES)}. Use the template in the "
            "exercise README: one `## Finding N: title` section per finding, each with "
            f"{list(REQUIRED_FIELDS)} lines.",
        )
    text = path.read_text(encoding="utf-8", errors="replace")
    findings = _parse_findings(text)
    if len(findings) < MIN_FINDINGS:
        return CheckResult(
            name,
            False,
            f"{path.name} contains {len(findings)} findings in the required format; at least "
            f"{MIN_FINDINGS} are required. Each one starts with `## Finding N: title`.",
        )
    problems: list[str] = []
    for finding in findings:
        fields = _parse_fields(finding.body)
        missing = [f for f in REQUIRED_FIELDS if f.lower() not in fields]
        if missing:
            problems.append(f"Finding {finding.number} is missing {missing}")
            continue
        severity = fields["severity"].strip().lower()
        if severity not in ALLOWED_SEVERITIES:
            problems.append(
                f"Finding {finding.number}: Severity is {fields['severity']!r}; "
                f"use one of {list(ALLOWED_SEVERITIES)}"
            )
        if not fields["location"].strip():
            problems.append(f"Finding {finding.number}: Location is empty; give file and line")
    if problems:
        return CheckResult(name, False, "\n".join(f"  - {p}" for p in problems))
    return CheckResult(name, True, f"{path.name}: {len(findings)} findings, all fields present.")


def _parse_findings(text: str) -> list[_Finding]:
    matches = list(_HEADING.finditer(text))
    findings: list[_Finding] = []
    for index, match in enumerate(matches):
        end = matches[index + 1].start() if index + 1 < len(matches) else len(text)
        findings.append(_Finding(match.group(1), match.group(2), text[match.end() : end]))
    return findings


def _parse_fields(body: str) -> dict[str, str]:
    fields: dict[str, str] = {}
    for line in body.splitlines():
        stripped = line.strip().lstrip("-*").strip()
        for field in REQUIRED_FIELDS:
            prefix = f"{field.lower()}:"
            if stripped.lower().startswith(prefix) or stripped.lower().startswith(f"**{field.lower()}**:"):
                value = stripped.split(":", 1)[1]
                fields[field.lower()] = value
    return fields


def _stub(name: str, reason: str) -> "object":
    def check(_: SubmissionContext) -> CheckResult:
        return CheckResult(name, False, reason)

    return named(check, name)


# TODO(spec 04, "Exercise 5, adversarial review"): implement once
# apps/examples/08-security/ exists. This check must run the flawed repository's own test
# suite against the student's fixed fork, from the pinned upstream commit, so a student
# cannot pass by deleting tests. Blocked on: the flawed repo, scheduled for lecture 8 in
# handover/05-build-order.md.
flawed_repo_tests_pass = _stub(
    "flawed_repo_tests_pass",
    "Not implemented: apps/examples/08-security/ does not exist yet, so there is no pinned "
    "test suite to run. Tracked against handover/04-autograder.spec.md, exercise 5. This "
    "check fails rather than passing vacuously.",
)

# TODO(spec 04, "Exercise 5, adversarial review"): implement once
# apps/examples/08-security/ exists. Each planted vulnerability needs a paired exploit
# probe (authorisation on the wrong object, client-only validation, the one concatenated
# SQL string, the committed secret) that must succeed against upstream and fail against the
# student's fork. Writing the probes before the flawed repo exists would fix the defects in
# advance, which is the wrong order.
planted_vulnerabilities_unreachable = _stub(
    "planted_vulnerabilities_unreachable",
    "Not implemented: the exploit probes are defined by the planted defects in "
    "apps/examples/08-security/, which does not exist yet. Tracked against "
    "handover/04-autograder.spec.md, exercise 5.",
)


def register_all() -> Sequence[object]:
    return (findings_file_format, flawed_repo_tests_pass, planted_vulnerabilities_unreachable)


findings_file_format.check_name = "findings_file_format"  # type: ignore[attr-defined]
