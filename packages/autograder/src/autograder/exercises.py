"""Registers every exercise's checks with the harness.

Importing this module is the one thing that wires `checks/*.py` into `registry.py`. The CLI
imports it before running anything; nothing else needs to know the exercise ids exist.
"""

from __future__ import annotations

from .checks import ex01_mcp, ex02_spec_driven, ex03_agent_feature, ex04_deployment, ex05_security
from .registry import register

EXERCISE_01 = "01-mcp-server"
EXERCISE_02 = "02-spec-driven"
EXERCISE_03 = "03-agent-feature"
EXERCISE_04 = "04-deployment"
EXERCISE_05 = "05-security-review"


def register_all() -> None:
    """Idempotent: safe to call more than once (e.g. once per test)."""
    register(EXERCISE_01, [ex01_mcp.probe_mcp_server])
    register(EXERCISE_02, ex02_spec_driven.register_all())
    register(EXERCISE_03, ex03_agent_feature.register_all())
    register(EXERCISE_04, ex04_deployment.register_all())
    register(EXERCISE_05, ex05_security.register_all())
