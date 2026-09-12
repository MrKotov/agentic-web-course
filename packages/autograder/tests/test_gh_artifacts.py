from __future__ import annotations

import io
import zipfile

import httpx

from autograder.gh_artifacts import GitHubClient


def _zip_with_result(payload: bytes) -> bytes:
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w") as archive:
        archive.writestr("result.json", payload)
    return buf.getvalue()


def test_download_result_json_round_trip(monkeypatch):
    result_bytes = (
        b'{"exercise": "01-mcp-server", "repo": "s/r", "commit": "abc", "checks": [], '
        b'"completed_at": "2026-01-01T00:00:00Z"}'
    )
    zip_bytes = _zip_with_result(result_bytes)

    def fake_get(url, *, headers, timeout, follow_redirects=False, params=None):
        assert headers["Authorization"] == "Bearer tok"
        return httpx.Response(200, content=zip_bytes, request=httpx.Request("GET", url))

    monkeypatch.setattr(httpx, "get", fake_get)
    client = GitHubClient(token="tok")
    payload = client.download_result_json("s/r", artifact_id=42)
    assert payload["repo"] == "s/r"
    assert payload["exercise"] == "01-mcp-server"


def test_latest_run_id_returns_none_when_no_runs(monkeypatch):
    def fake_get(url, *, headers, timeout, params=None, follow_redirects=False):
        return httpx.Response(200, json={"workflow_runs": []}, request=httpx.Request("GET", url))

    monkeypatch.setattr(httpx, "get", fake_get)
    client = GitHubClient(token="tok")
    assert client.latest_run_id("s/r") is None
