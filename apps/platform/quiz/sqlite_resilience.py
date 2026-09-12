"""SQLite concurrency workaround for the classroom write burst.

SQLite allows exactly one writer at a time; under enough parallel traffic even *readers*
can see a transient `sqlite3.OperationalError: database table is locked` instead of simply
waiting their turn, and there is no fairness guarantee that a retry will eventually win. That
is a real risk during a live quiz: up to 40 phones can answer inside the same few seconds
(spec, acceptance criterion 2).

Postgres — used in staging and production, see `config/settings.py` — uses MVCC and does not
have this limitation, so this decorator is a no-op there. Locally, and in any deployment that
genuinely runs on SQLite, it serialises the student write views with a single process-wide
lock. A lecture hall of 40 phones each answering five questions over three minutes is a low
enough request rate (roughly one request per second at peak) that serialising them costs
nothing anyone would notice, and it turns "usually fine, occasionally errors under load" into
"always correct".
"""

from __future__ import annotations

import threading
from collections.abc import Callable
from functools import wraps

from django.db import connection
from django.http import HttpRequest, HttpResponse

_sqlite_write_lock = threading.Lock()


def serialize_on_sqlite[F: Callable[..., HttpResponse]](view: F) -> F:
    """Run a view under a process-wide lock when the backend is SQLite.

    A no-op on Postgres, where concurrent writers are Postgres's problem to solve and it
    already does, via MVCC rather than a single file lock.
    """

    @wraps(view)
    def wrapped(request: HttpRequest, *args: object, **kwargs: object) -> HttpResponse:
        if connection.vendor != "sqlite":
            return view(request, *args, **kwargs)
        with _sqlite_write_lock:
            return view(request, *args, **kwargs)

    return wrapped  # type: ignore[return-value]
