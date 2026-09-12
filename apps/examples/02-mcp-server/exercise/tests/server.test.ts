/**
 * The exercise's own conformance suite — the same three questions the real autograder
 * asks (see `handover/04-autograder.spec.md`, "Exercise 1, MCP server" and
 * `packages/autograder/src/autograder/checks/ex01_mcp.py`), so you get the same feedback
 * locally, for free, before pushing.
 *
 * This suite is meant to FAIL against the unfinished starter. Run `npm test` now, read the
 * failures, then implement the two TODOs in `src/server.ts` until it passes.
 */
import { test } from "node:test";
import assert from "node:assert/strict";
import { fileURLToPath } from "node:url";
import { dirname, join } from "node:path";
import { McpTestClient } from "./support/mcp-test-client.ts";

const here = dirname(fileURLToPath(import.meta.url));
const exerciseRoot = join(here, "..");

function startServer(): McpTestClient {
  return new McpTestClient("node", ["src/server.ts"], exerciseRoot);
}

test("initialize handshake succeeds", async () => {
  const client = startServer();
  try {
    const { result, error } = await client.initialize();
    assert.equal(error, undefined, `initialize върна грешка: ${JSON.stringify(error)}`);
    assert.equal(
      (result as { protocolVersion?: string } | undefined)?.protocolVersion,
      "2025-06-18",
      "initialize трябва да върне protocolVersion",
    );
  } finally {
    client.close();
  }
});

test("tools/list returns word_count with a valid schema", async () => {
  const client = startServer();
  try {
    await client.initialize();
    const { result, error } = await client.request("tools/list", {});
    assert.equal(error, undefined, `tools/list върна грешка: ${JSON.stringify(error)}`);

    const tools = (result as { tools?: unknown[] } | undefined)?.tools;
    assert.ok(Array.isArray(tools), "tools/list трябва да върне { tools: [...] }");

    const wordCount = tools?.find(
      (tool): tool is { name: string; description: string; inputSchema: Record<string, unknown> } =>
        typeof tool === "object" && tool !== null && (tool as { name?: unknown }).name === "word_count",
    );
    assert.ok(wordCount, `Няма инструмент "word_count" сред: ${JSON.stringify(tools)}`);
    assert.equal(typeof wordCount.description, "string", "description трябва да е низ");
    assert.ok(wordCount.description.length > 0, "description не трябва да е празен");

    const schema = wordCount.inputSchema;
    assert.equal(schema?.type, "object", "inputSchema.type трябва да е \"object\"");
    const properties = schema?.properties as Record<string, unknown> | undefined;
    assert.ok(properties && "text" in properties, "inputSchema.properties трябва да съдържа \"text\"");
    const required = schema?.required as string[] | undefined;
    assert.ok(Array.isArray(required) && required.includes("text"), "\"text\" трябва да е в required");
  } finally {
    client.close();
  }
});

const cases: Array<{ text: string; expectedSubstring: string }> = [
  { text: "the quick brown fox jumps over the lazy dog", expectedSubstring: "9" },
  { text: "one", expectedSubstring: "1" },
  { text: "   spaced   out   words   ", expectedSubstring: "3" },
];

for (const { text, expectedSubstring } of cases) {
  test(`tools/call word_count("${text}") includes "${expectedSubstring}"`, async () => {
    const client = startServer();
    try {
      await client.initialize();
      const { result, error } = await client.request("tools/call", {
        name: "word_count",
        arguments: { text },
      });
      assert.equal(error, undefined, `tools/call върна грешка: ${JSON.stringify(error)}`);

      const call = result as { isError?: boolean; content?: Array<{ type: string; text?: string }> };
      assert.notEqual(call?.isError, true, `tools/call върна isError=true: ${JSON.stringify(call)}`);

      const textBlock = call?.content?.find((block) => block.type === "text");
      assert.ok(textBlock, `Резултатът няма content от тип "text": ${JSON.stringify(call)}`);
      assert.ok(
        textBlock.text?.includes(expectedSubstring),
        `Очаквах "${expectedSubstring}" в текста, получих: ${JSON.stringify(textBlock.text)}`,
      );
    } finally {
      client.close();
    }
  });
}

test("unknown tool is handled, not crashed, and the server keeps working", async () => {
  const client = startServer();
  try {
    await client.initialize();
    const { result, error } = await client.request("tools/call", {
      name: "definitely_not_a_tool",
      arguments: {},
    });

    const handled = error !== undefined || (result as { isError?: boolean } | undefined)?.isError === true;
    assert.ok(
      handled,
      "Извикване на непознат инструмент трябва да върне JSON-RPC грешка или isError=true, " +
        `а не тих успех: ${JSON.stringify({ result, error })}`,
    );

    // The real test: the process must still be alive and answering afterwards.
    const after = await client.request("tools/list", {});
    assert.equal(
      after.error,
      undefined,
      "След заявка за непознат инструмент сървърът вече не отговаря на tools/list — процесът е паднал.",
    );
  } finally {
    client.close();
  }
});
