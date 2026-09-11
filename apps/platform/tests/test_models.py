"""Model-level guarantees the measurement design depends on."""

from __future__ import annotations

import pytest
from django.utils import timezone
from datetime import timedelta

from quiz.models import Measurement, Phase, Quiz, QuizItem


@pytest.mark.django_db
def test_item_is_administered_in_many_quizzes(items, cohort) -> None:
    """An item belongs to a topic and is administered in several quizzes."""
    item = items[0]
    pre = Quiz.objects.create(lecture_number=1, phase=Phase.PRE, cohort=cohort)
    post = Quiz.objects.create(lecture_number=1, phase=Phase.POST, cohort=cohort)
    next_pre = Quiz.objects.create(lecture_number=2, phase=Phase.PRE, cohort=cohort)
    QuizItem.objects.create(quiz=pre, item=item, position=1, measurement=Measurement.BASELINE)
    QuizItem.objects.create(
        quiz=post, item=item, position=1, measurement=Measurement.ACQUISITION
    )
    QuizItem.objects.create(
        quiz=next_pre, item=item, position=1, measurement=Measurement.RETENTION
    )

    assert item.administrations.count() == 3
    assert set(item.administrations.values_list("measurement", flat=True)) == {
        Measurement.BASELINE,
        Measurement.ACQUISITION,
        Measurement.RETENTION,
    }


@pytest.mark.django_db
def test_research_ids_are_unique_and_carry_no_pii(cohort) -> None:
    from quiz.models import Student

    a = Student.objects.create(cohort=cohort, name="А А", email="a@x.bg")
    b = Student.objects.create(cohort=cohort, name="Б Б", email="b@x.bg")
    assert a.research_id != b.research_id
    for student in (a, b):
        assert student.name not in student.research_id
        assert student.email not in student.research_id


@pytest.mark.django_db
def test_quiz_open_and_close(quiz) -> None:
    assert quiz.is_open
    assert len(quiz.join_code) == 6
    quiz.close()
    assert not quiz.is_open


@pytest.mark.django_db
def test_quiz_not_open_before_opens_at(cohort) -> None:
    quiz = Quiz.objects.create(lecture_number=3, phase=Phase.PRE, cohort=cohort)
    assert not quiz.is_open  # no join code yet
    quiz.open()
    quiz.opens_at = timezone.now() + timedelta(hours=1)
    quiz.save()
    assert not quiz.is_open
