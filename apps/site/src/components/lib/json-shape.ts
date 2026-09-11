/**
 * Turning a returned blob of text into a comparable schema signature.
 * Used by the prompt variance runner to show that ten runs of one prompt produce
 * more than one shape.
 */

export type JsonValue =
  | string
  | number
  | boolean
  | null
  | readonly JsonValue[]
  | { readonly [key: string]: JsonValue };

export type ShapeKind =
  | 'string'
  | 'number'
  | 'boolean'
  | 'null'
  | 'object'
  | 'array<empty>'
  | 'array<string>'
  | 'array<number>'
  | 'array<object>'
  | 'array<mixed>';

export interface ExtractResult {
  readonly ok: boolean;
  /** Present when ok. */
  readonly value?: JsonValue;
  /** Present when !ok. */
  readonly error?: string;
  /** True when the model wrapped the JSON in prose or a markdown fence. */
  readonly hadWrapper: boolean;
}

/**
 * Pull JSON out of a model response. Models fence it, prefix it with prose, or both,
 * so a bare JSON.parse is not enough — which is itself part of the lesson.
 */
export function extractJson(raw: string): ExtractResult {
  const trimmed = raw.trim();
  const direct = tryParse(trimmed);
  if (direct.ok) return { ...direct, hadWrapper: false };

  const fenced = /```(?:json|JSON)?\s*([\s\S]*?)```/.exec(trimmed);
  if (fenced?.[1]) {
    const parsed = tryParse(fenced[1].trim());
    if (parsed.ok) return { ...parsed, hadWrapper: true };
  }

  const firstBrace = trimmed.search(/[[{]/);
  const lastBrace = Math.max(trimmed.lastIndexOf('}'), trimmed.lastIndexOf(']'));
  if (firstBrace >= 0 && lastBrace > firstBrace) {
    const parsed = tryParse(trimmed.slice(firstBrace, lastBrace + 1));
    if (parsed.ok) return { ...parsed, hadWrapper: true };
  }

  return { ok: false, error: direct.error ?? 'Невалиден JSON', hadWrapper: false };
}

function tryParse(text: string): { ok: boolean; value?: JsonValue; error?: string } {
  try {
    return { ok: true, value: JSON.parse(text) as JsonValue };
  } catch (error) {
    return { ok: false, error: error instanceof Error ? error.message : String(error) };
  }
}

export function kindOf(value: JsonValue): ShapeKind {
  if (value === null) return 'null';
  if (Array.isArray(value)) {
    if (value.length === 0) return 'array<empty>';
    const kinds = new Set(value.map((item) => (Array.isArray(item) ? 'object' : typeof item === 'object' && item !== null ? 'object' : typeof item)));
    if (kinds.size > 1) return 'array<mixed>';
    const only = [...kinds][0];
    if (only === 'string') return 'array<string>';
    if (only === 'number') return 'array<number>';
    if (only === 'object') return 'array<object>';
    return 'array<mixed>';
  }
  if (typeof value === 'object') return 'object';
  if (typeof value === 'string') return 'string';
  if (typeof value === 'number') return 'number';
  if (typeof value === 'boolean') return 'boolean';
  return 'null';
}

/** `field.path` -> kind, with array element objects flattened under `[]`. */
export type ShapeMap = ReadonlyMap<string, ShapeKind>;

export function shapeOf(value: JsonValue): ShapeMap {
  const out = new Map<string, ShapeKind>();
  walk(value, '', out, 0);
  return out;
}

function walk(value: JsonValue, path: string, out: Map<string, ShapeKind>, depth: number): void {
  if (depth > 6) return;
  const kind = kindOf(value);
  if (path !== '') out.set(path, kind);

  if (kind === 'object' && value !== null && !Array.isArray(value)) {
    for (const [key, child] of Object.entries(value as Record<string, JsonValue>)) {
      walk(child, path === '' ? key : `${path}.${key}`, out, depth + 1);
    }
    return;
  }
  if (kind === 'array<object>' && Array.isArray(value)) {
    const first = value[0];
    if (first !== undefined) walk(first, `${path}[]`, out, depth + 1);
  }
}

/** Stable text signature used to count how many *distinct* schemas came back. */
export function signatureOf(shape: ShapeMap): string {
  return [...shape.entries()]
    .map(([path, kind]) => `${path}:${kind}`)
    .sort()
    .join('|');
}

export interface FieldStat {
  readonly path: string;
  /** Run indexes in which this path appeared. */
  readonly presentIn: readonly number[];
  /** Distinct kinds seen for this path. More than one means a type conflict. */
  readonly kinds: readonly ShapeKind[];
}

export interface DiffSummary {
  readonly totalRuns: number;
  readonly parsedRuns: number;
  readonly failedRuns: number;
  readonly wrappedRuns: number;
  readonly distinctSchemas: number;
  /** Paths present in every run that parsed. */
  readonly stablePaths: readonly string[];
  /** Paths present in some runs but not all. */
  readonly unstablePaths: readonly string[];
  /** Paths whose type changed between runs. */
  readonly conflictingPaths: readonly string[];
  readonly fields: readonly FieldStat[];
}

export interface AnalysedRun {
  readonly index: number;
  readonly raw: string;
  readonly latencyMs: number;
  readonly completionTokens: number;
  readonly parsed: boolean;
  readonly hadWrapper: boolean;
  readonly error?: string;
  readonly shape: ShapeMap;
  readonly signature: string;
  /** 1-based id of the distinct schema this run belongs to, or null when it did not parse. */
  readonly schemaId: number | null;
}

export interface RunInput {
  readonly index: number;
  readonly raw: string;
  readonly latencyMs: number;
  readonly completionTokens: number;
}

export function analyse(runs: readonly RunInput[]): {
  readonly runs: readonly AnalysedRun[];
  readonly summary: DiffSummary;
} {
  const signatures = new Map<string, number>();
  const analysed: AnalysedRun[] = runs.map((run) => {
    const extracted = extractJson(run.raw);
    if (!extracted.ok || extracted.value === undefined) {
      return {
        index: run.index,
        raw: run.raw,
        latencyMs: run.latencyMs,
        completionTokens: run.completionTokens,
        parsed: false,
        hadWrapper: extracted.hadWrapper,
        error: extracted.error ?? 'Невалиден JSON',
        shape: new Map<string, ShapeKind>(),
        signature: '',
        schemaId: null,
      };
    }
    const shape = shapeOf(extracted.value);
    const signature = signatureOf(shape);
    if (!signatures.has(signature)) signatures.set(signature, signatures.size + 1);
    return {
      index: run.index,
      raw: run.raw,
      latencyMs: run.latencyMs,
      completionTokens: run.completionTokens,
      parsed: true,
      hadWrapper: extracted.hadWrapper,
      shape,
      signature,
      schemaId: signatures.get(signature) ?? null,
    };
  });

  const parsedRuns = analysed.filter((run) => run.parsed);
  const paths = new Map<string, { presentIn: number[]; kinds: Set<ShapeKind> }>();
  for (const run of parsedRuns) {
    for (const [path, kind] of run.shape) {
      const entry = paths.get(path) ?? { presentIn: [], kinds: new Set<ShapeKind>() };
      entry.presentIn.push(run.index);
      entry.kinds.add(kind);
      paths.set(path, entry);
    }
  }

  const fields: FieldStat[] = [...paths.entries()]
    .map(([path, entry]) => ({ path, presentIn: entry.presentIn, kinds: [...entry.kinds] }))
    .sort((a, b) => b.presentIn.length - a.presentIn.length || a.path.localeCompare(b.path));

  const stablePaths = fields.filter((f) => f.presentIn.length === parsedRuns.length).map((f) => f.path);
  const unstablePaths = fields.filter((f) => f.presentIn.length < parsedRuns.length).map((f) => f.path);
  const conflictingPaths = fields.filter((f) => f.kinds.length > 1).map((f) => f.path);

  return {
    runs: analysed,
    summary: {
      totalRuns: analysed.length,
      parsedRuns: parsedRuns.length,
      failedRuns: analysed.length - parsedRuns.length,
      wrappedRuns: analysed.filter((run) => run.hadWrapper).length,
      distinctSchemas: signatures.size,
      stablePaths,
      unstablePaths,
      conflictingPaths,
      fields,
    },
  };
}
