/**
 * The whole model client, in one file and with no dependencies.
 * `recorded` mode reads a fixture; `live` mode makes one HTTPS request.
 * Lecture 1 is demonstrated entirely in `recorded` mode — the hall network is
 * assumed to be broken.
 */
import { readFileSync } from "node:fs";

export interface ChatMessage {
  role: "system" | "user" | "assistant";
  content: string;
}

export interface ChatResult {
  text: string;
  model: string;
  source: "recorded" | "live";
  promptTokens: number;
  completionTokens: number;
}

/** The subset of the OpenAI-compatible response we depend on. */
interface ChatCompletionResponse {
  model?: string;
  choices?: Array<{ message?: { content?: string } }>;
  usage?: { prompt_tokens?: number; completion_tokens?: number };
}

export interface RecordedRun {
  /** Free-form label so a recording can be found by name. */
  id: string;
  model: string;
  messages: ChatMessage[];
  response: ChatCompletionResponse;
}

export function loadRecording(path: string, id: string): RecordedRun {
  const parsed: unknown = JSON.parse(readFileSync(path, "utf8"));
  if (!Array.isArray(parsed)) {
    throw new Error(`Recording file ${path} must contain a JSON array of runs.`);
  }
  const runs = parsed as RecordedRun[];
  const found = runs.find((run) => run.id === id);
  if (found === undefined) {
    const available = runs.map((run) => run.id).join(", ");
    throw new Error(`No recorded run with id "${id}" in ${path}. Available: ${available}`);
  }
  return found;
}

function toResult(
  response: ChatCompletionResponse,
  fallbackModel: string,
  source: "recorded" | "live",
): ChatResult {
  const text = response.choices?.[0]?.message?.content;
  if (typeof text !== "string") {
    throw new Error("Response contained no assistant message.");
  }
  return {
    text,
    model: response.model ?? fallbackModel,
    source,
    promptTokens: response.usage?.prompt_tokens ?? 0,
    completionTokens: response.usage?.completion_tokens ?? 0,
  };
}

export function replay(run: RecordedRun): ChatResult {
  return toResult(run.response, run.model, "recorded");
}

export interface LiveOptions {
  apiKey: string;
  model: string;
  messages: ChatMessage[];
  temperature?: number;
  seed?: number;
  timeoutMs?: number;
}

const OPENROUTER_URL = "https://openrouter.ai/api/v1/chat/completions";

export async function chatLive(options: LiveOptions): Promise<ChatResult> {
  const controller = new AbortController();
  const timeout = setTimeout(() => controller.abort(), options.timeoutMs ?? 30_000);
  try {
    const response = await fetch(OPENROUTER_URL, {
      method: "POST",
      headers: {
        Authorization: `Bearer ${options.apiKey}`,
        "Content-Type": "application/json",
      },
      body: JSON.stringify({
        model: options.model,
        messages: options.messages,
        ...(options.temperature !== undefined ? { temperature: options.temperature } : {}),
        ...(options.seed !== undefined ? { seed: options.seed } : {}),
      }),
      signal: controller.signal,
    });
    if (!response.ok) {
      const body = await response.text();
      throw new Error(`Provider returned HTTP ${response.status}: ${body.slice(0, 300)}`);
    }
    const parsed = (await response.json()) as ChatCompletionResponse;
    return toResult(parsed, options.model, "live");
  } finally {
    clearTimeout(timeout);
  }
}
