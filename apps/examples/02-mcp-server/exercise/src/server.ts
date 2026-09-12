#!/usr/bin/env node
/**
 * 02-mcp-server — starter.
 *
 * A hand-rolled MCP server that talks JSON-RPC 2.0 over stdio. No SDK, no framework: this
 * is the file the lecture is about, so the transport loop and the `initialize` handshake
 * are written for you below, working, and you should read them before touching anything.
 *
 * Your job is the two TODOs: answering `tools/list` and `tools/call`. Everything the
 * autograder checks (see `.autograder/mcp-server.json` and the exercise README) comes down
 * to those two handlers.
 *
 * Protocol rule that trips people up: stdout carries ONLY JSON-RPC messages, one per line.
 * Never `console.log` for debugging — use `console.error` (stderr) instead, or you will
 * corrupt every message after it.
 */
import { createInterface } from "node:readline";
import {
  ErrorCode,
  PROTOCOL_VERSION,
  TOOL_NAME,
  failure,
  isRequest,
  success,
  textContent,
  type JsonRpcMessage,
  type JsonRpcRequest,
  type ToolDeclaration,
} from "./protocol.ts";

// -- transport: reads/writes JSON-RPC frames, one per line -------------------------------
// This part is given. You should not need to change it.

const rl = createInterface({ input: process.stdin, terminal: false });

rl.on("line", (line) => {
  const trimmed = line.trim();
  if (trimmed.length === 0) return;

  let message: JsonRpcMessage;
  try {
    message = JSON.parse(trimmed) as JsonRpcMessage;
  } catch {
    // Not valid JSON. There is no request id to reply to, so there is nothing to send back
    // — but the process must keep running for the next line.
    console.error(`[server] could not parse line as JSON: ${trimmed.slice(0, 200)}`);
    return;
  }

  if (!isRequest(message)) {
    // A notification (e.g. `notifications/initialized`): no reply expected.
    return;
  }

  const response = dispatch(message);
  process.stdout.write(`${JSON.stringify(response)}\n`);
});

// -- dispatch: routes a request to a handler, and never lets a handler crash the process --
// This part is given. Add cases here only if you add tools; do not remove the try/catch.

function dispatch(request: JsonRpcRequest) {
  try {
    switch (request.method) {
      case "initialize":
        return handleInitialize(request);
      case "tools/list":
        return handleToolsList(request);
      case "tools/call":
        return handleToolsCall(request);
      default:
        return failure(request.id, ErrorCode.MethodNotFound, `Method not found: ${request.method}`);
    }
  } catch (error) {
    // A handler that throws must still produce a JSON-RPC error, not a dead process. A
    // server that crashes on a bad request fails the "unknown tool" check even if
    // `tools/call` itself is later correct.
    const message = error instanceof Error ? error.message : String(error);
    return failure(request.id, ErrorCode.InternalError, message);
  }
}

// -- initialize: the handshake. Given, working. -------------------------------------------

function handleInitialize(request: JsonRpcRequest) {
  return success(request.id, {
    protocolVersion: PROTOCOL_VERSION,
    capabilities: { tools: {} },
    serverInfo: { name: "course-02-mcp-server-exercise", version: "0.1.0" },
  });
}

// -- TODO 1: tools/list ---------------------------------------------------------------
//
// Return the list of tools this server exposes. Exactly one tool, named `word_count`
// (see `TOOL_NAME` in protocol.ts — use the constant, do not retype the string).
//
// The result must have the shape `{ tools: ToolDeclaration[] }`, and each declaration
// needs a non-empty `name`, a non-empty `description`, and an `inputSchema` that is a
// JSON Schema object declaring one required string property: `text`.
//
// See the exercise README for the exact schema the autograder expects.

function handleToolsList(request: JsonRpcRequest) {
  throw notImplemented(
    "tools/list",
    "върнете { tools: [ ... ] } с описанието на word_count — вижте README.md",
  );
}

// -- TODO 2: tools/call ----------------------------------------------------------------
//
// `request.params` is `{ name: string, arguments: Record<string, unknown> }`.
//
// - If `name` is `TOOL_NAME` ("word_count"):
//     - `arguments.text` must be a string. If it is missing or not a string, return a
//       result with `isError: true` and an explanatory text block — do not throw.
//     - Otherwise, count words (split on whitespace, ignore empty pieces) and return
//       `{ content: [ textContent(`...${count}...`) ] }`. The count must appear in the
//       text as a plain decimal number — the autograder checks for its digits as a
//       substring.
// - If `name` is anything else: return a result with `isError: true` (or throw — the
//   catch above turns it into a JSON-RPC error either way). Both are "handled"; a crash
//   or a silent success are not.

function handleToolsCall(request: JsonRpcRequest) {
  throw notImplemented(
    "tools/call",
    "изпълнете word_count и обработете непознато име на инструмент — вижте README.md",
  );
}

// -- helper ------------------------------------------------------------------------------

function notImplemented(where: string, hint: string): Error {
  return new Error(`TODO не е довършено (${where}): ${hint}`);
}
