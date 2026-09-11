"""Data model for the quiz and research platform.

The measurement design requires that an item belongs to a *topic*, not to a quiz.
The same item is administered in several quizzes at different measurement phases:
BASELINE before teaching, ACQUISITION straight after, RETENTION about a week later
as a repeat inside the next lecture's pre-quiz. Quizzes therefore do not own items;
`QuizItem` records one administration of one item.
"""

from __future__ import annotations

import secrets
import string

from django.db import models
from django.utils import timezone

JOIN_CODE_ALPHABET = "ABCDEFGHJKLMNPQRSTUVWXYZ23456789"  # no look-alike characters
JOIN_CODE_LENGTH = 6


def generate_join_code() -> str:
    """Return a short, unambiguous code students can type from the back of the hall."""
    return "".join(secrets.choice(JOIN_CODE_ALPHABET) for _ in range(JOIN_CODE_LENGTH))


def generate_research_id() -> str:
    """Return a random, stable pseudonym with no link to the student's identity."""
    alphabet = string.ascii_uppercase + string.digits
    return "R-" + "".join(secrets.choice(alphabet) for _ in range(10))


class Phase(models.TextChoices):
    """When in the lecture the quiz runs."""

    PRE = "PRE", "Преди лекцията"
    POST = "POST", "След лекцията"


class Measurement(models.TextChoices):
    """What one administration of an item measures."""

    BASELINE = "BASELINE", "Базова линия"
    ACQUISITION = "ACQUISITION", "Усвояване"
    RETENTION = "RETENTION", "Задържане"


class UsageMode(models.TextChoices):
    """Self-reported interaction style with the coding agent."""

    DELEGATED = "DELEGATED", "Делегиране"
    EXPLANATORY = "EXPLANATORY", "Обяснително"
    MIXED = "MIXED", "Смесено"
    NONE = "NONE", "Без агент"


class Cohort(models.Model):
    """One group of students in one semester."""

    semester = models.CharField(max_length=32)
    name = models.CharField(max_length=120)
    created_at = models.DateTimeField(default=timezone.now)

    class Meta:
        unique_together = [("semester", "name")]
        ordering = ["-semester", "name"]

    def __str__(self) -> str:
        return f"{self.name} ({self.semester})"


class Student(models.Model):
    """A member of a cohort. `research_id` is the only identifier that leaves the system."""

    cohort = models.ForeignKey(Cohort, on_delete=models.CASCADE, related_name="students")
    name = models.CharField(max_length=200)
    email = models.EmailField()
    research_id = models.CharField(max_length=32, unique=True, default=generate_research_id)
    created_at = models.DateTimeField(default=timezone.now)

    class Meta:
        unique_together = [("cohort", "email")]
        ordering = ["name"]

    def __str__(self) -> str:
        return f"{self.name} <{self.email}>"

    @property
    def has_consented(self) -> bool:
        """True when an active, non-withdrawn consent record exists."""
        consent = getattr(self, "consent", None)
        return bool(consent and consent.is_active)


class Topic(models.Model):
    """One lecture's subject. Items hang off topics, never off quizzes."""

    lecture_number = models.PositiveIntegerField()
    title = models.CharField(max_length=200)

    class Meta:
        ordering = ["lecture_number"]

    def __str__(self) -> str:
        return f"{self.lecture_number}. {self.title}"


class Item(models.Model):
    """A single multiple-choice question belonging to a topic.

    `options` is a JSON list of strings. `correct_option` is the zero-based index into it.
    Items sharing a `parallel_form_group` test the same thing with different wording, which
    is what lets the post-quiz avoid reusing the pre-quiz sentence verbatim.
    """

    topic = models.ForeignKey(Topic, on_delete=models.CASCADE, related_name="items")
    stem = models.TextField()
    options = models.JSONField(default=list)
    correct_option = models.PositiveSmallIntegerField()
    parallel_form_group = models.CharField(max_length=64, blank=True, default="")

    class Meta:
        ordering = ["topic", "id"]

    def __str__(self) -> str:
        return self.stem[:60]

    def is_correct_choice(self, chosen_option: int) -> bool:
        """Return whether the given zero-based option index is the keyed answer."""
        return chosen_option == self.correct_option


class Quiz(models.Model):
    """One administration event: a set of item administrations, opened by a join code."""

    lecture_number = models.PositiveIntegerField()
    phase = models.CharField(max_length=8, choices=Phase.choices)
    title = models.CharField(max_length=200, blank=True, default="")
    cohort = models.ForeignKey(
        Cohort, on_delete=models.CASCADE, related_name="quizzes", null=True, blank=True
    )
    opens_at = models.DateTimeField(null=True, blank=True)
    closes_at = models.DateTimeField(null=True, blank=True)
    join_code = models.CharField(max_length=16, unique=True, null=True, blank=True)
    reveal_answers = models.BooleanField(default=False)

    class Meta:
        ordering = ["lecture_number", "phase"]
        verbose_name_plural = "quizzes"

    def __str__(self) -> str:
        return f"L{self.lecture_number} {self.get_phase_display()}"

    @property
    def is_open(self) -> bool:
        """True when a join code exists and now falls inside the open window."""
        if not self.join_code:
            return False
        now = timezone.now()
        if self.opens_at and now < self.opens_at:
            return False
        if self.closes_at and now > self.closes_at:
            return False
        return True

    def open(self, closes_at: models.DateTimeField | None = None) -> str:
        """Generate a fresh join code and open the quiz. Returns the code."""
        code = generate_join_code()
        while Quiz.objects.filter(join_code=code).exclude(pk=self.pk).exists():
            code = generate_join_code()
        self.join_code = code
        self.opens_at = timezone.now()
        self.closes_at = closes_at
        self.save(update_fields=["join_code", "opens_at", "closes_at"])
        return code

    def close(self) -> None:
        """Close the quiz now. The join code stops working immediately."""
        self.closes_at = timezone.now()
        self.save(update_fields=["closes_at"])


class QuizItem(models.Model):
    """One administration of one item inside one quiz, tagged with what it measures."""

    quiz = models.ForeignKey(Quiz, on_delete=models.CASCADE, related_name="quiz_items")
    item = models.ForeignKey(Item, on_delete=models.CASCADE, related_name="administrations")
    position = models.PositiveSmallIntegerField(default=1)
    measurement = models.CharField(max_length=16, choices=Measurement.choices)

    class Meta:
        unique_together = [("quiz", "item")]
        ordering = ["quiz", "position"]

    def __str__(self) -> str:
        return f"{self.quiz} #{self.position}"


class Response(models.Model):
    """One student's answer to one item administration."""

    quiz_item = models.ForeignKey(QuizItem, on_delete=models.CASCADE, related_name="responses")
    student = models.ForeignKey(Student, on_delete=models.CASCADE, related_name="responses")
    chosen_option = models.PositiveSmallIntegerField()
    is_correct = models.BooleanField()
    answered_at = models.DateTimeField(default=timezone.now)
    latency_ms = models.PositiveIntegerField()

    class Meta:
        unique_together = [("quiz_item", "student")]
        ordering = ["answered_at"]

    def __str__(self) -> str:
        return f"{self.student.research_id} -> {self.quiz_item}"


class Consent(models.Model):
    """Explicit research opt-in, separate from course participation.

    Refusal has no academic consequence and never blocks quiz taking; it only keeps the
    student out of the research export.
    """

    student = models.OneToOneField(Student, on_delete=models.CASCADE, related_name="consent")
    given = models.BooleanField(default=False)
    timestamp = models.DateTimeField(default=timezone.now)
    withdrawn_at = models.DateTimeField(null=True, blank=True)

    def __str__(self) -> str:
        return f"{self.student.research_id}: {'given' if self.is_active else 'not given'}"

    @property
    def is_active(self) -> bool:
        """True when consent was given and has not since been withdrawn."""
        return self.given and self.withdrawn_at is None

    def withdraw(self, delete_responses: bool = True) -> None:
        """Withdraw consent and, by default, delete the student's responses."""
        self.withdrawn_at = timezone.now()
        self.given = False
        self.save(update_fields=["withdrawn_at", "given"])
        if delete_responses:
            self.student.responses.all().delete()


class AgentUsageMode(models.Model):
    """One self-report per student per lecture: how they worked with the agent."""

    student = models.ForeignKey(Student, on_delete=models.CASCADE, related_name="usage_modes")
    lecture = models.PositiveIntegerField()
    self_reported_mode = models.CharField(max_length=16, choices=UsageMode.choices)
    reported_at = models.DateTimeField(default=timezone.now)

    class Meta:
        unique_together = [("student", "lecture")]
        ordering = ["lecture"]

    def __str__(self) -> str:
        return f"{self.student.research_id} L{self.lecture}: {self.self_reported_mode}"
