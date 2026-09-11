"""Student quiz-taking flow, instructor live view and CSV export.

The student flow is deliberately one question per page: it is the only layout that works
on a phone in a lecture hall, and it gives an honest per-item `latency_ms`.
"""

from __future__ import annotations

from django.contrib.admin.views.decorators import staff_member_required
from django.http import HttpRequest, HttpResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone
from django.views.decorators.http import require_http_methods

from .models import (
    AgentUsageMode,
    Consent,
    Quiz,
    QuizItem,
    Response,
    Student,
    UsageMode,
)
from .services import aggregate_for_quiz, export_responses_csv

SESSION_STUDENT_KEY = "student_id"
SESSION_QUESTION_SHOWN_AT = "question_shown_at"


def _current_student(request: HttpRequest) -> Student | None:
    """Return the student this browser was identified as, if any."""
    student_id = request.session.get(SESSION_STUDENT_KEY)
    if not student_id:
        return None
    return Student.objects.filter(pk=student_id).select_related("consent").first()


def _find_open_quiz(code: str) -> Quiz | None:
    """Return the open quiz with this join code, or None."""
    quiz = Quiz.objects.filter(join_code__iexact=code.strip()).first()
    return quiz if quiz and quiz.is_open else None


@require_http_methods(["GET", "POST"])
def join(request: HttpRequest) -> HttpResponse:
    """Landing page: enter the join code shown on the projector."""
    error = None
    if request.method == "POST":
        code = request.POST.get("join_code", "")
        quiz = _find_open_quiz(code)
        if quiz is None:
            error = "Невалиден или затворен код."
        else:
            return redirect("quiz:identify", quiz_id=quiz.pk)
    return render(request, "quiz/join.html", {"error": error})


@require_http_methods(["GET", "POST"])
def identify(request: HttpRequest, quiz_id: int) -> HttpResponse:
    """Identify by university email once; the session remembers the student afterwards."""
    quiz = get_object_or_404(Quiz, pk=quiz_id)
    if not quiz.is_open:
        return render(request, "quiz/closed.html", {"quiz": quiz}, status=403)

    if _current_student(request) is not None:
        return redirect("quiz:consent", quiz_id=quiz.pk)

    error = None
    if request.method == "POST":
        email = request.POST.get("email", "").strip().lower()
        students = Student.objects.filter(email__iexact=email)
        if quiz.cohort_id:
            students = students.filter(cohort_id=quiz.cohort_id)
        student = students.first()
        if student is None:
            error = "Този имейл не е в списъка на групата. Провери изписването."
        else:
            request.session[SESSION_STUDENT_KEY] = student.pk
            return redirect("quiz:consent", quiz_id=quiz.pk)
    return render(request, "quiz/identify.html", {"quiz": quiz, "error": error})


@require_http_methods(["GET", "POST"])
def consent(request: HttpRequest, quiz_id: int) -> HttpResponse:
    """Ask for research consent once. Either answer leads straight into the quiz."""
    quiz = get_object_or_404(Quiz, pk=quiz_id)
    student = _current_student(request)
    if student is None:
        return redirect("quiz:identify", quiz_id=quiz.pk)

    if Consent.objects.filter(student=student).exists() and request.method == "GET":
        return redirect("quiz:question", quiz_id=quiz.pk, position=1)

    if request.method == "POST":
        given = request.POST.get("consent") == "yes"
        Consent.objects.update_or_create(
            student=student,
            defaults={"given": given, "timestamp": timezone.now(), "withdrawn_at": None},
        )
        return redirect("quiz:question", quiz_id=quiz.pk, position=1)
    return render(request, "quiz/consent.html", {"quiz": quiz})


@require_http_methods(["GET", "POST"])
def question(request: HttpRequest, quiz_id: int, position: int) -> HttpResponse:
    """Show one question and record the answer with its latency."""
    quiz = get_object_or_404(Quiz, pk=quiz_id)
    student = _current_student(request)
    if student is None:
        return redirect("quiz:identify", quiz_id=quiz.pk)
    if not quiz.is_open:
        return render(request, "quiz/closed.html", {"quiz": quiz}, status=403)

    quiz_items = list(quiz.quiz_items.select_related("item").order_by("position", "pk"))
    if position < 1 or position > len(quiz_items):
        return redirect("quiz:usage_mode", quiz_id=quiz.pk)
    quiz_item = quiz_items[position - 1]

    if request.method == "POST":
        chosen_raw = request.POST.get("chosen_option", "")
        if not chosen_raw.isdigit():
            return render(
                request,
                "quiz/question.html",
                {
                    "quiz": quiz,
                    "quiz_item": quiz_item,
                    "position": position,
                    "total": len(quiz_items),
                    "options": list(enumerate(quiz_item.item.options)),
                    "error": "Избери отговор.",
                },
            )
        chosen = int(chosen_raw)
        shown_at = request.session.get(SESSION_QUESTION_SHOWN_AT, {}).get(str(quiz_item.pk))
        latency_ms = _latency_ms(shown_at)
        Response.objects.update_or_create(
            quiz_item=quiz_item,
            student=student,
            defaults={
                "chosen_option": chosen,
                "is_correct": quiz_item.item.is_correct_choice(chosen),
                "answered_at": timezone.now(),
                "latency_ms": latency_ms,
            },
        )
        return redirect("quiz:question", quiz_id=quiz.pk, position=position + 1)

    shown = request.session.get(SESSION_QUESTION_SHOWN_AT, {})
    shown[str(quiz_item.pk)] = timezone.now().timestamp()
    request.session[SESSION_QUESTION_SHOWN_AT] = shown
    return render(
        request,
        "quiz/question.html",
        {
            "quiz": quiz,
            "quiz_item": quiz_item,
            "position": position,
            "total": len(quiz_items),
            "options": list(enumerate(quiz_item.item.options)),
            "error": None,
        },
    )


def _latency_ms(shown_at: float | None) -> int:
    """Milliseconds between rendering the question and receiving the answer."""
    if not shown_at:
        return 0
    delta = (timezone.now().timestamp() - float(shown_at)) * 1000
    return max(0, min(int(delta), 60 * 60 * 1000))


@require_http_methods(["GET", "POST"])
def usage_mode(request: HttpRequest, quiz_id: int) -> HttpResponse:
    """The one self-report question per lecture: how the agent was used."""
    quiz = get_object_or_404(Quiz, pk=quiz_id)
    student = _current_student(request)
    if student is None:
        return redirect("quiz:identify", quiz_id=quiz.pk)

    already = AgentUsageMode.objects.filter(
        student=student, lecture=quiz.lecture_number
    ).exists()
    if already and request.method == "GET":
        return redirect("quiz:done", quiz_id=quiz.pk)

    if request.method == "POST":
        mode = request.POST.get("mode", "")
        if mode in UsageMode.values:
            AgentUsageMode.objects.update_or_create(
                student=student,
                lecture=quiz.lecture_number,
                defaults={"self_reported_mode": mode, "reported_at": timezone.now()},
            )
        return redirect("quiz:done", quiz_id=quiz.pk)
    return render(
        request,
        "quiz/usage_mode.html",
        {"quiz": quiz, "modes": UsageMode.choices},
    )


def done(request: HttpRequest, quiz_id: int) -> HttpResponse:
    """Confirmation only. No score is ever shown to a student in v1."""
    quiz = get_object_or_404(Quiz, pk=quiz_id)
    return render(request, "quiz/done.html", {"quiz": quiz})


@staff_member_required
def live(request: HttpRequest, quiz_id: int) -> HttpResponse:
    """Projector view: option distribution, polled by HTMX once a second."""
    quiz = get_object_or_404(Quiz, pk=quiz_id)
    return render(request, "instructor/live.html", {"quiz": quiz})


@staff_member_required
def live_fragment(request: HttpRequest, quiz_id: int) -> HttpResponse:
    """The polled fragment. Aggregates only — no student is identifiable here."""
    quiz = get_object_or_404(Quiz, pk=quiz_id)
    return render(
        request,
        "instructor/_live_aggregate.html",
        {
            "quiz": quiz,
            "rows": aggregate_for_quiz(quiz),
            "reveal": quiz.reveal_answers,
        },
    )


@staff_member_required
@require_http_methods(["POST"])
def toggle_reveal(request: HttpRequest, quiz_id: int) -> HttpResponse:
    """Reveal or hide the keyed answer on the projection."""
    quiz = get_object_or_404(Quiz, pk=quiz_id)
    quiz.reveal_answers = not quiz.reveal_answers
    quiz.save(update_fields=["reveal_answers"])
    return live_fragment(request, quiz_id)


@staff_member_required
@require_http_methods(["POST"])
def toggle_open(request: HttpRequest, quiz_id: int) -> HttpResponse:
    """Open the quiz (generating a join code) or close it."""
    quiz = get_object_or_404(Quiz, pk=quiz_id)
    if quiz.is_open:
        quiz.close()
    else:
        quiz.open()
    return redirect("quiz:live", quiz_id=quiz.pk)


@staff_member_required
def export(request: HttpRequest, quiz_id: int) -> HttpResponse:
    """Download the research export for one quiz."""
    quiz = get_object_or_404(Quiz, pk=quiz_id)
    payload = export_responses_csv(quiz)
    response = HttpResponse(payload, content_type="text/csv")
    response["Content-Disposition"] = f'attachment; filename="quiz-{quiz.pk}-responses.csv"'
    return response


@staff_member_required
def export_all(request: HttpRequest) -> HttpResponse:
    """Download the research export for every quiz."""
    response = HttpResponse(export_responses_csv(), content_type="text/csv")
    response["Content-Disposition"] = 'attachment; filename="responses.csv"'
    return response
