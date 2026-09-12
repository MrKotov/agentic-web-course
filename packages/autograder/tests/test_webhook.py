"""Acceptance criterion 4: a failed webhook post retries and never silently loses a
submission."""

from __future__ import annotations

import json

import httpx
import pytest

from autograder.models import CheckResult, RunResult
from autograder.webhook import SECRET_HEADER, WebhookClient, WebhookError


def _result() -> RunResult:
    return RunResult(
        exercise="01-mcp-server",
        repo="student/agentic-ex1",
        commit="abc123",
        checks=[CheckResult("tools_list_responds", True)],
    )


def test_success_on_first_attempt(monkeypatch, tmp_path):
    calls = []

    def fake_post(url, *, json, headers, timeout):
        calls.append((url, json, headers))
        return httpx.Response(
            201, json={"id": 1, "created": True, "passed": True}, request=httpx.Request("POST", url)
        )

    monkeypatch.setattr(httpx, "post", fake_post)
    client = WebhookClient(
        base_url="https://platform.example/autograder", secret="s3cr3t", recovery_dir=tmp_path
    )
    outcome = client.post(_result())

    assert outcome.delivered is True
    assert outcome.attempts == 1
    assert outcome.submission_id == 1
    assert calls[0][2][SECRET_HEADER] == "s3cr3t"
    assert calls[0][0] == "https://platform.example/autograder/results/"
    assert not list(tmp_path.iterdir())  # nothing recovered: delivery succeeded


def test_retries_then_succeeds(monkeypatch, tmp_path):
    attempts = {"n": 0}

    def fake_post(url, *, json, headers, timeout):
        attempts["n"] += 1
        if attempts["n"] < 3:
            raise httpx.ConnectTimeout("timed out", request=httpx.Request("POST", url))
        return httpx.Response(
            200, json={"id": 2, "created": False}, request=httpx.Request("POST", url)
        )

    sleeps = []
    monkeypatch.setattr(httpx, "post", fake_post)
    monkeypatch.setattr("autograder.webhook.time.sleep", lambda s: sleeps.append(s))
    client = WebhookClient(
        base_url="https://platform.example/autograder", secret="s3cr3t", recovery_dir=tmp_path
    )

    outcome = client.post(_result())

    assert outcome.delivered is True
    assert outcome.attempts == 3
    assert len(sleeps) == 2
    assert sleeps == sorted(sleeps)  # exponential backoff: non-decreasing


def test_exhausted_retries_recovers_to_disk_never_loses_submission(monkeypatch, tmp_path):
    def always_fails(url, *, json, headers, timeout):
        raise httpx.ConnectError("connection refused", request=httpx.Request("POST", url))

    monkeypatch.setattr(httpx, "post", always_fails)
    monkeypatch.setattr("autograder.webhook.time.sleep", lambda s: None)
    client = WebhookClient(
        base_url="https://platform.example/autograder",
        secret="s3cr3t",
        max_attempts=3,
        recovery_dir=tmp_path,
    )
    result = _result()

    outcome = client.post(result)

    assert outcome.delivered is False
    assert outcome.attempts == 3
    assert outcome.recovery_path is not None
    assert outcome.recovery_path.exists()
    recovered = json.loads(outcome.recovery_path.read_text())
    assert recovered["repo"] == result.repo
    assert recovered["commit"] == result.commit
    # The exact same payload that would have been posted is fully recoverable.
    assert recovered == result.to_dict()


def test_4xx_raises_instead_of_retrying(monkeypatch, tmp_path):
    calls = {"n": 0}

    def fake_post(url, *, json, headers, timeout):
        calls["n"] += 1
        return httpx.Response(
            401, json={"error": "unauthorized"}, request=httpx.Request("POST", url)
        )

    monkeypatch.setattr(httpx, "post", fake_post)
    client = WebhookClient(
        base_url="https://platform.example/autograder", secret="wrong", recovery_dir=tmp_path
    )

    with pytest.raises(WebhookError):
        client.post(_result())
    assert calls["n"] == 1  # no retry on a 4xx: the secret is wrong, retrying won't help
