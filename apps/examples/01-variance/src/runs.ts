/** Loading the ten recorded runs, and (optionally) producing ten live ones. */
import { readFileSync } from "node:fs";
import { extractJson, type JsonValue, type RunOutcome } from "./schema.ts";

export interface PromptMessage {
  role: "system" | "user" | "assistant";
  content: string;
}

export interface RecordedRun {
  index: number;
  text: string;
  usage: { prompt_tokens: number; completion_tokens: number };
}

export interface RecordedSession {
  model: string;
  temperature: number;
  recorded_at: string;
  prompt: PromptMessage[];
  runs: RecordedRun[];
}

export function loadSession(path: string): RecordedSession {
  const session = JSON.parse(readFileSync(path, "utf8")) as RecordedSession;
  if (!Array.isArray(session.runs) || session.runs.length === 0) {
    throw new Error(`${path} contains no runs.`);
  }
  return session;
}

export function toOutcomes(runs: Array<{ index: number; text: string }>): RunOutcome[] {
  return runs.map((run) => {
    const parsed: JsonValue | undefined = extractJson(run.text);
    return parsed === undefined
      ? { index: run.index }
      : { index: run.index, parsed };
  });
}

const OPENROUTER_URL = "https://openrouter.ai/api/v1/chat/completions";

export interface LiveSessionOptions {
  apiKey: string;
  model: string;
  prompt: PromptMessage[];
  temperature: number;
  runs: number;
}

/** Used only outside the lecture hall. Sequential on purpose: free tiers rate-limit. */
export async function runLive(
  options: LiveSessionOptions,
): Promise<Array<{ index: number; text: string }>> {
  const results: Array<{ index: number; text: string }> = [];
  for (let i = 0; i < options.runs; i += 1) {
    const response = await fetch(OPENROUTER_URL, {
      method: "POST",
      headers: {
        Authorization: `Bearer ${options.apiKey}`,
        "Content-Type": "application/json",
      },
      body: JSON.stringify({
        model: options.model,
        messages: options.prompt,
        temperature: options.temperature,
      }),
    });
    if (!response.ok) {
      throw new Error(
        `Run ${i + 1} failed with HTTP ${response.status}. ` +
          "429 означава изчерпан безплатен лимит — изчакайте минута.",
      );
    }
    const body = (await response.json()) as {
      choices?: Array<{ message?: { content?: string } }>;
    };
    results.push({ index: i + 1, text: body.choices?.[0]?.message?.content ?? "" });
  }
  return results;
}
