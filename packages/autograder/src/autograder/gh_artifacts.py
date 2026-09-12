"""Minimal GitHub REST client used by the `collect` CLI verb.

Used only by the instructor-side collector (see `README.md`, "Secret handling"): it reads
workflow-run artifacts from student repositories with a read-only token that never touches a
student's fork, then hands the extracted result JSON to `webhook.WebhookClient`, which owns
the shared secret. Nothing here runs inside a student's workflow.
"""

from __future__ import annotations

import io
import json
import zipfile
from dataclasses import dataclass
from typing import Any

import httpx

API_ROOT = "https://api.github.com"
RESULT_ARTIFACT_NAME = "autograder-result"
RESULT_FILE_NAME = "result.json"


class GitHubApiError(RuntimeError):
    """The GitHub API returned something the collector cannot use."""


@dataclass(frozen=True, slots=True)
class GitHubClient:
    """A thin, read-only wrapper. `token` should be a fine-grained PAT scoped to
    `actions:read` on the roster's repositories, held only by the instructor's collector
    (see README) — never by a student's workflow."""

    token: str
    timeout_seconds: float = 20.0

    def _headers(self) -> dict[str, str]:
        return {"Accept": "application/vnd.github+json", "Authorization": f"Bearer {self.token}"}

    def latest_run_id(self, repo: str, *, branch: str | None = None) -> int | None:
        """The id of the most recent workflow run for `repo`, or None if there is none yet."""
        params: dict[str, Any] = {"per_page": 1}
        if branch:
            params["branch"] = branch
        response = httpx.get(
            f"{API_ROOT}/repos/{repo}/actions/runs",
            headers=self._headers(),
            params=params,
            timeout=self.timeout_seconds,
        )
        _raise_for_status(response, context=f"listing runs for {repo}")
        runs = response.json().get("workflow_runs", [])
        return runs[0]["id"] if runs else None

    def find_result_artifact(self, repo: str, run_id: int) -> dict[str, Any] | None:
        """The artifact metadata for `RESULT_ARTIFACT_NAME` on this run, if it exists."""
        response = httpx.get(
            f"{API_ROOT}/repos/{repo}/actions/runs/{run_id}/artifacts",
            headers=self._headers(),
            timeout=self.timeout_seconds,
        )
        _raise_for_status(response, context=f"listing artifacts for {repo} run {run_id}")
        for artifact in response.json().get("artifacts", []):
            if artifact.get("name") == RESULT_ARTIFACT_NAME and not artifact.get("expired"):
                return artifact
        return None

    def download_result_json(self, repo: str, artifact_id: int) -> dict[str, Any]:
        """Download and unzip the artifact, returning the parsed `result.json`."""
        response = httpx.get(
            f"{API_ROOT}/repos/{repo}/actions/artifacts/{artifact_id}/zip",
            headers=self._headers(),
            timeout=self.timeout_seconds,
            follow_redirects=True,
        )
        _raise_for_status(response, context=f"downloading artifact {artifact_id} for {repo}")
        with zipfile.ZipFile(io.BytesIO(response.content)) as archive:
            try:
                raw = archive.read(RESULT_FILE_NAME)
            except KeyError as exc:
                raise GitHubApiError(
                    f"artifact {artifact_id} for {repo} does not contain {RESULT_FILE_NAME}"
                ) from exc
        return json.loads(raw.decode("utf-8"))


def _raise_for_status(response: httpx.Response, *, context: str) -> None:
    if response.status_code >= 400:
        raise GitHubApiError(
            f"GitHub API error while {context}: {response.status_code} {response.text[:300]}"
        )
