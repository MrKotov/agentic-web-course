/**
 * Lecture 1 demo: one prompt, ten runs, schema diff.
 * Default mode replays `recordings/ten-runs.json`: no key, no network.
 */
import { fileURLToPath } from "node:url";
import { dirname, join } from "node:path";
import { loadSession, runLive, toOutcomes } from "../src/runs.ts";
import { analyse } from "../src/schema.ts";
import { renderReport } from "../src/report.ts";
import { loadEnv } from "../../00-setup/src/env.ts";

const here = dirname(fileURLToPath(import.meta.url));

async function main(): Promise<void> {
  const live = process.argv.includes("--live");
  const session = loadSession(join(here, "recordings", "ten-runs.json"));

  console.log("=== един и същи prompt ===");
  for (const message of session.prompt) {
    console.log(`[${message.role}] ${message.content}`);
  }
  console.log(`\nмодел: ${session.model}   temperature: ${session.temperature}`);

  let runs: Array<{ index: number; text: string }>;
  if (live) {
    const env = loadEnv(join(here, "..", ".env"));
    if (env.apiKey === undefined) {
      console.error("--live иска OPENROUTER_API_KEY в .env. Пуснете без --live.");
      process.exitCode = 1;
      return;
    }
    console.log("режим: live — 10 последователни заявки, това отнема време\n");
    runs = await runLive({
      apiKey: env.apiKey,
      model: env.model,
      prompt: session.prompt,
      temperature: session.temperature,
      runs: 10,
    });
  } else {
    console.log(`режим: запис от ${session.recorded_at} — нула мрежови заявки\n`);
    runs = session.runs;
  }

  console.log("=== десет отговора ===");
  for (const run of runs) {
    const oneLine = run.text.replaceAll("\n", " ").trim();
    const shown = oneLine.length > 110 ? `${oneLine.slice(0, 107)}...` : oneLine;
    console.log(`${String(run.index).padStart(2)}. ${shown}`);
  }

  console.log("\n=== разлики в схемата ===");
  console.log(renderReport(analyse(toOutcomes(runs))));
}

await main();
