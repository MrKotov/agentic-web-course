"""End-to-end proof (acceptance criteria 1 and 2) that exercise 1's checks work: a correct
server passes every check, a deliberately broken one fails with an actionable message."""

from __future__ import annotations

from autograder.checks.ex01_mcp import CHECK_NAMES, probe_mcp_server


def test_correct_server_passes_every_check(good_mcp_context):
    results = probe_mcp_server(good_mcp_context)
    names = {r.name for r in results}
    assert names == set(CHECK_NAMES)
    failed = [r for r in results if not r.passed]
    assert not failed, f"expected all checks to pass, but {failed} failed"


def test_broken_server_fails_with_actionable_detail(broken_mcp_context):
    results = probe_mcp_server(broken_mcp_context)
    by_name = {r.name: r for r in results}

    assert by_name["tools_list_schema_valid"].passed is False
    assert "description" in by_name["tools_list_schema_valid"].detail

    assert by_name["tool_invocation_matches_spec"].passed is False
    assert by_name["tool_invocation_matches_spec"].detail

    assert by_name["unknown_tool_handled"].passed is False
    assert by_name["server_survives_unknown_tool"].passed is False
    # Every failing check must carry a detail a student can act on.
    for result in results:
        if not result.passed:
            assert result.detail, f"{result.name} failed with no actionable detail"


def test_missing_manifest_fails_loudly(tmp_path):
    from autograder.context import SubmissionContext

    context = SubmissionContext(repo_path=tmp_path, repo="course/empty", commit="deadbeef")
    results = probe_mcp_server(context)
    by_name = {r.name: r for r in results}
    assert by_name["server_manifest_present"].passed is False
    assert ".autograder/mcp-server.json" in by_name["server_manifest_present"].detail
    # Every declared check name still appears, even though the run aborted early.
    assert set(by_name) == set(CHECK_NAMES)
