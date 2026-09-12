#!/usr/bin/env python3
"""A deliberately broken MCP server, used to prove the exercise 1 checks actually fail.

Three independent defects, each targeting a different check:
  - `tools/list` declares the tool without a `description`, so the schema check fails.
  - `word_count` always returns a wrong, hardcoded count, so the invocation check fails.
  - an unknown tool name crashes the process outright, so both the "unknown tool handled"
    and "server survives" checks fail.
"""

from __future__ import annotations

import json
import sys

PROTOCOL_VERSION = "2025-06-18"
TOOL_NAME = "word_count"


def handle_initialize(request: dict) -> dict:
    return _success(
        request,
        {
            "protocolVersion": PROTOCOL_VERSION,
            "capabilities": {"tools": {}},
            "serverInfo": {"name": "fixture-mcp-broken", "version": "1.0.0"},
        },
    )


def handle_tools_list(request: dict) -> dict:
    return _success(
        request,
        {
            "tools": [
                {
                    # Defect: no "description" field at all.
                    "name": TOOL_NAME,
                    "inputSchema": {
                        "type": "object",
                        "properties": {"text": {"type": "string"}},
                        "required": ["text"],
                    },
                }
            ]
        },
    )


def handle_tools_call(request: dict) -> dict:
    params = request.get("params", {})
    name = params.get("name")
    if name != TOOL_NAME:
        # Defect: an unhandled crash instead of a JSON-RPC error or isError=true.
        sys.exit(1)
    # Defect: ignores the input and always returns the same wrong count.
    return _success(request, {"content": [_text("0 words")]})


def dispatch(request: dict) -> dict | None:
    method = request.get("method")
    handler = {
        "initialize": handle_initialize,
        "tools/list": handle_tools_list,
        "tools/call": handle_tools_call,
    }.get(method)
    if handler is None:
        return _error(request, -32601, f"Method not found: {method}")
    return handler(request)


def _success(request: dict, result: dict) -> dict:
    return {"jsonrpc": "2.0", "id": request["id"], "result": result}


def _error(request: dict, code: int, message: str) -> dict:
    return {"jsonrpc": "2.0", "id": request.get("id"), "error": {"code": code, "message": message}}


def _text(text: str) -> dict:
    return {"type": "text", "text": text}


def main() -> None:
    for line in sys.stdin:
        line = line.strip()
        if not line:
            continue
        try:
            message = json.loads(line)
        except json.JSONDecodeError:
            continue
        if "id" not in message:
            continue
        response = dispatch(message)
        if response is not None:
            sys.stdout.write(json.dumps(response) + "\n")
            sys.stdout.flush()


if __name__ == "__main__":
    main()
