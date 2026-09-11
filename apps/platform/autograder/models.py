"""Storage for autograder results posted by exercise-template GitHub Actions workflows."""

from __future__ import annotations

from django.db import models
from django.utils import timezone

from quiz.models import Student


class Submission(models.Model):
    """One conformance run for one commit of one student repository.

    Idempotent on (repo, commit): a retried webhook post updates the existing row instead
    of creating a duplicate, so a failed post can be retried without losing or doubling a
    submission.
    """

    exercise = models.CharField(max_length=64)
    repo = models.CharField(max_length=200)
    commit = models.CharField(max_length=64)
    checks = models.JSONField(default=list)
    completed_at = models.DateTimeField()
    received_at = models.DateTimeField(default=timezone.now)
    student = models.ForeignKey(
        Student, on_delete=models.SET_NULL, null=True, blank=True, related_name="submissions"
    )

    class Meta:
        unique_together = [("repo", "commit")]
        ordering = ["-completed_at"]

    def __str__(self) -> str:
        return f"{self.exercise} {self.repo}@{self.commit[:8]}"

    @property
    def passed(self) -> bool:
        """True when every reported check passed."""
        return bool(self.checks) and all(check.get("passed") for check in self.checks)

    @property
    def failed_check_names(self) -> list[str]:
        """Names of the checks that did not pass."""
        return [c.get("name", "") for c in self.checks if not c.get("passed")]
