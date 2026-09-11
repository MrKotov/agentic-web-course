"""Reusable check builders.

Everything here is deterministic and cheap: a file is there or it is not, a command exits
zero or it does not, a URL answers 200 or it does not. Nothing here scores style, volume or
similarity, by design.
"""

from __future__ import annotations

import os
import re
import shlex
import subprocess
from collections.abc import Callable, Sequence
from datetime import date, datetime, timedelta
from pathlib import Path

from ..context import SubmissionContext
from ..models import CheckResult

Check = Callable[[SubmissionContext], CheckResult]

_SKIP_DIRS = {".git", "node_modules", ".venv", "venv", "__pycache__", "dist", "build", ".next"}


def named(check: Check, name: str) -> Check:
    """Tag a callable with the check name it emits, for crash reporting."""
    check.check_name = name  # type: ignore[attr-defined]
    return check


def file_present(name: str, candidates: Sequence[str], *, hint: str) -> Check:
    """Pass when at least one of `candidates` exists in the repository."""

    def check(context: SubmissionContext) -> CheckResult:
        for candidate in candidates:
            if context.exists(candidate):
                return CheckResult(name, True, f"Found {candidate}.")
        return CheckResult(
            name,
            False,
            f"None of {list(candidates)} exists in the repository. {hint}",
        )

    return named(check, name)


def file_non_trivial(
    name: str,
    candidates: Sequence[str],
    *,
    min_words: int,
    required_sections: Sequence[str] = (),
    hint: str,
) -> Check:
    """Pass when the document exists, has at least `min_words` words, and names its sections.

    "Non-trivial" is defined mechanically on purpose. It is a floor, not a quality judgement:
    whether the document is any good is a question for the defense.
    """

    def check(context: SubmissionContext) -> CheckResult:
        path = _first_existing(context, candidates)
        if path is None:
            return CheckResult(name, False, f"None of {list(candidates)} exists. {hint}")
        try:
            text = path.read_text(encoding="utf-8", errors="replace")
        except OSError as exc:
            return CheckResult(name, False, f"{path.name} could not be read: {exc}")
        words = len(text.split())
        if words < min_words:
            return CheckResult(
                name,
                False,
                f"{path.name} has {words} words; at least {min_words} are required. {hint}",
            )
        lowered = text.lower()
        missing = [s for s in required_sections if s.lower() not in lowered]
        if missing:
            return CheckResult(
                name,
                False,
                f"{path.name} does not mention the required sections: {missing}. {hint}",
            )
        return CheckResult(name, True, f"{path.name}: {words} words, all required sections present.")

    return named(check, name)


def command_succeeds(
    name: str,
    command: str | Sequence[str],
    *,
    cwd: str = ".",
    timeout: int = 300,
    skip_if_missing: Sequence[str] = (),
    hint: str,
) -> Check:
    """Pass when the command exits zero.

    `skip_if_missing` names files that must exist for the command to be meaningful; if none
    of them exist the check FAILS rather than skipping, because a missing build file is a
    non-conforming submission, not an excuse.
    """
    argv = shlex.split(command) if isinstance(command, str) else list(command)

    def check(context: SubmissionContext) -> CheckResult:
        if skip_if_missing and not any(context.exists(p) for p in skip_if_missing):
            return CheckResult(
                name,
                False,
                f"Expected one of {list(skip_if_missing)} in the repository so that "
                f"`{shlex.join(argv)}` can run. {hint}",
            )
        workdir = context.path(cwd)
        try:
            completed = subprocess.run(  # noqa: S603
                argv,
                cwd=str(workdir),
                capture_output=True,
                text=True,
                timeout=timeout,
                check=False,
            )
        except FileNotFoundError:
            return CheckResult(name, False, f"`{argv[0]}` is not available on the runner. {hint}")
        except subprocess.TimeoutExpired:
            return CheckResult(
                name, False, f"`{shlex.join(argv)}` did not finish within {timeout}s. {hint}"
            )
        if completed.returncode == 0:
            return CheckResult(name, True, f"`{shlex.join(argv)}` exited 0.")
        tail = _tail(completed.stdout + completed.stderr)
        return CheckResult(
            name,
            False,
            f"`{shlex.join(argv)}` exited {completed.returncode}. Last output:\n{tail}",
        )

    return named(check, name)


def url_returns_200(name: str, *, path: str = "/", timeout: int = 20, hint: str) -> Check:
    """Pass when `context.deployed_url` answers 200 within the timeout."""

    def check(context: SubmissionContext) -> CheckResult:
        import httpx

        if not context.deployed_url:
            return CheckResult(
                name,
                False,
                "No deployed URL was supplied. Set DEPLOYED_URL in the workflow (or the "
                f"repository variable the template documents). {hint}",
            )
        url = context.deployed_url.rstrip("/") + path
        try:
            response = httpx.get(url, timeout=timeout, follow_redirects=True)
        except httpx.HTTPError as exc:
            return CheckResult(name, False, f"GET {url} failed: {type(exc).__name__}: {exc}. {hint}")
        if response.status_code == 200:
            return CheckResult(name, True, f"GET {url} returned 200.")
        return CheckResult(
            name, False, f"GET {url} returned {response.status_code}, expected 200. {hint}"
        )

    return named(check, name)


# -- secret scan -----------------------------------------------------------------

SECRET_PATTERNS: list[tuple[str, re.Pattern[str]]] = [
    ("AWS access key id", re.compile(r"\bAKIA[0-9A-Z]{16}\b")),
    ("GitHub token", re.compile(r"\b(?:ghp|gho|ghu|ghs|ghr)_[A-Za-z0-9]{36,}\b")),
    ("GitHub fine-grained token", re.compile(r"\bgithub_pat_[A-Za-z0-9_]{60,}\b")),
    ("OpenAI-style API key", re.compile(r"\bsk-[A-Za-z0-9]{32,}\b")),
    ("OpenRouter key", re.compile(r"\bsk-or-v1-[A-Za-z0-9]{32,}\b")),
    ("Slack token", re.compile(r"\bxox[abprs]-[A-Za-z0-9-]{10,}\b")),
    ("Google API key", re.compile(r"\bAIza[0-9A-Za-z_\-]{35}\b")),
    ("Private key block", re.compile(r"-----BEGIN (?:RSA |EC |OPENSSH |PGP )?PRIVATE KEY-----")),
    (
        "Hardcoded credential assignment",
        re.compile(
            r"""(?i)\b(?:api[_-]?key|secret[_-]?key|access[_-]?token|password|passwd)\b\s*[:=]\s*["'][^"'\s${}]{16,}["']"""
        ),
    ),
]

_COMMITTED_ENV = re.compile(r"(^|/)\.env(\.|$)")
_ENV_ALLOWED = re.compile(r"(^|/)\.env\.example$")


def secret_scan(name: str, *, scan_history_commits: int = 200) -> Check:
    """Pass when neither the working tree nor recent history contains a credential.

    History matters: the exercise 5 brief plants a secret that was removed from the tip but
    is still in the log, and "delete the file" is not a fix.
    """

    def check(context: SubmissionContext) -> CheckResult:
        findings: list[str] = []
        for path in _walk(context.repo_path):
            rel = path.relative_to(context.repo_path).as_posix()
            if _COMMITTED_ENV.search(rel) and not _ENV_ALLOWED.search(rel):
                findings.append(f"{rel}: a .env file is committed; commit .env.example instead")
            findings.extend(f"{rel}:{line}: {label}" for label, line in _scan_file(path))
        history = _scan_history(context.repo_path, scan_history_commits)
        findings.extend(history)
        if findings:
            shown = "\n".join(f"  - {f}" for f in findings[:20])
            more = f"\n  ... and {len(findings) - 20} more" if len(findings) > 20 else ""
            return CheckResult(
                name,
                False,
                "Credentials found in the repository. Rotate them, then remove them from the "
                f"working tree and from history:\n{shown}{more}",
            )
        return CheckResult(name, True, "No credential patterns in the working tree or recent history.")

    return named(check, name)


def _scan_file(path: Path) -> list[tuple[str, int]]:
    if path.name == ".env.example":
        return []
    try:
        if path.stat().st_size > 1_000_000:
            return []
        text = path.read_text(encoding="utf-8", errors="ignore")
    except OSError:
        return []
    hits: list[tuple[str, int]] = []
    for number, line in enumerate(text.splitlines(), start=1):
        if "autograder:allow-secret-pattern" in line:
            continue
        for label, pattern in SECRET_PATTERNS:
            if pattern.search(line):
                hits.append((label, number))
    return hits


def _scan_history(repo_path: Path, max_commits: int) -> list[str]:
    if not (repo_path / ".git").exists():
        return []
    try:
        completed = subprocess.run(  # noqa: S603
            ["git", "-C", str(repo_path), "log", "-p", "--no-color", f"-{max_commits}", "--", "."],
            capture_output=True,
            text=True,
            timeout=120,
            check=False,
        )
    except (OSError, subprocess.SubprocessError):
        return []
    if completed.returncode != 0:
        return []
    findings: list[str] = []
    commit = "?"
    for line in completed.stdout.splitlines():
        if line.startswith("commit "):
            commit = line.split()[1][:8]
        elif line.startswith("+") and not line.startswith("+++"):
            if "autograder:allow-secret-pattern" in line:
                continue
            for label, pattern in SECRET_PATTERNS:
                if pattern.search(line):
                    findings.append(f"git history {commit}: {label}")
                    break
    return sorted(set(findings))


# -- prompt log ------------------------------------------------------------------

_DATE = re.compile(r"\b(\d{4})-(\d{2})-(\d{2})\b")


def prompt_log_covers_commits(
    name: str,
    candidates: Sequence[str],
    *,
    min_entries: int,
    tolerance_days: int = 2,
    hint: str,
) -> Check:
    """Pass when a prompt log exists and its dates span the commit history.

    The point is that the log was kept while the work happened, not written afterwards in
    one sitting. A machine can only check the span; whether the log is honest is a defense
    question.
    """

    def check(context: SubmissionContext) -> CheckResult:
        texts = _collect_prompt_log(context, candidates)
        if not texts:
            return CheckResult(name, False, f"No prompt log found at any of {list(candidates)}. {hint}")
        blob = "\n".join(texts)
        log_dates = sorted({_to_date(m) for m in _DATE.finditer(blob)} - {None})
        entries = blob.count("\n## ") + blob.count("\n### ")
        if entries < min_entries:
            return CheckResult(
                name,
                False,
                f"The prompt log has {entries} entries (counted as `##`/`###` headings); "
                f"at least {min_entries} are required. {hint}",
            )
        if not log_dates:
            return CheckResult(
                name,
                False,
                "The prompt log has no YYYY-MM-DD dates, so it cannot be matched to the "
                f"commit history. {hint}",
            )
        commit_range = _commit_date_range(context.repo_path)
        if commit_range is None:
            return CheckResult(
                name, True, f"Prompt log present with {entries} entries; no git history to compare."
            )
        first_commit, last_commit = commit_range
        slack = timedelta(days=tolerance_days)
        log_first, log_last = log_dates[0], log_dates[-1]
        if log_first > first_commit + slack or log_last < last_commit - slack:
            return CheckResult(
                name,
                False,
                f"The prompt log spans {log_first}..{log_last} but the commits span "
                f"{first_commit}..{last_commit}. The log must cover the period you were "
                f"working, not a single session. {hint}",
            )
        return CheckResult(
            name,
            True,
            f"Prompt log: {entries} entries spanning {log_first}..{log_last}, "
            f"covering commits {first_commit}..{last_commit}.",
        )

    return named(check, name)


def _collect_prompt_log(context: SubmissionContext, candidates: Sequence[str]) -> list[str]:
    texts: list[str] = []
    for candidate in candidates:
        path = context.path(candidate)
        if path.is_file():
            texts.append(_read(path))
        elif path.is_dir():
            for child in sorted(path.rglob("*")):
                if child.is_file() and child.suffix.lower() in {".md", ".txt", ".jsonl"}:
                    texts.append(_read(child))
    return [t for t in texts if t.strip()]


def _commit_date_range(repo_path: Path) -> tuple[date, date] | None:
    if not (repo_path / ".git").exists():
        return None
    try:
        completed = subprocess.run(  # noqa: S603
            ["git", "-C", str(repo_path), "log", "--format=%cs"],
            capture_output=True,
            text=True,
            timeout=60,
            check=False,
        )
    except (OSError, subprocess.SubprocessError):
        return None
    if completed.returncode != 0:
        return None
    stamps = sorted(
        d for d in (_parse_date(line.strip()) for line in completed.stdout.splitlines()) if d
    )
    if not stamps:
        return None
    return stamps[0], stamps[-1]


def _parse_date(value: str) -> date | None:
    try:
        return datetime.strptime(value, "%Y-%m-%d").date()
    except ValueError:
        return None


def _to_date(match: re.Match[str]) -> date | None:
    return _parse_date(match.group(0))


# -- small shared utilities ------------------------------------------------------


def _first_existing(context: SubmissionContext, candidates: Sequence[str]) -> Path | None:
    for candidate in candidates:
        path = context.path(candidate)
        if path.is_file():
            return path
    return None


def _read(path: Path) -> str:
    try:
        return path.read_text(encoding="utf-8", errors="replace")
    except OSError:
        return ""


def _walk(root: Path) -> list[Path]:
    found: list[Path] = []
    for dirpath, dirnames, filenames in os.walk(root):
        dirnames[:] = [d for d in dirnames if d not in _SKIP_DIRS]
        for filename in filenames:
            found.append(Path(dirpath) / filename)
    return found


def _tail(text: str, limit: int = 2000) -> str:
    stripped = text.strip()
    return stripped[-limit:] if len(stripped) > limit else stripped
