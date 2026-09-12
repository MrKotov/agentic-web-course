"""Exercise 2: spec-driven — same task, with and without a design doc.

Per handover/04-autograder.spec.md: "Design doc exists and is non-trivial. Build runs. Both
runs (with and without the doc) are present for the diff." Whether the doc actually
*helped* is a defense question; the harness only checks that the artifacts needed for that
conversation exist and that the repository still builds.

File names are an instructor convention (not fixed by the spec), documented in
`README.md` and in the exercise 2 brief in `apps/examples/03-context/`. Candidate lists give
students latitude in layout without weakening the check.
"""

from __future__ import annotations

from .common import Check, command_succeeds, file_non_trivial, file_present

DESIGN_DOC_CANDIDATES = ("DESIGN.md", "docs/DESIGN.md", "design/DESIGN.md")

WITHOUT_DOC_RUN_CANDIDATES = (
    "runs/without-doc.md",
    "runs/without-doc/README.md",
    "runs/without-doc/output.md",
)
WITH_DOC_RUN_CANDIDATES = (
    "runs/with-doc.md",
    "runs/with-doc/README.md",
    "runs/with-doc/output.md",
)

DESIGN_DOC_MIN_WORDS = 150
DESIGN_DOC_SECTIONS = ("goal", "constraint")

_HINT = (
    "See apps/examples/03-context/README.md for the expected layout: a DESIGN.md written "
    "before building, and one recorded run per condition under runs/."
)


_design_doc_check: Check = file_non_trivial(
    "design_doc_non_trivial",
    DESIGN_DOC_CANDIDATES,
    min_words=DESIGN_DOC_MIN_WORDS,
    required_sections=DESIGN_DOC_SECTIONS,
    hint=_HINT,
)

without_doc_run_present: Check = file_present(
    "without_doc_run_present",
    WITHOUT_DOC_RUN_CANDIDATES,
    hint=_HINT,
)

with_doc_run_present: Check = file_present(
    "with_doc_run_present",
    WITH_DOC_RUN_CANDIDATES,
    hint=_HINT,
)


_build_check: Check = command_succeeds(
    "build_runs",
    ["make", "build"],
    skip_if_missing=("Makefile", "package.json", "pyproject.toml"),
    hint="The repository must build with `make build` (or the project's documented build "
    "command aliased to it). Add a `build` target even if it only runs a compiler/typecheck.",
)


def register_all() -> tuple[Check, ...]:
    return (
        _design_doc_check,
        without_doc_run_present,
        with_doc_run_present,
        _build_check,
    )
