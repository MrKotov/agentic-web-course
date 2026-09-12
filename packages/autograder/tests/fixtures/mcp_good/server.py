#!/usr/bin/env python3
"""A correct, minimal MCP server exposing `word_count`. Used to prove the exercise 1 checks
pass end to end. Deliberately dependency-free, matching the constraint the real exercise
sets for students.
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
            "serverInfo": {"name": "fixture-mcp-good", "version": "1.0.0"},
        },
    )


def handle_tools_list(request: dict) -> dict:
    return _success(
        request,
        {
            "tools": [
                {
                    "name": TOOL_NAME,
                    "description": "Counts whitespace-separated words in the given text.",
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
    arguments = params.get("arguments", {})
    if name != TOOL_NAME:
        return _success(request, {"isError": True, "content": [_text(f"unknown tool: {name}")]})
    text = arguments.get("text")
    if not isinstance(text, str):
        return _success(request, {"isError": True, "content": [_text("`text` must be a string")]})
    count = len(text.split())
    return _success(request, {"content": [_text(f"{count} words")]})


def dispatch(request: dict) -> dict | None:
    method = request.get("method")
    handler = {
        "initialize": handle_initialize,
        "tools/list": handle_tools_list,
        "tools/call": handle_tools_call,
    }.get(method)
    if handler is None:
        return _error(request, -32601, f"Method not found: {method}")
    try:
        return handler(request)
    except Exception as exc:
        return _error(request, -32603, str(exc))


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
            continue  # a notification: no reply
        response = dispatch(message)
        if response is not None:
            sys.stdout.write(json.dumps(response) + "\n")
            sys.stdout.flush()


if __name__ == "__main__":
    main()
