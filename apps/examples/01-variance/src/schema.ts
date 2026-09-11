/**
 * Schema extraction and diffing for lecture 1.
 *
 * The point of the lecture: the same prompt, sent ten times, does not produce the
 * same *shape*. To show that we need a canonical description of a shape, and a way
 * to compare two of them.
 */

export type JsonValue =
  | null
  | boolean
  | number
  | string
  | JsonValue[]
  | { [key: string]: JsonValue };

/** Leaf type names, plus the two container names. */
export type TypeName =
  | "null"
  | "boolean"
  | "number"
  | "string"
  | "array"
  | "object";

export function typeOf(value: JsonValue): TypeName {
  if (value === null) return "null";
  if (Array.isArray(value)) return "array";
  switch (typeof value) {
    case "boolean":
      return "boolean";
    case "number":
      return "number";
    case "string":
      return "string";
    default:
      return "object";
  }
}

/**
 * Flattens a value into `path -> type` pairs. Array indices collapse to `[]`, so
 * `genres[0]` and `genres[1]` are the same path: we care about the shape, not the
 * length. Types seen at the same path are unioned, e.g. `string|number`.
 */
export function flatten(value: JsonValue): Map<string, string> {
  const out = new Map<string, string>();

  const add = (path: string, type: TypeName): void => {
    const existing = out.get(path);
    if (existing === undefined) {
      out.set(path, type);
      return;
    }
    const parts = new Set(existing.split("|"));
    parts.add(type);
    out.set(path, [...parts].sort().join("|"));
  };

  const walk = (node: JsonValue, path: string): void => {
    const type = typeOf(node);
    add(path, type);
    if (type === "object") {
      for (const [key, child] of Object.entries(node as Record<string, JsonValue>)) {
        walk(child, path === "$" ? `$.${key}` : `${path}.${key}`);
      }
    } else if (type === "array") {
      for (const child of node as JsonValue[]) {
        walk(child, `${path}[]`);
      }
    }
  };

  walk(value, "$");
  return out;
}

/** A stable, comparable string for one shape. Equal signatures mean equal shapes. */
export function signature(value: JsonValue): string {
  return [...flatten(value)]
    .sort(([a], [b]) => (a < b ? -1 : a > b ? 1 : 0))
    .map(([path, type]) => `${path}:${type}`)
    .join("\n");
}

export interface FieldStability {
  path: string;
  /** How many of the runs contained this path at all. */
  present: number;
  /** Distinct type strings observed, sorted. */
  types: string[];
}

export interface VarianceReport {
  totalRuns: number;
  /** Runs whose output could not be parsed as JSON at all. */
  unparsable: number;
  /** Number of distinct signatures among the parsed runs. */
  distinctSchemas: number;
  /** Signature -> indices of the runs that produced it. */
  groups: Map<string, number[]>;
  fields: FieldStability[];
}

export interface RunOutcome {
  index: number;
  parsed: JsonValue | undefined;
}

export function analyse(outcomes: RunOutcome[]): VarianceReport {
  const groups = new Map<string, number[]>();
  const fieldTypes = new Map<string, Set<string>>();
  const fieldPresence = new Map<string, number>();
  let unparsable = 0;
  let parsedCount = 0;

  for (const outcome of outcomes) {
    if (outcome.parsed === undefined) {
      unparsable += 1;
      continue;
    }
    parsedCount += 1;
    const sig = signature(outcome.parsed);
    const bucket = groups.get(sig);
    if (bucket === undefined) groups.set(sig, [outcome.index]);
    else bucket.push(outcome.index);

    for (const [path, type] of flatten(outcome.parsed)) {
      if (path === "$") continue;
      fieldPresence.set(path, (fieldPresence.get(path) ?? 0) + 1);
      const set = fieldTypes.get(path) ?? new Set<string>();
      set.add(type);
      fieldTypes.set(path, set);
    }
  }

  const fields: FieldStability[] = [...fieldPresence.entries()]
    .map(([path, present]) => ({
      path,
      present,
      types: [...(fieldTypes.get(path) ?? new Set<string>())].sort(),
    }))
    .sort((a, b) => b.present - a.present || (a.path < b.path ? -1 : 1));

  return {
    totalRuns: outcomes.length,
    unparsable,
    distinctSchemas: groups.size,
    groups,
    fields,
  };
}

/** True when a field appeared in every parsed run with exactly one type. */
export function isStable(field: FieldStability, parsedRuns: number): boolean {
  return field.present === parsedRuns && field.types.length === 1;
}

/**
 * Models wrap JSON in prose or in a ```json fence often enough that stripping it is
 * part of the lesson, not a trick. Returns undefined when nothing parses — which is
 * itself a result worth counting.
 */
export function extractJson(text: string): JsonValue | undefined {
  const candidates: string[] = [text.trim()];

  const fence = /```(?:json)?\s*([\s\S]*?)```/i.exec(text);
  if (fence?.[1] !== undefined) candidates.push(fence[1].trim());

  const firstBrace = text.indexOf("{");
  const lastBrace = text.lastIndexOf("}");
  if (firstBrace !== -1 && lastBrace > firstBrace) {
    candidates.push(text.slice(firstBrace, lastBrace + 1));
  }

  for (const candidate of candidates) {
    try {
      return JSON.parse(candidate) as JsonValue;
    } catch {
      // try the next candidate
    }
  }
  return undefined;
}
