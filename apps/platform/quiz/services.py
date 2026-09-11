"""Business logic that is shared between views, admin actions and management commands."""

from __future__ import annotations

import csv
import io
from dataclasses import dataclass
from typing import IO, Iterable

from django.db import transaction

from .models import Cohort, Quiz, Response, Student

EXPORT_COLUMNS = [
    "research_id",
    "cohort_semester",
    "lecture_number",
    "topic_title",
    "phase",
    "measurement",
    "item_id",
    "parallel_form_group",
    "chosen_option",
    "is_correct",
    "latency_ms",
    "answered_at",
    "agent_usage_mode",
]

GRADEBOOK_COLUMNS = [
    "name",
    "email",
    "research_id",
    "consented",
    "answered_count",
    "correct_count",
]


@dataclass
class RosterImportResult:
    """Outcome of a roster CSV import."""

    created: int
    updated: int
    errors: list[str]

    @property
    def total(self) -> int:
        return self.created + self.updated


@transaction.atomic
def import_roster(cohort: Cohort, csv_file: IO[str]) -> RosterImportResult:
    """Import students from a CSV with `name` and `email` columns.

    Re-importing the same file updates names in place rather than duplicating students,
    so a corrected roster can simply be uploaded again.
    """
    reader = csv.DictReader(csv_file)
    fieldnames = [(f or "").strip().lower() for f in (reader.fieldnames or [])]
    if "email" not in fieldnames:
        return RosterImportResult(0, 0, ["CSV файлът трябва да има колона 'email'."])

    created = 0
    updated = 0
    errors: list[str] = []
    for line_number, row in enumerate(reader, start=2):
        normalised = {(k or "").strip().lower(): (v or "").strip() for k, v in row.items()}
        email = normalised.get("email", "")
        name = normalised.get("name", "")
        if not email:
            errors.append(f"Ред {line_number}: липсва email.")
            continue
        student, was_created = Student.objects.get_or_create(
            cohort=cohort,
            email=email.lower(),
            defaults={"name": name or email},
        )
        if was_created:
            created += 1
        else:
            if name and student.name != name:
                student.name = name
                student.save(update_fields=["name"])
            updated += 1
    return RosterImportResult(created, updated, errors)


def _usage_mode_lookup(student_ids: Iterable[int]) -> dict[tuple[int, int], str]:
    """Map (student_id, lecture) to the self-reported agent usage mode."""
    from .models import AgentUsageMode

    return {
        (m.student_id, m.lecture): m.self_reported_mode
        for m in AgentUsageMode.objects.filter(student_id__in=list(student_ids))
    }


def export_responses_csv(quiz: Quiz | None = None) -> str:
    """Return the research export as CSV text.

    Contains `research_id` only: no name and no email appear anywhere in the output.
    Students who have not given active consent are excluded entirely.
    """
    responses = (
        Response.objects.select_related(
            "student",
            "student__cohort",
            "student__consent",
            "quiz_item",
            "quiz_item__quiz",
            "quiz_item__item",
            "quiz_item__item__topic",
        )
        .filter(student__consent__given=True, student__consent__withdrawn_at__isnull=True)
        .order_by("answered_at")
    )
    if quiz is not None:
        responses = responses.filter(quiz_item__quiz=quiz)

    responses = list(responses)
    modes = _usage_mode_lookup({r.student_id for r in responses})

    buffer = io.StringIO()
    writer = csv.writer(buffer)
    writer.writerow(EXPORT_COLUMNS)
    for response in responses:
        quiz_item = response.quiz_item
        item = quiz_item.item
        writer.writerow(
            [
                response.student.research_id,
                response.student.cohort.semester,
                quiz_item.quiz.lecture_number,
                item.topic.title,
                quiz_item.quiz.phase,
                quiz_item.measurement,
                item.pk,
                item.parallel_form_group,
                response.chosen_option,
                "1" if response.is_correct else "0",
                response.latency_ms,
                response.answered_at.isoformat(),
                modes.get((response.student_id, quiz_item.quiz.lecture_number), ""),
            ]
        )
    return buffer.getvalue()


def export_gradebook_csv(cohort: Cohort) -> str:
    """Return the instructor-facing gradebook.

    Unlike the research export this is identifiable and includes every student in the
    cohort, consented or not, because participation is a course matter and consent is not.
    """
    buffer = io.StringIO()
    writer = csv.writer(buffer)
    writer.writerow(GRADEBOOK_COLUMNS)
    for student in cohort.students.select_related("consent").prefetch_related("responses"):
        responses = list(student.responses.all())
        writer.writerow(
            [
                student.name,
                student.email,
                student.research_id,
                "1" if student.has_consented else "0",
                len(responses),
                sum(1 for r in responses if r.is_correct),
            ]
        )
    return buffer.getvalue()


def aggregate_for_quiz(quiz: Quiz) -> list[dict[str, object]]:
    """Per-item option counts for the live view. Never returns per-student data."""
    rows: list[dict[str, object]] = []
    quiz_items = quiz.quiz_items.select_related("item", "item__topic").order_by("position")
    for quiz_item in quiz_items:
        options = list(quiz_item.item.options)
        counts = [0] * len(options)
        total = 0
        for response in quiz_item.responses.all():
            total += 1
            if 0 <= response.chosen_option < len(counts):
                counts[response.chosen_option] += 1
        rows.append(
            {
                "quiz_item": quiz_item,
                "stem": quiz_item.item.stem,
                "measurement": quiz_item.get_measurement_display(),
                "answered": total,
                "correct_option": quiz_item.item.correct_option,
                "options": [
                    {
                        "index": index,
                        "text": text,
                        "count": counts[index],
                        "percent": round(100 * counts[index] / total) if total else 0,
                        "is_correct": index == quiz_item.item.correct_option,
                    }
                    for index, text in enumerate(options)
                ],
            }
        )
    return rows
