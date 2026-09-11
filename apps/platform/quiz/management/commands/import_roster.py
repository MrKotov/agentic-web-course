"""Management command: import a roster CSV into a cohort."""

from __future__ import annotations

from typing import Any

from django.core.management.base import BaseCommand, CommandError

from quiz.models import Cohort
from quiz.services import import_roster


class Command(BaseCommand):
    help = "Import students from a CSV with name,email columns into a cohort."

    def add_arguments(self, parser: Any) -> None:
        parser.add_argument("--semester", required=True)
        parser.add_argument("--cohort", required=True, help="Cohort name")
        parser.add_argument("--csv", required=True, help="Path to the roster CSV")

    def handle(self, *args: Any, **options: Any) -> None:
        cohort, _ = Cohort.objects.get_or_create(
            semester=options["semester"], name=options["cohort"]
        )
        try:
            with open(options["csv"], encoding="utf-8-sig", newline="") as handle:
                result = import_roster(cohort, handle)
        except OSError as exc:
            raise CommandError(str(exc)) from exc
        for error in result.errors:
            self.stderr.write(self.style.WARNING(error))
        self.stdout.write(
            self.style.SUCCESS(
                f"{cohort}: {result.created} created, {result.updated} updated."
            )
        )
