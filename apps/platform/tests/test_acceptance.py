"""One test (at least) per acceptance criterion in handover/02-quiz-platform.spec.md."""

from __future__ import annotations

import csv
import io
from concurrent.futures import ThreadPoolExecutor

import pytest
from django.test import Client
from django.urls import reverse
from django.utils import timezone

from quiz.models import (
    Cohort,
    Consent,
    Item,
    Measurement,
    Phase,
    Quiz,
    QuizItem,
    Response,
    Student,
    Topic,
)
from quiz.services import export_gradebook_csv, export_responses_csv, import_roster


def _roster_csv(count: int) -> io.StringIO:
    lines = ["name,email"]
    lines += [f"Студент {n},student{n}@students.tu-sofia.bg" for n in range(count)]
    return io.StringIO("\n".join(lines) + "\n")


def _take_quiz(client: Client, quiz: Quiz, email: str, consent: str = "yes") -> None:
    """Walk one phone through the whole student flow."""
    client.post(reverse("quiz:join"), {"join_code": quiz.join_code})
    client.post(reverse("quiz:identify", args=[quiz.pk]), {"email": email})
    client.post(reverse("quiz:consent", args=[quiz.pk]), {"consent": consent})
    total = quiz.quiz_items.count()
    for position in range(1, total + 1):
        client.get(reverse("quiz:question", args=[quiz.pk, position]))
        client.post(
            reverse("quiz:question", args=[quiz.pk, position]), {"chosen_option": "1"}
        )
    client.post(reverse("quiz:usage_mode", args=[quiz.pk]), {"mode": "EXPLANATORY"})


# --- AC1: roster import, item authoring, open a quiz, get a join code -------------------


@pytest.mark.django_db
def test_ac1_instructor_can_set_up_a_quiz_without_touching_the_database(
    client: Client, instructor
) -> None:
    cohort = Cohort.objects.create(semester="2026/2027-1", name="КСТ")
    result = import_roster(cohort, _roster_csv(40))
    assert result.created == 40
    assert cohort.students.count() == 40

    topic = Topic.objects.create(lecture_number=1, title="Агентният цикъл")
    quiz = Quiz.objects.create(lecture_number=1, phase=Phase.PRE, cohort=cohort)
    for position in range(1, 6):
        item = Item.objects.create(
            topic=topic,
            stem=f"Въпрос {position}",
            options=["А", "Б", "В", "Г"],
            correct_option=0,
        )
        QuizItem.objects.create(
            quiz=quiz, item=item, position=position, measurement=Measurement.BASELINE
        )
    code = quiz.open()

    assert len(code) == 6
    assert quiz.is_open
    assert quiz.quiz_items.count() == 5

    client.force_login(instructor)
    live = client.get(reverse("quiz:live", args=[quiz.pk]))
    assert live.status_code == 200
    assert code in live.content.decode()


@pytest.mark.django_db
def test_ac1_reimporting_the_roster_updates_instead_of_duplicating(cohort) -> None:
    import_roster(cohort, _roster_csv(40))
    second = import_roster(cohort, _roster_csv(40))
    assert second.created == 0
    assert second.updated == 40
    assert cohort.students.count() == 40


# --- AC2: 40 concurrent phones submit inside the window ---------------------------------


@pytest.mark.django_db(transaction=True)
def test_ac2_forty_concurrent_phones_submit_without_errors(cohort, quiz) -> None:
    students = [
        Student.objects.create(
            cohort=cohort, name=f"Студент {n}", email=f"s{n}@students.tu-sofia.bg"
        )
        for n in range(40)
    ]

    def submit(student: Student) -> int:
        client = Client()
        _take_quiz(client, quiz, student.email)
        return student.pk

    with ThreadPoolExecutor(max_workers=10) as pool:
        done = list(pool.map(submit, students))

    assert len(done) == 40
    assert Response.objects.count() == 40 * quiz.quiz_items.count()
    assert Response.objects.filter(latency_ms__gt=0).exists()


@pytest.mark.django_db
def test_latency_is_captured_on_every_response(client: Client, quiz, student) -> None:
    _take_quiz(client, quiz, student.email)
    responses = Response.objects.filter(student=student)
    assert responses.count() == quiz.quiz_items.count()
    assert all(r.latency_ms is not None for r in responses)
    assert all(r.latency_ms >= 0 for r in responses)


@pytest.mark.django_db
def test_student_never_sees_a_score(client: Client, quiz, student) -> None:
    _take_quiz(client, quiz, student.email)
    body = client.get(reverse("quiz:done", args=[quiz.pk])).content.decode()
    assert "Отговорите са записани" in body
    for forbidden in ("верни", "точки", "резултат", "score"):
        assert forbidden not in body.lower()


# --- AC3: live view is aggregate-only and reflects a submission immediately -------------


@pytest.mark.django_db
def test_ac3_live_view_updates_and_shows_no_individual_answers(
    client: Client, instructor, quiz, student
) -> None:
    client.force_login(instructor)
    url = reverse("quiz:live_fragment", args=[quiz.pk])
    before = client.get(url).content.decode()
    assert "отговорили: 0" in before

    phone = Client()
    _take_quiz(phone, quiz, student.email)

    after = client.get(url).content.decode()
    assert "отговорили: 1" in after
    assert student.name not in after
    assert student.email not in after
    assert student.research_id not in after


@pytest.mark.django_db
def test_ac3_live_view_hides_the_key_until_revealed(
    client: Client, instructor, quiz, student
) -> None:
    client.force_login(instructor)
    phone = Client()
    _take_quiz(phone, quiz, student.email)

    hidden = client.get(reverse("quiz:live_fragment", args=[quiz.pk])).content.decode()
    assert "✓" not in hidden

    revealed = client.post(reverse("quiz:toggle_reveal", args=[quiz.pk])).content.decode()
    assert "✓" in revealed


@pytest.mark.django_db
def test_live_view_requires_staff(client: Client, quiz) -> None:
    assert client.get(reverse("quiz:live", args=[quiz.pk])).status_code in (302, 403)
    assert client.get(reverse("quiz:export", args=[quiz.pk])).status_code in (302, 403)


# --- AC4: the export carries research_id and no PII -------------------------------------


@pytest.mark.django_db
def test_ac4_export_has_required_columns_and_no_name_or_email(
    client: Client, quiz, consented_student
) -> None:
    phone = Client()
    _take_quiz(phone, quiz, consented_student.email)

    payload = export_responses_csv(quiz)
    rows = list(csv.DictReader(io.StringIO(payload)))

    assert len(rows) == quiz.quiz_items.count()
    for column in (
        "research_id",
        "topic_title",
        "phase",
        "measurement",
        "is_correct",
        "latency_ms",
    ):
        assert column in rows[0]
    assert all(row["research_id"] == consented_student.research_id for row in rows)

    # No name and no email anywhere in the file, header included.
    assert consented_student.name not in payload
    assert consented_student.email not in payload
    assert "@" not in payload
    for banned in ("name", "email"):
        assert banned not in payload.splitlines()[0].split(",")


# --- AC5: no consent means gradebook yes, export no -------------------------------------


@pytest.mark.django_db
def test_ac5_unconsented_student_is_in_the_gradebook_but_not_the_export(
    cohort, quiz
) -> None:
    refuser = Student.objects.create(
        cohort=cohort, name="Мария Иванова", email="maria@students.tu-sofia.bg"
    )
    agreer = Student.objects.create(
        cohort=cohort, name="Георги Колев", email="georgi@students.tu-sofia.bg"
    )
    _take_quiz(Client(), quiz, refuser.email, consent="no")
    _take_quiz(Client(), quiz, agreer.email, consent="yes")

    assert Response.objects.filter(student=refuser).count() == quiz.quiz_items.count()
    assert Consent.objects.get(student=refuser).given is False

    gradebook = export_gradebook_csv(cohort)
    assert refuser.research_id in gradebook
    assert refuser.name in gradebook

    export = export_responses_csv()
    assert refuser.research_id not in export
    assert agreer.research_id in export


@pytest.mark.django_db
def test_ac5_withdrawn_consent_drops_out_of_the_export(quiz, consented_student) -> None:
    _take_quiz(Client(), quiz, consented_student.email)
    assert consented_student.research_id in export_responses_csv()

    consent = Consent.objects.get(student=consented_student)
    consent.withdraw(delete_responses=False)

    assert consented_student.research_id not in export_responses_csv()


# --- AC6: deletion removes responses and leaves aggregates recomputable -----------------


@pytest.mark.django_db
def test_ac6_deleting_a_students_data_leaves_aggregates_recomputable(
    cohort, quiz, client: Client, instructor
) -> None:
    leaver = Student.objects.create(
        cohort=cohort, name="Петър Петров", email="petar@students.tu-sofia.bg"
    )
    stayer = Student.objects.create(
        cohort=cohort, name="Анна Стоева", email="anna@students.tu-sofia.bg"
    )
    Consent.objects.create(student=leaver, given=True, timestamp=timezone.now())
    Consent.objects.create(student=stayer, given=True, timestamp=timezone.now())
    _take_quiz(Client(), quiz, leaver.email)
    _take_quiz(Client(), quiz, stayer.email)

    from quiz.services import aggregate_for_quiz

    before = aggregate_for_quiz(quiz)
    assert before[0]["answered"] == 2

    Consent.objects.get(student=leaver).withdraw()

    assert Response.objects.filter(student=leaver).count() == 0
    after = aggregate_for_quiz(quiz)
    assert after[0]["answered"] == 1
    assert stayer.research_id in export_responses_csv()
    assert leaver.research_id not in export_responses_csv()


@pytest.mark.django_db
def test_ac6_deleting_the_student_row_cascades_to_responses(quiz, consented_student) -> None:
    _take_quiz(Client(), quiz, consented_student.email)
    assert Response.objects.count() == quiz.quiz_items.count()
    consented_student.delete()
    assert Response.objects.count() == 0
    assert quiz.quiz_items.count() == 5  # the instrument survives the person
