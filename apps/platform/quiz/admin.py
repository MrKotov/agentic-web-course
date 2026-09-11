"""Django admin — the instructor's whole authoring surface.

Everything in acceptance criterion 1 (import a roster, author items, open a quiz, read the
join code) happens here without touching the database.
"""

from __future__ import annotations

import io

from django import forms
from django.contrib import admin, messages
from django.http import HttpRequest, HttpResponse, HttpResponseRedirect
from django.shortcuts import render
from django.urls import URLPattern, path, reverse
from django.utils.html import format_html

from .models import (
    AgentUsageMode,
    Cohort,
    Consent,
    Item,
    Quiz,
    QuizItem,
    Response,
    Student,
    Topic,
)
from .services import export_gradebook_csv, import_roster


class RosterUploadForm(forms.Form):
    """Upload form for the roster CSV."""

    csv_file = forms.FileField(label="CSV файл (колони: name,email)")


@admin.register(Cohort)
class CohortAdmin(admin.ModelAdmin):
    list_display = ("name", "semester", "student_count", "roster_actions")
    search_fields = ("name", "semester")

    @admin.display(description="students")
    def student_count(self, obj: Cohort) -> int:
        return obj.students.count()

    @admin.display(description="actions")
    def roster_actions(self, obj: Cohort) -> str:
        return format_html(
            '<a href="{}">Импорт на списък</a> &middot; <a href="{}">Gradebook CSV</a>',
            reverse("admin:quiz_cohort_import_roster", args=[obj.pk]),
            reverse("admin:quiz_cohort_gradebook", args=[obj.pk]),
        )

    def get_urls(self) -> list[URLPattern]:
        return [
            path(
                "<int:cohort_id>/import-roster/",
                self.admin_site.admin_view(self.import_roster_view),
                name="quiz_cohort_import_roster",
            ),
            path(
                "<int:cohort_id>/gradebook.csv",
                self.admin_site.admin_view(self.gradebook_view),
                name="quiz_cohort_gradebook",
            ),
            *super().get_urls(),
        ]

    def import_roster_view(self, request: HttpRequest, cohort_id: int) -> HttpResponse:
        """Upload a roster CSV and create or update students in this cohort."""
        cohort = Cohort.objects.get(pk=cohort_id)
        if request.method == "POST":
            form = RosterUploadForm(request.POST, request.FILES)
            if form.is_valid():
                raw = form.cleaned_data["csv_file"].read().decode("utf-8-sig")
                result = import_roster(cohort, io.StringIO(raw))
                for error in result.errors:
                    self.message_user(request, error, level=messages.WARNING)
                self.message_user(
                    request,
                    f"Импортирани: {result.created} нови, {result.updated} обновени.",
                    level=messages.SUCCESS,
                )
                return HttpResponseRedirect(reverse("admin:quiz_cohort_changelist"))
        else:
            form = RosterUploadForm()
        return render(
            request,
            "admin/quiz/import_roster.html",
            {**self.admin_site.each_context(request), "cohort": cohort, "form": form},
        )

    def gradebook_view(self, request: HttpRequest, cohort_id: int) -> HttpResponse:
        """Download the identifiable gradebook for this cohort."""
        cohort = Cohort.objects.get(pk=cohort_id)
        response = HttpResponse(export_gradebook_csv(cohort), content_type="text/csv")
        response["Content-Disposition"] = f'attachment; filename="gradebook-{cohort.pk}.csv"'
        return response


@admin.register(Student)
class StudentAdmin(admin.ModelAdmin):
    list_display = ("name", "email", "research_id", "cohort", "consented")
    list_filter = ("cohort",)
    search_fields = ("name", "email", "research_id")
    readonly_fields = ("research_id",)
    actions = ["delete_research_data"]

    @admin.display(boolean=True, description="consent")
    def consented(self, obj: Student) -> bool:
        return obj.has_consented

    @admin.action(description="Изтрий изследователските данни (отговори и съгласие)")
    def delete_research_data(self, request: HttpRequest, queryset: object) -> None:
        """Withdrawal: delete responses, leaving aggregates recomputable from what remains."""
        deleted = 0
        for student in queryset:
            deleted += student.responses.count()
            student.responses.all().delete()
            consent = getattr(student, "consent", None)
            if consent is not None:
                consent.withdraw(delete_responses=False)
        self.message_user(request, f"Изтрити отговори: {deleted}.", level=messages.SUCCESS)


@admin.register(Topic)
class TopicAdmin(admin.ModelAdmin):
    list_display = ("lecture_number", "title", "item_count")
    search_fields = ("title",)

    @admin.display(description="items")
    def item_count(self, obj: Topic) -> int:
        return obj.items.count()


@admin.register(Item)
class ItemAdmin(admin.ModelAdmin):
    list_display = ("__str__", "topic", "correct_option", "parallel_form_group")
    list_filter = ("topic", "parallel_form_group")
    search_fields = ("stem",)


class QuizItemInline(admin.TabularInline):
    model = QuizItem
    extra = 5
    autocomplete_fields: list[str] = []


@admin.register(Quiz)
class QuizAdmin(admin.ModelAdmin):
    list_display = ("__str__", "cohort", "join_code", "is_open", "live_link", "export_link")
    list_filter = ("phase", "cohort")
    inlines = [QuizItemInline]
    actions = ["open_quizzes", "close_quizzes"]
    readonly_fields = ("join_code",)

    @admin.display(boolean=True, description="open")
    def is_open(self, obj: Quiz) -> bool:
        return obj.is_open

    @admin.display(description="live")
    def live_link(self, obj: Quiz) -> str:
        return format_html('<a href="{}">Проекция</a>', reverse("quiz:live", args=[obj.pk]))

    @admin.display(description="export")
    def export_link(self, obj: Quiz) -> str:
        return format_html('<a href="{}">CSV</a>', reverse("quiz:export", args=[obj.pk]))

    @admin.action(description="Отвори (генерира код за присъединяване)")
    def open_quizzes(self, request: HttpRequest, queryset: object) -> None:
        codes = [f"{quiz}: {quiz.open()}" for quiz in queryset]
        self.message_user(request, "Отворени — " + "; ".join(codes), level=messages.SUCCESS)

    @admin.action(description="Затвори")
    def close_quizzes(self, request: HttpRequest, queryset: object) -> None:
        for quiz in queryset:
            quiz.close()
        self.message_user(request, "Затворени.", level=messages.SUCCESS)


@admin.register(Response)
class ResponseAdmin(admin.ModelAdmin):
    list_display = ("research_id", "quiz_item", "chosen_option", "is_correct", "latency_ms")
    list_filter = ("is_correct", "quiz_item__quiz")

    @admin.display(description="research id")
    def research_id(self, obj: Response) -> str:
        return obj.student.research_id


@admin.register(Consent)
class ConsentAdmin(admin.ModelAdmin):
    list_display = ("student", "given", "timestamp", "withdrawn_at")
    list_filter = ("given",)


@admin.register(AgentUsageMode)
class AgentUsageModeAdmin(admin.ModelAdmin):
    list_display = ("student", "lecture", "self_reported_mode")
    list_filter = ("lecture", "self_reported_mode")


admin.site.site_header = "Платформа за тестове и изследване"
admin.site.site_title = "Платформа"
admin.site.index_title = "Управление"
