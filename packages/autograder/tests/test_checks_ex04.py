from __future__ import annotations

import httpx

from autograder.checks import ex04_deployment as ex04
from autograder.context import SubmissionContext


def test_deployed_url_check_passes_on_200(tmp_path, monkeypatch):
    def fake_get(url, *, timeout, follow_redirects):
        return httpx.Response(200, request=httpx.Request("GET", url))

    monkeypatch.setattr(httpx, "get", fake_get)
    context = SubmissionContext(
        repo_path=tmp_path, repo="course/ex4", commit="c1", deployed_url="https://example.edu"
    )
    result = ex04.deployed_url_returns_200(context)
    assert result.passed is True


def test_deployed_url_check_fails_without_url(tmp_path):
    context = SubmissionContext(repo_path=tmp_path, repo="course/ex4", commit="c1")
    result = ex04.deployed_url_returns_200(context)
    assert result.passed is False
    assert "DEPLOYED_URL" in result.detail


def test_gap_report_check_requires_substance(tmp_path):
    context = SubmissionContext(repo_path=tmp_path, repo="course/ex4", commit="c1")
    result = ex04.production_gap_report_present(context)
    assert result.passed is False

    (tmp_path / "PRODUCTION_GAPS.md").write_text("gap " * 150)
    result = ex04.production_gap_report_present(context)
    assert result.passed is True
