from __future__ import annotations

from autograder.exercises import (
    EXERCISE_01,
    EXERCISE_02,
    EXERCISE_03,
    EXERCISE_04,
    EXERCISE_05,
    register_all,
)
from autograder.registry import UnknownExercise, checks_for, known_exercises
from autograder.runner import run_exercise


def test_all_five_exercises_register():
    register_all()
    assert set(known_exercises()) == {
        EXERCISE_01,
        EXERCISE_02,
        EXERCISE_03,
        EXERCISE_04,
        EXERCISE_05,
    }
    for exercise in known_exercises():
        assert checks_for(exercise), f"{exercise} has no checks registered"


def test_running_ex01_against_good_fixture_end_to_end(good_mcp_context):
    register_all()
    result = run_exercise(EXERCISE_01, good_mcp_context)
    assert result.exercise == EXERCISE_01
    assert result.repo == good_mcp_context.repo
    assert result.commit == good_mcp_context.commit
    assert result.passed is True
    body = result.to_dict()
    assert body["completed_at"].endswith("Z")
    assert all("passed" in c for c in body["checks"])


def test_unknown_exercise_raises():
    register_all()
    try:
        checks_for("99-does-not-exist")
    except UnknownExercise as exc:
        assert "99-does-not-exist" in str(exc)
    else:
        raise AssertionError("expected UnknownExercise")
