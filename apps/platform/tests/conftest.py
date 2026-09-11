"""Shared fixtures."""

from __future__ import annotations

import pytest
from django.contrib.auth.models import User
from django.utils import timezone

from quiz.models import Cohort, Consent, Item, Measurement, Phase, Quiz, QuizItem, Student


@pytest.fixture
def cohort(db: None) -> Cohort:
    return Cohort.objects.create(semester="2026/2027-1", name="КСТ 4 курс")


@pytest.fixture
def topic(db: None):
    from quiz.models import Topic

    return Topic.objects.create(lecture_number=1, title="Как работи агентният цикъл")


@pytest.fixture
def items(topic) -> list[Item]:
    return [
        Item.objects.create(
            topic=topic,
            stem=f"Въпрос {index}",
            options=["А", "Б", "В", "Г"],
            correct_option=index % 4,
            parallel_form_group=f"g{index}",
        )
        for index in range(5)
    ]


@pytest.fixture
def quiz(cohort, items) -> Quiz:
    quiz = Quiz.objects.create(lecture_number=1, phase=Phase.PRE, cohort=cohort)
    for position, item in enumerate(items, start=1):
        QuizItem.objects.create(
            quiz=quiz, item=item, position=position, measurement=Measurement.BASELINE
        )
    quiz.open()
    return quiz


@pytest.fixture
def student(cohort) -> Student:
    return Student.objects.create(
        cohort=cohort, name="Иван Петров", email="ivan.petrov@students.tu-sofia.bg"
    )


@pytest.fixture
def consented_student(student) -> Student:
    Consent.objects.create(student=student, given=True, timestamp=timezone.now())
    return student


@pytest.fixture
def instructor(db: None) -> User:
    return User.objects.create_superuser("instructor", "i@example.org", "pw-for-tests-only")
