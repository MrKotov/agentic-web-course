/**
 * 00-setup access check.
 *
 * Runs with no API key and no network by default: it proves the toolchain and the
 * repository work. `--live` additionally spends one free-tier request to prove the
 * key works.
 *
 * Every failure must print something the student can act on. If it does not, that
 * is a bug in this file, not in the student's setup.
 */
import { existsSync, readFileSync } from "node:fs";
import { fileURLToPath } from "node:url";
import { dirname, join, resolve } from "node:path";
import { loadEnv, looksLikeOpenRouterKey, maskKey } from "../src/env.ts";
import { chatLive, loadRecording, replay } from "../src/chat.ts";

const here = dirname(fileURLToPath(import.meta.url));
const root = resolve(here, "..");
const repoRoot = resolve(root, "..");

interface CheckOutcome {
  name: string;
  passed: boolean;
  detail: string;
  /** A failed optional check warns but does not fail the run. */
  optional?: boolean;
}

const REQUIRED_NODE_MAJOR = 24;
const REQUIRED_NODE_MINOR = 12;

function checkNode(): CheckOutcome {
  const [majorText = "0", minorText = "0"] = process.versions.node.split(".");
  const major = Number.parseInt(majorText, 10);
  const minor = Number.parseInt(minorText, 10);
  const ok =
    major > REQUIRED_NODE_MAJOR ||
    (major === REQUIRED_NODE_MAJOR && minor >= REQUIRED_NODE_MINOR);
  return {
    name: "node_version",
    passed: ok,
    detail: ok
      ? `Node ${process.versions.node}`
      : `Node ${process.versions.node} е твърде стар. Трябва >= 24.12.0. ` +
        `В devcontainer-а това не би трябвало да се случи — ако сте извън него: ` +
        `nvm install 24.12.0 && nvm use 24.12.0`,
  };
}

function checkEnvFile(): CheckOutcome {
  const envPath = join(root, ".env");
  const ok = existsSync(envPath);
  return {
    name: "env_file_exists",
    passed: ok,
    detail: ok
      ? `Намерен: ${envPath}`
      : `Липсва ${envPath}. Изпълнете:  cp .env.example .env  и попълнете ключа.`,
  };
}

function checkKey(): CheckOutcome {
  const env = loadEnv(join(root, ".env"));
  if (env.apiKey === undefined) {
    return {
      name: "api_key_present",
      passed: false,
      detail:
        "OPENROUTER_API_KEY е празен. Вземете безплатен ключ от https://openrouter.ai/keys " +
        "(без карта) и го сложете в .env.",
    };
  }
  if (!looksLikeOpenRouterKey(env.apiKey)) {
    return {
      name: "api_key_present",
      passed: false,
      detail:
        `OPENROUTER_API_KEY не изглежда като ключ на OpenRouter (${maskKey(env.apiKey)}). ` +
        "Очакван формат: sk-or-v1-… . Проверете дали не сте копирали и кавички или интервал.",
    };
  }
  return {
    name: "api_key_present",
    passed: true,
    detail: `Ключ с валиден формат: ${maskKey(env.apiKey)}`,
  };
}

function checkSecretsIgnored(): CheckOutcome {
  const candidates = [join(repoRoot, ".gitignore"), join(root, ".gitignore")];
  const ignored = candidates.some((path) => {
    if (!existsSync(path)) return false;
    return readFileSync(path, "utf8")
      .split("\n")
      .map((line) => line.trim())
      .includes(".env");
  });
  return {
    name: "secrets_ignored",
    passed: ignored,
    detail: ignored
      ? ".env е в .gitignore"
      : "ВНИМАНИЕ: .env не е в .gitignore. Не комитвайте ключа си. Добавете ред `.env`.",
  };
}

function checkRecordedCall(): CheckOutcome {
  try {
    const run = loadRecording(join(root, "demo", "recordings", "hello-world.json"), "hello-world");
    const result = replay(run);
    const ok = result.text.trim().length > 0;
    return {
      name: "recorded_call_works",
      passed: ok,
      detail: ok
        ? `Записаният отговор се чете (${result.completionTokens} токена изход).`
        : "Записът се прочете, но е празен. Изтеглете хранилището наново.",
    };
  } catch (error) {
    return {
      name: "recorded_call_works",
      passed: false,
      detail:
        `Записът не може да се прочете: ${(error as Error).message}. ` +
        "Пуснете `git status` — най-вероятно файл в demo/recordings/ липсва или е променен.",
    };
  }
}

async function checkLiveCall(): Promise<CheckOutcome> {
  const env = loadEnv(join(root, ".env"));
  if (env.apiKey === undefined) {
    return {
      name: "live_call_works",
      passed: false,
      optional: true,
      detail: "Пропуснато: няма ключ.",
    };
  }
  try {
    const result = await chatLive({
      apiKey: env.apiKey,
      model: env.model,
      messages: [{ role: "user", content: "Отговори само с думата: готово" }],
      timeoutMs: 30_000,
    });
    return {
      name: "live_call_works",
      passed: true,
      detail: `Доставчикът отговори с ${result.completionTokens} токена от ${result.model}.`,
    };
  } catch (error) {
    return {
      name: "live_call_works",
      passed: false,
      detail:
        `Истинската заявка се провали: ${(error as Error).message}\n` +
        "    HTTP 401 → ключът е грешен или изтрит.\n" +
        "    HTTP 429 → изчерпан безплатен лимит; изчакайте минута и пробвайте пак.\n" +
        "    Мрежова грешка → проверете дали университетското прокси не блокира openrouter.ai.",
    };
  }
}

async function main(): Promise<void> {
  const live = process.argv.includes("--live");

  const outcomes: CheckOutcome[] = [
    checkNode(),
    checkEnvFile(),
    checkKey(),
    checkSecretsIgnored(),
    checkRecordedCall(),
  ];
  if (live) {
    outcomes.push(await checkLiveCall());
  }

  console.log("Проверка на средата за 00-setup\n");
  for (const outcome of outcomes) {
    const mark = outcome.passed ? "OK  " : outcome.optional === true ? "ПРОП" : "ГРЕШ";
    console.log(`[${mark}] ${outcome.name}`);
    console.log(`       ${outcome.detail.replaceAll("\n", "\n       ")}`);
  }

  const hardFailures = outcomes.filter((o) => !o.passed && o.optional !== true);
  console.log("");
  if (hardFailures.length === 0) {
    console.log("Всичко е наред. Следваща стъпка: `npm run demo`, после lecture 01-variance.");
    if (!live) {
      console.log("Ключът не е проверен срещу доставчика. За това: `npm run check:live`.");
    }
    return;
  }
  console.log(
    `${hardFailures.length} проверк${hardFailures.length === 1 ? "а се провали" : "и се провалиха"}: ` +
      hardFailures.map((o) => o.name).join(", "),
  );
  console.log("Оправете ги отгоре надолу — долните обикновено зависят от горните.");
  process.exitCode = 1;
}

await main();
