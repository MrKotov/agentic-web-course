"""Exercise 1: MCP server, no framework.

The substantive exercise. The harness speaks MCP to the student's server and asks three
behavioural questions from the spec: does it answer `tools/list` with a valid schema, does
it invoke the named tool with the right arguments, does it survive an unknown tool.

What the server must *do* is fixed here, by the instructor. The submission supplies only the
launch command, in `.autograder/mcp-server.json`, so no submission can redefine its own
grade. To change the assignment, edit `EXERCISE_01_CONTRACT` and the exercise README
together; they are one contract in two places.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from ..context import SubmissionContext
from ..mcp import McpError, McpStdioClient, load_launch_manifest
from ..mcp.client import MANIFEST_PATH
from ..models import CheckResult


@dataclass(frozen=True, slots=True)
class ToolCase:
    """One deterministic invocation: these arguments must produce text containing these strings."""

    arguments: dict[str, Any]
    expected_substrings: tuple[str, ...]


@dataclass(frozen=True, slots=True)
class ToolContract:
    """The tool the exercise requires, and how it is exercised."""

    name: str
    required_arguments: tuple[str, ...]
    cases: tuple[ToolCase, ...]
    unknown_tool_name: str = "definitely_not_a_tool"
    launch_timeout_seconds: float = 20.0
    aliases: tuple[str, ...] = field(default=())


EXERCISE_01_CONTRACT = ToolContract(
    name="word_count",
    required_arguments=("text",),
    cases=(
        ToolCase({"text": "the quick brown fox jumps over the lazy dog"}, ("9",)),
        ToolCase({"text": "one"}, ("1",)),
        ToolCase({"text": "   spaced   out   words   "}, ("3",)),
    ),
)

CHECK_NAMES = (
    "server_manifest_present",
    "initialize_handshake",
    "tools_list_responds",
    "tools_list_schema_valid",
    "required_tool_declared",
    "tool_invocation_matches_spec",
    "unknown_tool_handled",
    "server_survives_unknown_tool",
)


def probe_mcp_server(context: SubmissionContext) -> list[CheckResult]:
    """Run the whole exercise 1 suite in a single MCP session.

    One session rather than one per check: starting a server is the expensive part, and a
    single session is also the honest test — a real client does not restart between calls.
    """
    return _probe(context, EXERCISE_01_CONTRACT)


probe_mcp_server.check_names = CHECK_NAMES  # type: ignore[attr-defined]


def _probe(context: SubmissionContext, contract: ToolContract) -> list[CheckResult]:
    results: _Results = _Results()

    try:
        launch = load_launch_manifest(context.repo_path)
    except McpError as exc:
        results.add("server_manifest_present", False, str(exc))
        return results.finish("The server could not be started, so nothing else could be tested.")
    results.add(
        "server_manifest_present",
        True,
        f"{MANIFEST_PATH} starts the server with `{launch.describe()}`.",
    )

    with McpStdioClient(launch, timeout=contract.launch_timeout_seconds) as client:
        try:
            info = client.initialize()
        except McpError as exc:
            results.add(
                "initialize_handshake",
                False,
                f"{exc} An MCP server must answer `initialize` on stdin and write only "
                "JSON-RPC messages to stdout — send your own logging to stderr.",
            )
            return results.finish("The handshake failed, so nothing else could be tested.")
        server_name = _server_name(info)
        results.add("initialize_handshake", True, f"Handshake succeeded with {server_name}.")

        try:
            tools = client.list_tools()
        except McpError as exc:
            results.add("tools_list_responds", False, str(exc))
            return results.finish("`tools/list` failed, so nothing else could be tested.")
        results.add(
            "tools_list_responds",
            True,
            f"`tools/list` returned {len(tools)} tool(s): {sorted(_tool_names(tools))}.",
        )

        schema_problems = _schema_problems(tools)
        results.add(
            "tools_list_schema_valid",
            not schema_problems,
            (
                "Every declared tool has a name, a description and an object inputSchema."
                if not schema_problems
                else "These tool declarations are not valid:\n"
                + "\n".join(f"  - {p}" for p in schema_problems)
            ),
        )

        tool = _find_tool(tools, contract)
        if tool is None:
            results.add(
                "required_tool_declared",
                False,
                f"No tool named {contract.name!r} in `tools/list`; found "
                f"{sorted(_tool_names(tools))}. The exercise brief fixes the tool name.",
            )
            return results.finish(f"The tool {contract.name!r} does not exist.")

        missing_args = _missing_required_arguments(tool, contract)
        results.add(
            "required_tool_declared",
            not missing_args,
            (
                f"{contract.name!r} is declared and requires {list(contract.required_arguments)}."
                if not missing_args
                else f"{contract.name!r} is declared, but its inputSchema does not require "
                f"{missing_args}. Put them in `inputSchema.properties` and list them in "
                "`inputSchema.required`."
            ),
        )

        results.add(*_invocation_outcome(client, contract))
        results.add(*_unknown_tool_outcome(client, contract))
        results.add(*_survival_outcome(client, contract))

    return results.finish("Not reached.")


# -- individual probes -----------------------------------------------------------


def _invocation_outcome(client: McpStdioClient, contract: ToolContract) -> tuple[str, bool, str]:
    name = "tool_invocation_matches_spec"
    for case in contract.cases:
        try:
            result = client.call_tool(contract.name, case.arguments)
        except McpError as exc:
            return name, False, f"Calling {contract.name} with {case.arguments!r} failed: {exc}"
        if result.get("isError"):
            return (
                name,
                False,
                f"Calling {contract.name} with {case.arguments!r} returned isError=true: "
                f"{_text_of(result)!r}",
            )
        text = _text_of(result)
        if text is None:
            return (
                name,
                False,
                f"Calling {contract.name} with {case.arguments!r} returned no text content. "
                'The result must contain `content: [{"type": "text", "text": "..."}]`.',
            )
        missing = [s for s in case.expected_substrings if s not in text]
        if missing:
            return (
                name,
                False,
                f"Calling {contract.name} with {case.arguments!r} returned {text!r}, which does "
                f"not contain {missing}. Check the exercise brief for what the tool must return.",
            )
    return (
        name,
        True,
        f"{contract.name} returned the expected answer for all {len(contract.cases)} cases.",
    )


def _unknown_tool_outcome(client: McpStdioClient, contract: ToolContract) -> tuple[str, bool, str]:
    name = "unknown_tool_handled"
    try:
        result, error = client.call_tool_allowing_error(contract.unknown_tool_name, {})
    except McpError as exc:
        return (
            name,
            False,
            f"Calling the unknown tool {contract.unknown_tool_name!r} broke the server: {exc} "
            "An unknown tool must produce a JSON-RPC error or a result with isError=true — "
            "never an unhandled exception that kills the process.",
        )
    if error is not None:
        return name, True, f"Unknown tool answered with a JSON-RPC error: {error.get('message')!r}."
    if isinstance(result, dict) and result.get("isError"):
        return name, True, f"Unknown tool answered with isError=true: {_text_of(result)!r}."
    return (
        name,
        False,
        f"Calling the unknown tool {contract.unknown_tool_name!r} returned a successful result "
        f"({result!r}). Reject names you do not implement, with a JSON-RPC error or isError=true.",
    )


def _survival_outcome(client: McpStdioClient, contract: ToolContract) -> tuple[str, bool, str]:
    name = "server_survives_unknown_tool"
    try:
        tools = client.list_tools()
    except McpError as exc:
        return (
            name,
            False,
            f"After the unknown-tool call the server no longer answers `tools/list`: {exc} "
            "A bad request must not end the session.",
        )
    if contract.name not in _tool_names(tools):
        return (
            name,
            False,
            f"After the unknown-tool call, `tools/list` no longer contains {contract.name!r}.",
        )
    return name, True, "The server still answers `tools/list` after a bad request."


# -- inspection helpers ----------------------------------------------------------


def _schema_problems(tools: list[dict[str, Any]]) -> list[str]:
    problems: list[str] = []
    for index, tool in enumerate(tools):
        label = f"tool #{index}"
        if not isinstance(tool, dict):
            problems.append(f"{label} is not an object")
            continue
        raw_name = tool.get("name")
        label = f"tool {raw_name!r}" if isinstance(raw_name, str) else label
        if not isinstance(raw_name, str) or not raw_name.strip():
            problems.append(f"{label}: `name` must be a non-empty string")
        description = tool.get("description")
        if not isinstance(description, str) or not description.strip():
            problems.append(f"{label}: `description` must be a non-empty string")
        schema = tool.get("inputSchema")
        if not isinstance(schema, dict):
            problems.append(f"{label}: `inputSchema` must be a JSON Schema object")
            continue
        if schema.get("type") != "object":
            problems.append(f'{label}: `inputSchema.type` must be "object"')
        if not isinstance(schema.get("properties"), dict):
            problems.append(f"{label}: `inputSchema.properties` must be an object")
        required = schema.get("required", [])
        if not isinstance(required, list) or not all(isinstance(r, str) for r in required):
            problems.append(f"{label}: `inputSchema.required` must be a list of strings")
    return problems


def _tool_names(tools: list[dict[str, Any]]) -> set[str]:
    return {t["name"] for t in tools if isinstance(t, dict) and isinstance(t.get("name"), str)}


def _find_tool(tools: list[dict[str, Any]], contract: ToolContract) -> dict[str, Any] | None:
    wanted = {contract.name, *contract.aliases}
    for tool in tools:
        if isinstance(tool, dict) and tool.get("name") in wanted:
            return tool
    return None


def _missing_required_arguments(tool: dict[str, Any], contract: ToolContract) -> list[str]:
    schema = tool.get("inputSchema")
    if not isinstance(schema, dict):
        return list(contract.required_arguments)
    properties = schema.get("properties")
    properties = properties if isinstance(properties, dict) else {}
    required = schema.get("required")
    required = set(required) if isinstance(required, list) else set()
    return [a for a in contract.required_arguments if a not in properties or a not in required]


def _text_of(result: dict[str, Any] | None) -> str | None:
    if not isinstance(result, dict):
        return None
    content = result.get("content")
    if not isinstance(content, list):
        return None
    parts = [
        block["text"]
        for block in content
        if isinstance(block, dict)
        and block.get("type") == "text"
        and isinstance(block.get("text"), str)
    ]
    return "\n".join(parts) if parts else None


def _server_name(info: dict[str, Any]) -> str:
    server = info.get("serverInfo")
    if isinstance(server, dict) and isinstance(server.get("name"), str):
        version = server.get("version")
        return f"{server['name']} {version}" if isinstance(version, str) else server["name"]
    return "an unnamed server"


class _Results:
    """Collects outcomes and fills the remaining check names when a stage aborts the run."""

    def __init__(self) -> None:
        self._by_name: dict[str, CheckResult] = {}

    def add(self, name: str, passed: bool, detail: str) -> None:
        self._by_name[name] = CheckResult(name, passed, detail)

    def finish(self, reason: str) -> list[CheckResult]:
        for name in CHECK_NAMES:
            self._by_name.setdefault(name, CheckResult(name, False, f"Not run. {reason}"))
        return [self._by_name[name] for name in CHECK_NAMES]
