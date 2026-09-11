"""Admin for autograder submissions — read-only roll-up for the instructor."""

from __future__ import annotations

from django.contrib import admin

from .models import Submission


@admin.register(Submission)
class SubmissionAdmin(admin.ModelAdmin):
    list_display = ("exercise", "repo", "short_commit", "passed", "completed_at", "student")
    list_filter = ("exercise",)
    search_fields = ("repo", "commit")
    readonly_fields = ("exercise", "repo", "commit", "checks", "completed_at", "received_at")

    @admin.display(description="commit")
    def short_commit(self, obj: Submission) -> str:
        return obj.commit[:8]

    @admin.display(boolean=True, description="passed")
    def passed(self, obj: Submission) -> bool:
        return obj.passed
