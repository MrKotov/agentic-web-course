/**
 * Minimal JSON-RPC 2.0 / MCP framing types.
 *
 * This file is given to you working — it is the "framing" part of the protocol, not the
 * part the exercise is testing. What you write lives in `server.ts`: the two handlers that
 * decide *what* the server answers, not *how* the bytes are shaped.
 */

export const PROTOCOL_VERSION = "2025-06-18";

/** The one tool this exercise's server must expose. Do not rename it — the autograder
 * calls it by this exact name. */
export const TOOL_NAME = "word_count";

export interface JsonRpcRequest {
  jsonrpc: "2.0";
  id: string | number;
  method: string;
  params?: Record<string, unknown>;
}

export interface JsonRpcNotification {
  jsonrpc: "2.0";
  method: string;
  params?: Record<string, unknown>;
}

export interface JsonRpcSuccess {
  jsonrpc: "2.0";
  id: string | number;
  result: unknown;
}

export interface JsonRpcFailure {
  jsonrpc: "2.0";
  id: string | number;
  error: { code: number; message: string; data?: unknown };
}

export type JsonRpcMessage = JsonRpcRequest | JsonRpcNotification;

/** True when the incoming message expects a reply (has an `id`). Notifications do not. */
export function isRequest(message: JsonRpcMessage): message is JsonRpcRequest {
  return "id" in message && message.id !== undefined && message.id !== null;
}

export function success(id: string | number, result: unknown): JsonRpcSuccess {
  return { jsonrpc: "2.0", id, result };
}

export function failure(id: string | number, code: number, message: string): JsonRpcFailure {
  return { jsonrpc: "2.0", id, error: { code, message } };
}

/** Standard JSON-RPC error codes used by this server. */
export const ErrorCode = {
  ParseError: -32700,
  MethodNotFound: -32601,
  InvalidParams: -32602,
  InternalError: -32603,
} as const;

/** A single text content block, the shape `tools/call` results are built from. */
export function textContent(text: string): { type: "text"; text: string } {
  return { type: "text", text };
}

/** The MCP JSON Schema for one tool declaration, as returned by `tools/list`. */
export interface ToolDeclaration {
  name: string;
  description: string;
  inputSchema: {
    type: "object";
    properties: Record<string, { type: string; description?: string }>;
    required: string[];
  };
}
