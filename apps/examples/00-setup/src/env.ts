/**
 * Minimal .env reader. No dependency, on purpose: the first thing a student runs
 * must not require a successful `npm install`.
 */
import { readFileSync } from "node:fs";

export type CourseMode = "recorded" | "live";

export interface CourseEnv {
  apiKey: string | undefined;
  model: string;
  mode: CourseMode;
  envFileFound: boolean;
}

/** Parses KEY=VALUE lines. Ignores blanks, comments and malformed lines. */
export function parseDotenv(text: string): Record<string, string> {
  const out: Record<string, string> = {};
  for (const rawLine of text.split("\n")) {
    const line = rawLine.trim();
    if (line.length === 0 || line.startsWith("#")) continue;
    const eq = line.indexOf("=");
    if (eq <= 0) continue;
    const key = line.slice(0, eq).trim();
    let value = line.slice(eq + 1).trim();
    if (
      (value.startsWith('"') && value.endsWith('"')) ||
      (value.startsWith("'") && value.endsWith("'"))
    ) {
      value = value.slice(1, -1);
    }
    out[key] = value;
  }
  return out;
}

function readEnvFile(path: string): Record<string, string> | undefined {
  try {
    return parseDotenv(readFileSync(path, "utf8"));
  } catch {
    return undefined;
  }
}

export const DEFAULT_MODEL = "meta-llama/llama-3.3-70b-instruct:free";

export function loadEnv(envPath: string): CourseEnv {
  const fromFile = readEnvFile(envPath);
  const merged: Record<string, string | undefined> = {
    ...(fromFile ?? {}),
    // A real environment variable always wins over the file. CI sets them this way.
    ...Object.fromEntries(
      Object.entries(process.env).filter(([, v]) => v !== undefined && v !== ""),
    ),
  };

  const rawKey = merged["OPENROUTER_API_KEY"];
  const rawMode = merged["COURSE_MODE"];

  return {
    apiKey: rawKey !== undefined && rawKey.length > 0 ? rawKey : undefined,
    model: merged["OPENROUTER_MODEL"] ?? DEFAULT_MODEL,
    mode: rawMode === "live" ? "live" : "recorded",
    envFileFound: fromFile !== undefined,
  };
}

/**
 * Shape check only. We never print the key and we never validate it against the
 * provider unless the student explicitly asks for a live run.
 */
export function looksLikeOpenRouterKey(key: string): boolean {
  return /^sk-or-v1-[A-Za-z0-9]{16,}$/.test(key);
}

/** Renders a key so it can be shown in a terminal without leaking it. */
export function maskKey(key: string): string {
  if (key.length <= 12) return "*".repeat(key.length);
  return `${key.slice(0, 10)}…${"*".repeat(6)}${key.slice(-4)}`;
}
