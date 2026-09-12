from __future__ import annotations

from pathlib import Path

import pytest

from autograder.context import SubmissionContext

FIXTURES = Path(__file__).parent / "fixtures"


@pytest.fixture
def good_mcp_context() -> SubmissionContext:
    return SubmissionContext(
        repo_path=FIXTURES / "mcp_good", repo="course/fixture-good", commit="good1234"
    )


@pytest.fixture
def broken_mcp_context() -> SubmissionContext:
    return SubmissionContext(
        repo_path=FIXTURES / "mcp_broken", repo="course/fixture-broken", commit="broken123"
    )
