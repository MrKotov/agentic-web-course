from __future__ import annotations

from autograder.checks import ex02_spec_driven as ex02
from autograder.context import SubmissionContext


def _make_repo(tmp_path):
    (tmp_path / "runs").mkdir()
    (tmp_path / "DESIGN.md").write_text(
        "# Design\n\n## Goal\n" + ("word " * 200) + "\n\n## Constraint\nfree tier only.\n"
    )
    (tmp_path / "runs" / "with-doc.md").write_text("with doc output")
    (tmp_path / "runs" / "without-doc.md").write_text("without doc output")
    (tmp_path / "Makefile").write_text("build:\n\ttrue\n")
    return SubmissionContext(repo_path=tmp_path, repo="course/ex2", commit="c1")


def test_complete_submission_passes_all_ex02_checks(tmp_path):
    context = _make_repo(tmp_path)
    for check in ex02.register_all():
        result = check(context)
        assert result.passed, f"{result.name} failed: {result.detail}"


def test_missing_design_doc_fails(tmp_path):
    context = _make_repo(tmp_path)
    (tmp_path / "DESIGN.md").unlink()
    result = ex02._design_doc_check(context)
    assert result.passed is False
    assert "DESIGN.md" in result.detail
