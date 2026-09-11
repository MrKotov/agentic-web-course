"""Ingest endpoint for autograder results (handover/04, 'Result format')."""

from __future__ import annotations

import hmac
import json
from typing import Any

from django.conf import settings
from django.http import HttpRequest, HttpResponse, JsonResponse
from django.utils.dateparse import parse_datetime
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_POST

from .models import Submission

SECRET_HEADER = "HTTP_X_AUTOGRADER_SECRET"


def _secret_ok(request: HttpRequest) -> bool:
    """Constant-time compare the presented shared secret against the configured one."""
    expected = settings.AUTOGRADER_SHARED_SECRET
    if not expected:
        return False
    presented = request.META.get(SECRET_HEADER, "")
    return hmac.compare_digest(presented, expected)


def _validate(payload: Any) -> tuple[dict[str, Any] | None, str | None]:
    """Return (cleaned payload, error message). Exactly one of the two is None."""
    if not isinstance(payload, dict):
        return None, "payload must be a JSON object"
    for field in ("exercise", "repo", "commit", "completed_at"):
        value = payload.get(field)
        if not isinstance(value, str) or not value:
            return None, f"missing or invalid field: {field}"
    checks = payload.get("checks")
    if not isinstance(checks, list):
        return None, "missing or invalid field: checks"
    for check in checks:
        if not isinstance(check, dict) or "name" not in check or "passed" not in check:
            return None, "each check needs a name and a passed flag"
    completed_at = parse_datetime(payload["completed_at"])
    if completed_at is None:
        return None, "completed_at must be an ISO 8601 timestamp"
    return {
        "exercise": payload["exercise"],
        "repo": payload["repo"],
        "commit": payload["commit"],
        "checks": checks,
        "completed_at": completed_at,
    }, None


@csrf_exempt
@require_POST
def ingest_result(request: HttpRequest) -> HttpResponse:
    """Accept a result JSON, authenticate by shared secret, upsert on (repo, commit)."""
    if not _secret_ok(request):
        return JsonResponse({"error": "unauthorized"}, status=401)
    try:
        payload = json.loads(request.body.decode("utf-8"))
    except (ValueError, UnicodeDecodeError):
        return JsonResponse({"error": "invalid JSON"}, status=400)

    cleaned, error = _validate(payload)
    if cleaned is None:
        return JsonResponse({"error": error}, status=400)

    submission, created = Submission.objects.update_or_create(
        repo=cleaned["repo"],
        commit=cleaned["commit"],
        defaults={
            "exercise": cleaned["exercise"],
            "checks": cleaned["checks"],
            "completed_at": cleaned["completed_at"],
        },
    )
    return JsonResponse(
        {
            "id": submission.pk,
            "created": created,
            "passed": submission.passed,
        },
        status=201 if created else 200,
    )
