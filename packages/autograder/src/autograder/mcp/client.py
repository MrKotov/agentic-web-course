"""A dependency-free MCP client that speaks JSON-RPC 2.0 over stdio.

Deliberately not built on an MCP SDK. The student's server may be written in any language,
the grader must fail on protocol violations rather than have an SDK paper over them, and a
frozen hand-rolled client keeps the grade reproducible across semesters.

Everything here is bounded by a timeout. A server that hangs is a failing server, not a
hanging grader.
"""

from __future__ import annotations

import json
import os
import queue
import shlex
import subprocess
import threading
from dataclasses import dataclass, field
from pathlib import Path
from types import TracebackType
from typing import Any

PROTOCOL_VERSION = "2025-06-18"
"""The MCP revision the harness negotiates. Pinned: a semester must grade against one revision."""

SUPPORTED_PROTOCOL_VERSIONS = frozenset({"2025-06-18", "2025-03-26", "2024-11-05"})
"""Revisions the harness accepts back from a server, so a student SDK one minor behind still
grades."""

MANIFEST_PATH = ".autograder/mcp-server.json"
"""Where a submission declares how to start its server. The only thing the student controls."""


class McpError(RuntimeError):
    """Any failure to speak MCP with the server: transport, protocol or timeout."""


@dataclass(frozen=True, slots=True)
class ServerLaunch:
    """How to start the server under test."""

    command: list[str]
    cwd: Path
    env: dict[str, str] = field(default_factory=dict)

    def describe(self) -> str:
        return shlex.join(self.command)


def load_launch_manifest(repo_path: Path, manifest_path: str = MANIFEST_PATH) -> ServerLaunch:
    """Read `.autograder/mcp-server.json` from the submission.

    The manifest carries the launch command only. What the server must *do* is fixed by the
    exercise contract in this package, so a submission cannot redefine its own grade.
    """
    path = repo_path / manifest_path
    if not path.is_file():
        raise McpError(
            f"Missing {manifest_path}. Create it with the command that starts your server, "
            'for example: {"command": ["python", "-m", "server"]}'
        )
    try:
        raw = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise McpError(f"{manifest_path} is not readable JSON: {exc}") from exc
    if not isinstance(raw, dict):
        raise McpError(f"{manifest_path} must contain a JSON object.")

    command = raw.get("command")
    if isinstance(command, str):
        command = shlex.split(command)
    if not isinstance(command, list) or not command or not all(isinstance(p, str) for p in command):
        raise McpError(
            f'{manifest_path} needs a non-empty "command", a string or a list of strings.'
        )
    args = raw.get("args", [])
    if not isinstance(args, list) or not all(isinstance(p, str) for p in args):
        raise McpError(f'{manifest_path}: "args" must be a list of strings.')

    cwd_value = raw.get("cwd", ".")
    if not isinstance(cwd_value, str):
        raise McpError(f'{manifest_path}: "cwd" must be a string.')
    cwd = (repo_path / cwd_value).resolve()
    if not cwd.is_dir():
        raise McpError(
            f'{manifest_path}: "cwd" {cwd_value!r} is not a directory in the repository.'
        )

    env_value = raw.get("env", {})
    if not isinstance(env_value, dict) or not all(
        isinstance(k, str) and isinstance(v, str) for k, v in env_value.items()
    ):
        raise McpError(f'{manifest_path}: "env" must be a string-to-string object.')

    return ServerLaunch(command=[*command, *args], cwd=cwd, env=dict(env_value))


class McpStdioClient:
    """One MCP session against one server process.

    Use as a context manager; the process is always terminated, including on failure.
    """

    def __init__(self, launch: ServerLaunch, *, timeout: float = 20.0) -> None:
        self._launch = launch
        self._timeout = timeout
        self._process: subprocess.Popen[str] | None = None
        self._stdout: queue.Queue[str | None] = queue.Queue()
        self._stderr_chunks: list[str] = []
        self._next_id = 0
        self._server_info: dict[str, Any] = {}

    # -- lifecycle ---------------------------------------------------------------

    def __enter__(self) -> McpStdioClient:
        self.start()
        return self

    def __exit__(
        self,
        exc_type: type[BaseException] | None,
        exc: BaseException | None,
        tb: TracebackType | None,
    ) -> None:
        self.close()

    def start(self) -> None:
        env = {**os.environ, **self._launch.env, "PYTHONUNBUFFERED": "1"}
        try:
            self._process = subprocess.Popen(
                self._launch.command,
                cwd=str(self._launch.cwd),
                env=env,
                stdin=subprocess.PIPE,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                bufsize=1,
            )
        except OSError as exc:
            raise McpError(
                f"Could not start the server with {self._launch.describe()!r}: {exc}"
            ) from exc
        threading.Thread(target=self._pump_stdout, daemon=True).start()
        threading.Thread(target=self._pump_stderr, daemon=True).start()

    def close(self) -> None:
        process = self._process
        if process is None:
            return
        try:
            if process.stdin and not process.stdin.closed:
                process.stdin.close()
        except OSError:
            pass
        try:
            process.wait(timeout=3)
        except subprocess.TimeoutExpired:
            process.kill()
            try:
                process.wait(timeout=3)
            except subprocess.TimeoutExpired:
                pass
        self._process = None

    @property
    def stderr_tail(self) -> str:
        """Last of the server's stderr, for putting in a failure message."""
        text = "".join(self._stderr_chunks).strip()
        return text[-1500:]

    @property
    def server_info(self) -> dict[str, Any]:
        return dict(self._server_info)

    # -- protocol ----------------------------------------------------------------

    def initialize(self) -> dict[str, Any]:
        """Perform the MCP handshake. Raises McpError if the server will not shake hands."""
        result = self.request(
            "initialize",
            {
                "protocolVersion": PROTOCOL_VERSION,
                "capabilities": {},
                "clientInfo": {"name": "course-autograder", "version": "0.1.0"},
            },
        )
        if not isinstance(result, dict):
            raise McpError("initialize did not return a result object.")
        negotiated = result.get("protocolVersion")
        if not isinstance(negotiated, str) or negotiated not in SUPPORTED_PROTOCOL_VERSIONS:
            raise McpError(
                f"initialize returned protocolVersion {negotiated!r}; the grader speaks "
                f"{sorted(SUPPORTED_PROTOCOL_VERSIONS)}."
            )
        self._server_info = result
        self.notify("notifications/initialized", {})
        return result

    def list_tools(self) -> list[dict[str, Any]]:
        """Return the `tools` array from `tools/list`, or raise if it is not one."""
        result = self.request("tools/list", {})
        if not isinstance(result, dict) or not isinstance(result.get("tools"), list):
            raise McpError("tools/list must return an object with a `tools` array.")
        return list(result["tools"])

    def call_tool(self, name: str, arguments: dict[str, Any]) -> dict[str, Any]:
        """Invoke a tool. Returns the JSON-RPC *result* object."""
        result = self.request("tools/call", {"name": name, "arguments": arguments})
        if not isinstance(result, dict):
            raise McpError(f"tools/call for {name!r} did not return a result object.")
        return result

    def call_tool_allowing_error(
        self, name: str, arguments: dict[str, Any]
    ) -> tuple[dict[str, Any] | None, dict[str, Any] | None]:
        """Invoke a tool, tolerating a JSON-RPC error response.

        Returns `(result, error)`; exactly one is not None. Used for the unknown-tool check,
        where a protocol-level error is a correct answer and a crash is not.
        """
        message = self._exchange(
            name_method="tools/call", params={"name": name, "arguments": arguments}
        )
        if "error" in message:
            error = message["error"]
            return None, error if isinstance(error, dict) else {"message": str(error)}
        return message.get("result"), None

    # -- transport ---------------------------------------------------------------

    def request(self, method: str, params: dict[str, Any]) -> Any:
        message = self._exchange(name_method=method, params=params)
        if "error" in message:
            raise McpError(f"{method} returned a JSON-RPC error: {json.dumps(message['error'])}")
        return message.get("result")

    def notify(self, method: str, params: dict[str, Any]) -> None:
        self._write({"jsonrpc": "2.0", "method": method, "params": params})

    def _exchange(self, *, name_method: str, params: dict[str, Any]) -> dict[str, Any]:
        self._next_id += 1
        request_id = self._next_id
        self._write({"jsonrpc": "2.0", "id": request_id, "method": name_method, "params": params})
        # Skip anything that is not the answer to this request: servers may interleave
        # notifications or log lines of their own.
        while True:
            message = self._read_message(name_method)
            if message.get("id") == request_id:
                return message

    def _write(self, message: dict[str, Any]) -> None:
        process = self._require_process()
        if process.stdin is None:
            raise McpError("The server process has no stdin.")
        try:
            process.stdin.write(json.dumps(message) + "\n")
            process.stdin.flush()
        except (BrokenPipeError, ValueError) as exc:
            raise McpError(
                f"The server closed its input before answering {message.get('method')!r}. "
                f"It probably exited. stderr: {self.stderr_tail or '(empty)'}"
            ) from exc

    def _read_message(self, method: str) -> dict[str, Any]:
        process = self._require_process()
        while True:
            try:
                line = self._stdout.get(timeout=self._timeout)
            except queue.Empty:
                raise McpError(
                    f"The server did not answer {method!r} within {self._timeout:.0f}s. "
                    f"stderr: {self.stderr_tail or '(empty)'}"
                ) from None
            if line is None:
                code = process.poll()
                raise McpError(
                    f"The server closed stdout while answering {method!r} "
                    f"(exit code {code}). stderr: {self.stderr_tail or '(empty)'}"
                )
            line = line.strip()
            if not line:
                continue
            try:
                message = json.loads(line)
            except json.JSONDecodeError:
                # Not JSON: almost always a stray print() to stdout, which corrupts the
                # transport. Keep reading, but the detail below names the real problem.
                self._stderr_chunks.append(
                    f"\n[non-JSON line on stdout, which breaks MCP framing]: {line[:200]}\n"
                )
                continue
            if not isinstance(message, dict):
                continue
            if "id" in message or "error" in message:
                return message
            # A notification from the server; ignore and keep waiting.

    def _require_process(self) -> subprocess.Popen[str]:
        if self._process is None:
            raise McpError("The server process is not running. Call start() first.")
        return self._process

    def _pump_stdout(self) -> None:
        process = self._process
        if process is None or process.stdout is None:
            return
        try:
            for line in process.stdout:
                self._stdout.put(line)
        except (OSError, ValueError):
            pass
        finally:
            self._stdout.put(None)

    def _pump_stderr(self) -> None:
        process = self._process
        if process is None or process.stderr is None:
            return
        try:
            for line in process.stderr:
                self._stderr_chunks.append(line)
                if len(self._stderr_chunks) > 500:
                    del self._stderr_chunks[:250]
        except (OSError, ValueError):
            pass
