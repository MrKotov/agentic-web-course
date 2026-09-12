"""Command-line entry point: `autograder run|submit|collect`.

- `run`     — inside a student's workflow (no secret): execute the checks, write result.json,
              print a human-readable summary. Exit non-zero if any check failed.
- `submit`  — post one result.json to the platform with retry. Used by the instructor-side
              collector (see README, "Secret handling"); never invoked from a student fork.
- `collect` — poll a roster of repositories for a finished `run`, download the result
              artifact, and `submit` each one. Instructor-side only, same reason as above.
"""

from __future__ import annotations

import argparse
import json
import os
import sys
from datetime import datetime
from pathlib import Path
from typing import Any

from .context import SubmissionContext, detect_commit, detect_repo
from .exercises import register_all
from .gh_artifacts import GitHubApiError, GitHubClient
from .models import CheckResult, RunResult
from .registry import UnknownExercise, known_exercises
from .runner import run_exercise
from .webhook import WebhookClient, WebhookError, load_result_json


def main(argv: list[str] | None = None) -> int:
    register_all()
    parser = _build_parser()
    args = parser.parse_args(argv)
    return args.handler(args)


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="autograder")
    sub = parser.add_subparsers(dest="command", required=True)

    run_parser = sub.add_parser("run", help="run an exercise's checks against a repository")
    run_parser.add_argument("--exercise", required=True, help=f"one of {known_exercises()}")
    run_parser.add_argument("--repo-path", default=".", type=Path)
    run_parser.add_argument("--deployed-url", default=os.environ.get("DEPLOYED_URL"))
    run_parser.add_argument("--timeout-seconds", type=int, default=120)
    run_parser.add_argument("--out", default="result.json", type=Path)
    run_parser.set_defaults(handler=_cmd_run)

    submit_parser = sub.add_parser("submit", help="post a result.json to the platform, with retry")
    submit_parser.add_argument("--result", required=True, type=Path)
    submit_parser.add_argument("--platform-url", default=os.environ.get("AUTOGRADER_PLATFORM_URL"))
    submit_parser.add_argument("--secret", default=os.environ.get("AUTOGRADER_SHARED_SECRET"))
    submit_parser.set_defaults(handler=_cmd_submit)

    collect_parser = sub.add_parser(
        "collect", help="poll a roster of repos for finished runs and submit their results"
    )
    collect_parser.add_argument("--roster", required=True, type=Path)
    collect_parser.add_argument("--platform-url", default=os.environ.get("AUTOGRADER_PLATFORM_URL"))
    collect_parser.add_argument("--secret", default=os.environ.get("AUTOGRADER_SHARED_SECRET"))
    collect_parser.add_argument("--github-token", default=os.environ.get("COLLECTOR_GITHUB_TOKEN"))
    collect_parser.set_defaults(handler=_cmd_collect)

    return parser


def _cmd_run(args: argparse.Namespace) -> int:
    repo_path: Path = args.repo_path.resolve()
    context = SubmissionContext(
        repo_path=repo_path,
        repo=detect_repo(repo_path),
        commit=detect_commit(repo_path),
        deployed_url=args.deployed_url,
        timeout_seconds=args.timeout_seconds,
    )
    try:
        result = run_exercise(args.exercise, context)
    except UnknownExercise as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2

    args.out.write_text(result.to_json(), encoding="utf-8")
    _print_summary(result)
    summary_path = os.environ.get("GITHUB_STEP_SUMMARY")
    if summary_path:
        Path(summary_path).open("a", encoding="utf-8").write(_markdown_summary(result))
    return 0 if result.passed else 1


def _cmd_submit(args: argparse.Namespace) -> int:
    if not args.platform_url or not args.secret:
        print(
            "error: --platform-url/AUTOGRADER_PLATFORM_URL and --secret/AUTOGRADER_SHARED_SECRET "
            "are both required.",
            file=sys.stderr,
        )
        return 2
    payload = load_result_json(args.result)
    result = _result_from_dict(payload)
    return _submit(result, platform_url=args.platform_url, secret=args.secret)


def _cmd_collect(args: argparse.Namespace) -> int:
    if not args.platform_url or not args.secret or not args.github_token:
        print(
            "error: --platform-url, --secret and --github-token are all required for collect.",
            file=sys.stderr,
        )
        return 2
    roster = json.loads(args.roster.read_text(encoding="utf-8"))
    repos = [entry["repo"] for entry in roster if isinstance(entry, dict) and entry.get("repo")]
    client = GitHubClient(token=args.github_token)
    exit_code = 0
    for repo in repos:
        try:
            run_id = client.latest_run_id(repo)
            if run_id is None:
                print(f"{repo}: no workflow runs yet, skipping.")
                continue
            artifact = client.find_result_artifact(repo, run_id)
            if artifact is None:
                print(f"{repo}: run {run_id} has no {'autograder-result'!r} artifact, skipping.")
                continue
            payload = client.download_result_json(repo, artifact["id"])
        except GitHubApiError as exc:
            print(f"{repo}: {exc}", file=sys.stderr)
            exit_code = 1
            continue
        result = _result_from_dict(payload)
        if _submit(result, platform_url=args.platform_url, secret=args.secret) != 0:
            exit_code = 1
    return exit_code


def _submit(result: RunResult, *, platform_url: str, secret: str) -> int:
    webhook = WebhookClient(base_url=platform_url, secret=secret)
    try:
        outcome = webhook.post(result)
    except WebhookError as exc:
        print(f"{result.repo}@{result.commit[:8]}: rejected: {exc}", file=sys.stderr)
        return 1
    if outcome.delivered:
        print(
            f"{result.repo}@{result.commit[:8]}: delivered "
            f"(attempt {outcome.attempts}, status {outcome.status_code}, "
            f"created={outcome.created})."
        )
        return 0
    print(
        f"{result.repo}@{result.commit[:8]}: NOT delivered after {outcome.attempts} attempts. "
        f"{outcome.detail} Recovered to {outcome.recovery_path}.",
        file=sys.stderr,
    )
    return 1


def _result_from_dict(payload: dict[str, Any]) -> RunResult:
    return RunResult(
        exercise=payload["exercise"],
        repo=payload["repo"],
        commit=payload["commit"],
        checks=[CheckResult(**c) for c in payload["checks"]],
        completed_at=datetime.fromisoformat(payload["completed_at"].replace("Z", "+00:00")),
    )


def _print_summary(result: RunResult) -> None:
    print(f"== {result.exercise} :: {result.repo}@{result.commit[:8]} ==")
    for check in result.checks:
        mark = "PASS" if check.passed else "FAIL"
        print(f"[{mark}] {check.name}")
        if check.detail and not check.passed:
            print(f"       {check.detail}")
    print(f"-- {'ALL CHECKS PASSED' if result.passed else 'SOME CHECKS FAILED'} --")


def _markdown_summary(result: RunResult) -> str:
    lines = [f"## Autograder: {result.exercise}\n", "| Check | Result |", "|---|---|"]
    for check in result.checks:
        mark = "PASS" if check.passed else "FAIL"
        lines.append(f"| {check.name} | {mark} |")
    if not result.passed:
        lines.append("\n### Details\n")
        for check in result.checks:
            if not check.passed:
                lines.append(f"- **{check.name}**: {check.detail or '(no detail)'}")
    return "\n".join(lines) + "\n"


if __name__ == "__main__":
    sys.exit(main())
