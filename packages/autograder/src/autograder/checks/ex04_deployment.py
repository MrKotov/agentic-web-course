"""Exercise 4: deployment.

Per handover/04-autograder.spec.md: "Deployed URL returns 200, smoke test passes, CI is
green, production-gap report present. Secrets not in the repo, checked by scan." Which
production gaps matter is a defense question; the harness only checks that the report
exists and is substantive.
"""

from __future__ import annotations

import os
import subprocess
import sys

import httpx

from ..context import SubmissionContext
from ..models import CheckResult
from .common import Check, file_non_trivial, named, secret_scan

GAP_REPORT_CANDIDATES = ("PRODUCTION_GAPS.md", "docs/PRODUCTION_GAPS.md", "GAPS.md")
SMOKE_TEST_CANDIDATES = ("scripts/smoke.sh", "smoke.sh", "scripts/smoke.py", "smoke_test.py")

_GAP_HINT = (
    "See apps/examples/06-ship/README.md: name the gaps between this deployment and a real "
    "production rollout (observability, secrets rotation, scaling, backups, ...) and why "
    "each one does or does not matter here."
)


def _deployed_url_check(context: SubmissionContext) -> CheckResult:
    name = "deployed_url_returns_200"
    if not context.deployed_url:
        return CheckResult(
            name,
            False,
            "No deployed URL was supplied. Set the DEPLOYED_URL workflow input/variable "
            "documented in apps/examples/06-ship/README.md.",
        )
    try:
        response = httpx.get(context.deployed_url, timeout=20, follow_redirects=True)
    except httpx.HTTPError as exc:
        return CheckResult(
            name, False, f"GET {context.deployed_url} failed: {type(exc).__name__}: {exc}"
        )
    if response.status_code == 200:
        return CheckResult(name, True, f"GET {context.deployed_url} returned 200.")
    return CheckResult(
        name,
        False,
        f"GET {context.deployed_url} returned {response.status_code}, expected 200.",
    )


deployed_url_returns_200 = named(_deployed_url_check, "deployed_url_returns_200")


def _smoke_test_check(context: SubmissionContext) -> CheckResult:
    name = "smoke_test_passes"
    hint = (
        "Add a smoke test script (see apps/examples/06-ship/README.md) at one of "
        f"{list(SMOKE_TEST_CANDIDATES)} that exercises the deployed app end to end and "
        "exits non-zero on failure."
    )
    script = next((p for p in SMOKE_TEST_CANDIDATES if context.exists(p)), None)
    if script is None:
        return CheckResult(name, False, f"No smoke test found. {hint}")
    path = context.path(script)
    argv = [str(path)] if os.access(path, os.X_OK) else [sys.executable, str(path)]
    env = {**os.environ}
    if context.deployed_url:
        env["DEPLOYED_URL"] = context.deployed_url
    try:
        completed = subprocess.run(
            argv,
            cwd=str(context.repo_path),
            env=env,
            capture_output=True,
            text=True,
            timeout=60,
            check=False,
        )
    except (OSError, subprocess.TimeoutExpired) as exc:
        return CheckResult(name, False, f"Could not run {script}: {exc}. {hint}")
    if completed.returncode == 0:
        return CheckResult(name, True, f"{script} exited 0.")
    tail = (completed.stdout + completed.stderr).strip()[-2000:]
    return CheckResult(name, False, f"{script} exited {completed.returncode}. Output:\n{tail}")


smoke_test_passes = named(_smoke_test_check, "smoke_test_passes")


def _ci_green_check(context: SubmissionContext) -> CheckResult:
    """Pass when every completed GitHub Actions check run on this commit succeeded.

    Reads the GitHub check-runs API for `context.repo`/`context.commit`. Works unauthenticated
    for public repos (rate-limited); set GITHUB_TOKEN in the workflow environment for private
    repos or a higher rate limit — this is the ambient Actions token, never a secret the
    student manages, so it is safe to read from the environment here.
    """
    name = "ci_is_green"
    if context.repo == "unknown" or context.commit == "unknown":
        return CheckResult(name, False, "Could not determine repo/commit to query CI status for.")
    url = f"https://api.github.com/repos/{context.repo}/commits/{context.commit}/check-runs"
    headers = {"Accept": "application/vnd.github+json"}
    token = os.environ.get("GITHUB_TOKEN")
    if token:
        headers["Authorization"] = f"Bearer {token}"
    try:
        response = httpx.get(url, headers=headers, timeout=20)
    except httpx.HTTPError as exc:
        return CheckResult(name, False, f"Could not reach the GitHub API: {exc}")
    if response.status_code != 200:
        return CheckResult(
            name,
            False,
            f"GitHub API returned {response.status_code} for {url}: {response.text[:300]}",
        )
    payload = response.json()
    runs = payload.get("check_runs", []) if isinstance(payload, dict) else []
    # Exclude the run that is executing this very check: it cannot have concluded yet.
    relevant = [r for r in runs if r.get("name") != os.environ.get("GITHUB_JOB")]
    if not relevant:
        return CheckResult(name, False, f"No completed check runs found for {context.commit}.")
    incomplete = [r for r in relevant if r.get("status") != "completed"]
    if incomplete:
        return CheckResult(
            name,
            False,
            f"{len(incomplete)} check run(s) have not completed yet: "
            f"{[r.get('name') for r in incomplete]}.",
        )
    ok_conclusions = {"success", "skipped", "neutral"}
    failing = [r for r in relevant if r.get("conclusion") not in ok_conclusions]
    if failing:
        return CheckResult(
            name,
            False,
            "These check runs did not succeed: "
            + ", ".join(f"{r.get('name')}={r.get('conclusion')}" for r in failing),
        )
    return CheckResult(name, True, f"{len(relevant)} check run(s), all green.")


ci_is_green = named(_ci_green_check, "ci_is_green")

production_gap_report_present = file_non_trivial(
    "production_gap_report_present",
    GAP_REPORT_CANDIDATES,
    min_words=100,
    required_sections=(),
    hint=_GAP_HINT,
)

secrets_not_committed = secret_scan("secrets_not_committed")


def register_all() -> tuple[Check, ...]:
    return (
        deployed_url_returns_200,
        smoke_test_passes,
        ci_is_green,
        production_gap_report_present,
        secrets_not_committed,
    )
