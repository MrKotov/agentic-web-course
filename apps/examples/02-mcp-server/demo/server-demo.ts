/**
 * Lecture 2 demo: what the instructor runs in the hall.
 *
 * Spawns `ping-server.ts` (a complete, working hand-rolled MCP server) and drives it with a
 * tiny inline JSON-RPC client, printing every request and response so the class can see the
 * protocol frame by frame: `initialize`, `tools/list`, `tools/call`, and a bad request that
 * does not kill the server.
 *
 * There is no `--live` mode here and no recording to replay: an MCP server talks over local
 * stdio, not the network, so this demo has nothing to fail even with the venue's wifi down.
 */
import { spawn } from "node:child_process";
import { createInterface } from "node:readline";
import { fileURLToPath } from "node:url";
import { dirname, join } from "node:path";

const here = dirname(fileURLToPath(import.meta.url));
const serverPath = join(here, "ping-server.ts");

interface JsonRpcMessage {
  jsonrpc: "2.0";
  id?: number;
  result?: unknown;
  error?: unknown;
}

function send(
  stdin: NodeJS.WritableStream,
  id: number,
  method: string,
  params: Record<string, unknown>,
): void {
  const request = { jsonrpc: "2.0", id, method, params };
  console.log(`\n--> ${JSON.stringify(request)}`);
  stdin.write(`${JSON.stringify(request)}\n`);
}

async function main(): Promise<void> {
  const child = spawn("node", [serverPath], { stdio: ["pipe", "pipe", "inherit"] });
  if (child.stdin === null || child.stdout === null) {
    throw new Error("Неочаквано: процесът няма stdin/stdout — проверете spawn() опциите.");
  }
  const stdin = child.stdin;
  const rl = createInterface({ input: child.stdout, terminal: false });
  const pending = new Map<number, (message: JsonRpcMessage) => void>();

  rl.on("line", (line) => {
    const trimmed = line.trim();
    if (trimmed.length === 0) return;
    const message = JSON.parse(trimmed) as JsonRpcMessage;
    console.log(`<-- ${JSON.stringify(message)}`);
    if (typeof message.id === "number") {
      pending.get(message.id)?.(message);
      pending.delete(message.id);
    }
  });

  let nextId = 1;
  function call(method: string, params: Record<string, unknown>): Promise<JsonRpcMessage> {
    const id = nextId++;
    return new Promise((resolve) => {
      pending.set(id, resolve);
      send(stdin, id, method, params);
    });
  }

  console.log("=== 1. initialize (ръкостискане) ===");
  await call("initialize", { protocolVersion: "2025-06-18", capabilities: {}, clientInfo: { name: "demo", version: "0" } });

  console.log("\n=== 2. tools/list ===");
  await call("tools/list", {});

  console.log("\n=== 3. tools/call с валиден инструмент ===");
  await call("tools/call", { name: "ping", arguments: { message: "здрасти" } });

  console.log("\n=== 4. tools/call с НЕПОЗНАТ инструмент — сървърът не бива да падне ===");
  await call("tools/call", { name: "definitely_not_a_tool", arguments: {} });

  console.log("\n=== 5. сървърът е още жив — пак tools/list ===");
  await call("tools/list", {});

  console.log("\nГотово. Точно тези пет стъпки проверява автоматичният оценител в 02-mcp-server/exercise.");
  child.kill();
}

await main();
