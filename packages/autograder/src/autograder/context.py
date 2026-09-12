"""Everything a check is allowed to know about the submission under test."""

from __future__ import annotations

import os
import subprocess
from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True, slots=True)
class SubmissionContext:
    """The repository under test, plus the environment facts checks may read.

    Checks receive this and nothing else. They must not reach for global state, so that a
    run is reproducible from the context alone.
    """

    repo_path: Path
    repo: str
    commit: str
    deployed_url: str | None = None
    timeout_seconds: int = 120

    def path(self, *parts: str) -> Path:
        return self.repo_path.joinpath(*parts)

    def exists(self, *parts: str) -> bool:
        return self.path(*parts).exists()


def detect_repo(repo_path: Path) -> str:
    """Best-effort `owner/name` for the checkout.

    Prefers GITHUB_REPOSITORY, which CI always sets, and falls back to the origin remote so
    the harness is usable from an instructor's laptop.
    """
    env_repo = os.environ.get("GITHUB_REPOSITORY")
    if env_repo:
        return env_repo
    remote = _git(repo_path, "config", "--get", "remote.origin.url")
    if remote:
        trimmed = remote.removesuffix(".git")
        if ":" in trimmed or "/" in trimmed:
            parts = trimmed.replace(":", "/").split("/")
            if len(parts) >= 2:
                return "/".join(parts[-2:])
    return repo_path.name


def detect_commit(repo_path: Path) -> str:
    """Best-effort commit SHA for the checkout."""
    env_sha = os.environ.get("GITHUB_SHA")
    if env_sha:
        return env_sha
    return _git(repo_path, "rev-parse", "HEAD") or "unknown"


def _git(repo_path: Path, *args: str) -> str:
    try:
        completed = subprocess.run(
            ["git", "-C", str(repo_path), *args],
            capture_output=True,
            text=True,
            timeout=15,
            check=False,
        )
    except (OSError, subprocess.SubprocessError):
        return ""
    return completed.stdout.strip() if completed.returncode == 0 else ""
