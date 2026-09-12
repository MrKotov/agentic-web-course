"""Posts a `RunResult` to the platform's ingest endpoint.

Contract (matched exactly against `apps/platform/autograder/views.py`, which this package
must not edit):

- `POST <base_url>/results/`
- header `X-Autograder-Secret: <shared secret>`, compared with `hmac.compare_digest` on the
  platform side.
- JSON body is exactly `RunResult.to_dict()` (handover/04, "Result format").
- the platform is idempotent on `(repo, commit)`: a retried POST for the same submission
  upserts rather than duplicating, so retrying here is always safe.
- responses: 201 (created) or 200 (updated) on success, 400 on a malformed payload, 401 on a
  bad secret. Only network errors, timeouts and 5xx are retried; 4xx means the payload or
  the secret is wrong and retrying would not help.

Acceptance criterion 4 ("a failed webhook post retries and never silently loses a
submission") is implemented here: `post_with_retry` retries with exponential backoff, and on
final failure writes the result JSON to a local recovery file rather than raising past the
caller silently. The recovery directory is also where GitHub Actions should point an
`upload-artifact` step, so a submission that never reaches the platform is still recoverable
from the workflow run.
"""

from __future__ import annotations

import json
import logging
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import httpx

from .models import RunResult

logger = logging.getLogger(__name__)

SECRET_HEADER = "X-Autograder-Secret"
RESULTS_PATH = "results/"

DEFAULT_RECOVERY_DIR = Path("autograder-recovery")
"""Where an undeliverable result is written. Point a GitHub Actions `upload-artifact` step
at this directory (see `templates/check.yml`) so a submission that exhausts its retries is
still recoverable from the Actions run rather than silently lost."""


class WebhookError(RuntimeError):
    """Raised when a POST is rejected for a reason retrying cannot fix (4xx, bad secret)."""


@dataclass(frozen=True, slots=True)
class WebhookOutcome:
    """What happened when posting a result: delivered, or recovered to disk."""

    delivered: bool
    attempts: int
    status_code: int | None = None
    submission_id: int | None = None
    created: bool | None = None
    recovery_path: Path | None = None
    detail: str = ""


@dataclass(frozen=True, slots=True)
class WebhookClient:
    """Posts results to the platform, with retry and a guaranteed local fallback.

    `base_url` is the platform's autograder app root, e.g.
    `https://platform.example.edu/autograder/`. `secret` is the shared secret configured as
    `AUTOGRADER_SHARED_SECRET` on the platform; it must never be committed, only read from
    an environment variable at call time (see `README.md`, "Secret handling").
    """

    base_url: str
    secret: str
    max_attempts: int = 5
    backoff_seconds: float = 1.0
    backoff_multiplier: float = 2.0
    timeout_seconds: float = 15.0
    recovery_dir: Path = DEFAULT_RECOVERY_DIR

    def post(self, result: RunResult) -> WebhookOutcome:
        """Attempt delivery `max_attempts` times; on exhaustion, persist to disk and return.

        Never raises for a delivery failure: the caller (the CLI) must still exit non-zero
        for CI visibility, but the submission itself is never dropped without a trace.
        """
        payload = result.to_dict()
        url = self.base_url.rstrip("/") + "/" + RESULTS_PATH
        last_detail = "not attempted"
        for attempt in range(1, self.max_attempts + 1):
            try:
                response = httpx.post(
                    url,
                    json=payload,
                    headers={SECRET_HEADER: self.secret},
                    timeout=self.timeout_seconds,
                )
            except httpx.HTTPError as exc:
                last_detail = f"{type(exc).__name__}: {exc}"
                logger.warning(
                    "attempt %d/%d: network error: %s", attempt, self.max_attempts, last_detail
                )
            else:
                if response.status_code in (200, 201):
                    body = _safe_json(response)
                    return WebhookOutcome(
                        delivered=True,
                        attempts=attempt,
                        status_code=response.status_code,
                        submission_id=body.get("id") if isinstance(body, dict) else None,
                        created=body.get("created") if isinstance(body, dict) else None,
                        detail=f"delivered on attempt {attempt}",
                    )
                if 400 <= response.status_code < 500:
                    # A 4xx is not a delivery failure to retry: the payload or the secret is
                    # wrong, and retrying an identical request would fail identically.
                    raise WebhookError(
                        f"platform rejected the result ({response.status_code}): "
                        f"{response.text[:500]}"
                    )
                last_detail = f"HTTP {response.status_code}: {response.text[:500]}"
                logger.warning("attempt %d/%d: %s", attempt, self.max_attempts, last_detail)
            if attempt < self.max_attempts:
                time.sleep(self.backoff_seconds * (self.backoff_multiplier ** (attempt - 1)))
        recovery_path = self._write_recovery(result)
        return WebhookOutcome(
            delivered=False,
            attempts=self.max_attempts,
            detail=f"exhausted {self.max_attempts} attempts; last error: {last_detail}",
            recovery_path=recovery_path,
        )

    def _write_recovery(self, result: RunResult) -> Path:
        """Write the undelivered result to `recovery_dir`, keyed by repo and commit.

        The filename is stable and collision-resistant: (repo, commit) is exactly the key
        the platform de-duplicates on, so re-running `submit` against this file later is
        safe even if it was already retried once.
        """
        self.recovery_dir.mkdir(parents=True, exist_ok=True)
        safe_repo = result.repo.replace("/", "_")
        path = self.recovery_dir / f"{safe_repo}_{result.commit}.json"
        path.write_text(result.to_json(), encoding="utf-8")
        logger.error(
            "could not deliver result for %s@%s after retries; wrote %s for manual resubmission",
            result.repo,
            result.commit,
            path,
        )
        return path


def load_result_json(path: Path) -> dict[str, Any]:
    """Read a previously written result JSON, e.g. for the `autograder submit-file` CLI verb."""
    return json.loads(path.read_text(encoding="utf-8"))


def _safe_json(response: httpx.Response) -> Any:
    try:
        return response.json()
    except ValueError:
        return None
