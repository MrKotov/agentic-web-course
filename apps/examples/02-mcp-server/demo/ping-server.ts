#!/usr/bin/env node
/**
 * Demo server for the lecture hall.
 *
 * A complete, working hand-rolled MCP server — deliberately with a different tool
 * (`ping`) than the exercise (`word_count`), so watching this demo does not hand students
 * the exercise's answer. The point of the demo is the shape of the protocol: `initialize`,
 * `tools/list`, `tools/call`, and a bad request that does not kill the server.
 */
import { createInterface } from "node:readline";

const PROTOCOL_VERSION = "2025-06-18";

const rl = createInterface({ input: process.stdin, terminal: false });

rl.on("line", (line) => {
  const trimmed = line.trim();
  if (trimmed.length === 0) return;

  const message = JSON.parse(trimmed) as {
    id?: string | number;
    method: string;
    params?: { name?: string; arguments?: { message?: unknown } };
  };
  if (message.id === undefined) return; // notification, no reply

  process.stdout.write(`${JSON.stringify(handle(message))}\n`);
});

function handle(message: {
  id?: string | number;
  method: string;
  params?: { name?: string; arguments?: { message?: unknown } };
}) {
  const id = message.id as string | number;
  switch (message.method) {
    case "initialize":
      return {
        jsonrpc: "2.0",
        id,
        result: {
          protocolVersion: PROTOCOL_VERSION,
          capabilities: { tools: {} },
          serverInfo: { name: "course-02-mcp-server-demo", version: "0.1.0" },
        },
      };

    case "tools/list":
      return {
        jsonrpc: "2.0",
        id,
        result: {
          tools: [
            {
              name: "ping",
              description: "Връща обратно съобщението, което получи.",
              inputSchema: {
                type: "object",
                properties: { message: { type: "string" } },
                required: ["message"],
              },
            },
          ],
        },
      };

    case "tools/call": {
      const name = message.params?.name;
      if (name !== "ping") {
        return {
          jsonrpc: "2.0",
          id,
          result: { isError: true, content: [{ type: "text", text: `Непознат инструмент: ${name}` }] },
        };
      }
      const text = message.params?.arguments?.message;
      return {
        jsonrpc: "2.0",
        id,
        result: { content: [{ type: "text", text: `pong: ${String(text)}` }] },
      };
    }

    default:
      return { jsonrpc: "2.0", id, error: { code: -32601, message: `Method not found: ${message.method}` } };
  }
}
