/**
 * A tiny MCP client for the test suite, given to you working.
 *
 * It is deliberately similar to (but simpler than) the real autograder client in
 * `packages/autograder/src/autograder/mcp/client.py`: spawn the server, speak JSON-RPC over
 * stdio, one request at a time, bounded by a timeout so a hung server fails the test
 * instead of hanging the run.
 *
 * You should not need to change this file. If a test fails, the bug is almost always in
 * `src/server.ts`, not here.
 */
import { spawn, type ChildProcessWithoutNullStreams } from "node:child_process";
import { createInterface } from "node:readline";

export interface JsonRpcResult {
  result?: unknown;
  error?: { code: number; message: string } | undefined;
}

export class McpTestClient {
  private readonly child: ChildProcessWithoutNullStreams;
  private nextId = 0;
  private readonly pending = new Map<
    number,
    { resolve: (value: JsonRpcResult) => void; reject: (error: Error) => void }
  >();
  private readonly stderrChunks: string[] = [];
  private closed = false;

  constructor(command: string, args: string[], cwd: string) {
    this.child = spawn(command, args, { cwd, stdio: ["pipe", "pipe", "pipe"] });
    this.child.on("error", (error) => this.failAllPending(error));
    this.child.on("exit", () => {
      this.closed = true;
      this.failAllPending(
        new Error(`Процесът на сървъра приключи неочаквано. stderr: ${this.stderrTail()}`),
      );
    });

    const stdout = createInterface({ input: this.child.stdout, terminal: false });
    stdout.on("line", (line) => this.handleLine(line));
    this.child.stderr.on("data", (chunk: Buffer) => this.stderrChunks.push(chunk.toString("utf8")));
  }

  private handleLine(line: string): void {
    const trimmed = line.trim();
    if (trimmed.length === 0) return;
    let message: { id?: number; result?: unknown; error?: { code: number; message: string } };
    try {
      message = JSON.parse(trimmed);
    } catch {
      return; // Non-JSON stdout is a server bug the test itself will surface via a timeout.
    }
    if (typeof message.id !== "number") return;
    const waiting = this.pending.get(message.id);
    if (!waiting) return;
    this.pending.delete(message.id);
    waiting.resolve({ result: message.result, error: message.error });
  }

  private failAllPending(error: Error): void {
    for (const { reject } of this.pending.values()) reject(error);
    this.pending.clear();
  }

  stderrTail(): string {
    return this.stderrChunks.join("").slice(-1000);
  }

  request(method: string, params: Record<string, unknown>, timeoutMs = 5000): Promise<JsonRpcResult> {
    if (this.closed) {
      return Promise.reject(new Error("Сървърът вече е спрян."));
    }
    const id = this.nextId++;
    const payload = JSON.stringify({ jsonrpc: "2.0", id, method, params }) + "\n";
    return new Promise<JsonRpcResult>((resolve, reject) => {
      const timer = setTimeout(() => {
        this.pending.delete(id);
        reject(
          new Error(
            `Няма отговор на "${method}" за ${timeoutMs}ms. stderr: ${this.stderrTail() || "(празно)"}`,
          ),
        );
      }, timeoutMs);
      this.pending.set(id, {
        resolve: (value) => {
          clearTimeout(timer);
          resolve(value);
        },
        reject: (error) => {
          clearTimeout(timer);
          reject(error);
        },
      });
      this.child.stdin.write(payload, (error) => {
        if (error) {
          clearTimeout(timer);
          this.pending.delete(id);
          reject(error);
        }
      });
    });
  }

  notify(method: string, params: Record<string, unknown>): void {
    const payload = JSON.stringify({ jsonrpc: "2.0", method, params }) + "\n";
    this.child.stdin.write(payload);
  }

  async initialize(): Promise<JsonRpcResult> {
    const result = await this.request("initialize", {
      protocolVersion: "2025-06-18",
      capabilities: {},
      clientInfo: { name: "exercise-02-test-client", version: "0.1.0" },
    });
    this.notify("notifications/initialized", {});
    return result;
  }

  close(): void {
    if (this.closed) return;
    this.closed = true;
    this.child.kill();
  }
}
