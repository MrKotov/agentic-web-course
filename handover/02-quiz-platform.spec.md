# Spec: quiz and research platform

The load-bearing build. Everything else can slip a week; this cannot, because the baseline
measurement for the study has to happen before the first lecture and there is no way to
collect it later.

## Goal

Run three-minute quizzes in a lecture hall, from phones, and produce a dataset clean enough
to publish from.

## Non-goals

- Not an LMS. No course content, no file storage, no forums.
- No final grade calculation in v1. CSV export, grades computed elsewhere.
- No dashboards in v1. They get built after three lectures have run, when it is clear what
  is actually worth showing.
- No student-visible scores in v1. Showing scores changes behaviour and contaminates the
  measurement.

## The measurement design

This is the part that must be right from the start.

Each lecture has two quizzes:

- **Pre-quiz**, at the start. Five questions. Two of them are repeats from the *previous*
  lecture's topic.
- **Post-quiz**, at the end. Five questions on today's topic, parallel forms of the
  pre-quiz items, not identical wording.

So each item on a topic is answered at three points: before teaching (baseline),
immediately after (acquisition), and roughly a week later as a repeat in the next pre-quiz
(retention). Retention is the interesting measurement and it costs no extra class time.

Implication for the data model: an item is not tied to a single quiz. An item belongs to a
topic and is *administered* in many quizzes, at different phases. Do not model quizzes as
owning their questions.

## Data model

```
Cohort            semester, name
Student           cohort, name, email, research_id (random, stable, no PII link in exports)
Topic             lecture number, title
Item              topic, stem, options (JSON), correct_option, parallel_form_group
Quiz              lecture number, phase (PRE | POST), opens_at, closes_at, join_code
QuizItem          quiz, item, position, measurement (BASELINE | ACQUISITION | RETENTION)
Response          quiz_item, student, chosen_option, is_correct, answered_at, latency_ms
Consent           student, given (bool), timestamp, withdrawn_at
AgentUsageMode    student, lecture, self_reported mode (DELEGATED | EXPLANATORY | MIXED | NONE)
```

`AgentUsageMode` is one self-report question per lecture. It is what lets the retention
curve be split by interaction style, which is the replication of the RCT finding and the
reason this is a study rather than a feedback form.

`latency_ms` is worth capturing: time-to-answer separates recall from reconstruction and
costs nothing to record.

## Functional requirements

**Instructor**
- Create a cohort, import a roster from CSV.
- Author items against a topic, mark parallel-form groups.
- Build a quiz by selecting items and tagging each with its measurement phase.
- Open a quiz, which generates a short join code.
- Watch a live aggregate view while it is open: count answered, distribution per option,
  nothing per-student.
- Close a quiz, export CSV.

**Student**
- Join by code, no account creation, identify by university email once and be remembered.
- Answer five questions on a phone in under three minutes.
- See a confirmation, not a score.

**Live aggregate view**
This is what makes the predict-then-reveal moments work in the hall. It projects, shows the
option distribution updating as answers arrive, and reveals the correct answer only when the
instructor clicks. HTMX polling at a one-second interval is sufficient; no websockets needed
for a room of 40.

## Consent and data protection

- Consent is captured once, at the first session, as an explicit opt-in, separate from
  course participation. Refusing must have no academic consequence and must not block
  taking the quizzes.
- Exports contain `research_id`, never names or emails.
- Withdrawal deletes responses on request.
- Hosting decides the data controller. Settle this before provisioning. University
  infrastructure is the clean answer; a personal VPS makes the instructor personally the
  controller, which complicates the ethics application.

## Acceptance criteria

1. An instructor can import a 40-student roster, author 5 items, open a quiz, and see a
   join code, in under 10 minutes without touching the database.
2. 40 concurrent phones can submit within a 3-minute window without errors.
3. The live view updates within 2 seconds of a submission and never shows individual
   answers.
4. A CSV export contains one row per response with topic, phase, measurement, correctness,
   latency, and `research_id`, and contains no name or email anywhere.
5. A student who has not consented still appears in the gradebook but not in the export.
6. Deleting a student's data removes their responses and leaves aggregates recomputable.

## Build order inside this component

1. Models, admin, roster import.
2. Student quiz-taking flow on mobile.
3. Join codes and open/close.
4. Live aggregate view.
5. CSV export and consent.

Stop there for semester one.
