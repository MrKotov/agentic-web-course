/**
 * Lecture 0 demo. Runs from a recording: no API key, no network.
 * Pass --live to make a real call (only outside the lecture hall).
 */
import { fileURLToPath } from "node:url";
import { dirname, join } from "node:path";
import { loadEnv } from "../src/env.ts";
import { chatLive, loadRecording, replay, type ChatResult } from "../src/chat.ts";

const here = dirname(fileURLToPath(import.meta.url));
const recordingPath = join(here, "recordings", "hello-world.json");

async function main(): Promise<void> {
  const wantsLive = process.argv.includes("--live");
  const env = loadEnv(join(here, "..", ".env"));
  const run = loadRecording(recordingPath, "hello-world");

  let result: ChatResult;
  if (wantsLive) {
    if (env.apiKey === undefined) {
      console.error("--live иска OPENROUTER_API_KEY в .env. Пуснете без --live.");
      process.exitCode = 1;
      return;
    }
    result = await chatLive({ apiKey: env.apiKey, model: env.model, messages: run.messages });
  } else {
    result = replay(run);
  }

  console.log("=== prompt ===");
  for (const message of run.messages) {
    console.log(`[${message.role}] ${message.content}`);
  }
  console.log("\n=== отговор ===");
  console.log(result.text);
  console.log("\n=== метаданни ===");
  console.log(`източник: ${result.source}   модел: ${result.model}`);
  console.log(`токени: ${result.promptTokens} вход + ${result.completionTokens} изход`);
  if (result.source === "recorded") {
    console.log("(запис — нула мрежови заявки, нула стотинки)");
  }
}

await main();
