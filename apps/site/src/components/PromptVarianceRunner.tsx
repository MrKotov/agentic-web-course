import { useCallback, useEffect, useMemo, useRef, useState } from 'react';
import {
  PROMPT_VARIANCE_FIXTURE,
  type RecordedRun,
  type VarianceFixture,
} from '../data/prompt-variance';
import { analyse, type AnalysedRun, type RunInput, type ShapeKind } from './lib/json-shape';
import { DEFAULT_ENDPOINT, runOnce } from './lib/live-provider';
import { useLocalSetting } from './lib/use-api-key';
import { Badge } from './ui/badge';
import { Button } from './ui/button';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from './ui/card';
import { Separator } from './ui/separator';
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from './ui/table';
import { Tabs, TabsList, TabsTrigger } from './ui/tabs';

type Mode = 'recorded' | 'live';
type Phase = 'idle' | 'running' | 'done';

interface Props {
  /** Override the fixture; defaults to the lecture 1 job-ad extraction recording. */
  readonly fixture?: VarianceFixture;
  /** Allow the live path at all. Recorded mode always works. */
  readonly allowLive?: boolean;
}

const KIND_LABEL: Record<ShapeKind, string> = {
  string: 'str',
  number: 'num',
  boolean: 'bool',
  null: 'null',
  object: 'obj',
  'array<empty>': '[]',
  'array<string>': '[str]',
  'array<number>': '[num]',
  'array<object>': '[obj]',
  'array<mixed>': '[mix]',
};

function toRunInput(run: RecordedRun): RunInput {
  return {
    index: run.index,
    raw: run.raw,
    latencyMs: run.latencyMs,
    completionTokens: run.completionTokens,
  };
}

export default function PromptVarianceRunner({
  fixture = PROMPT_VARIANCE_FIXTURE,
  allowLive = true,
}: Props): React.ReactElement {
  const [mode, setMode] = useState<Mode>('recorded');
  const [phase, setPhase] = useState<Phase>('idle');
  const [visible, setVisible] = useState(0);
  const [liveRuns, setLiveRuns] = useState<readonly RunInput[]>([]);
  const [liveError, setLiveError] = useState<string | null>(null);
  const [showPrompt, setShowPrompt] = useState(false);
  const [selected, setSelected] = useState<number | null>(null);
  const abortRef = useRef<AbortController | null>(null);
  const timersRef = useRef<number[]>([]);

  const apiKey = useLocalSetting('apiKey');
  const endpoint = useLocalSetting('endpoint', DEFAULT_ENDPOINT);
  const model = useLocalSetting('model', 'openai/gpt-oss-20b:free');

  const runCount = mode === 'recorded' ? fixture.runs.length : 10;

  const sourceRuns: readonly RunInput[] = useMemo(
    () => (mode === 'recorded' ? fixture.runs.map(toRunInput) : liveRuns),
    [mode, fixture, liveRuns],
  );

  const shown = useMemo(() => sourceRuns.slice(0, visible), [sourceRuns, visible]);
  const { runs, summary } = useMemo(() => analyse(shown), [shown]);

  const clearTimers = useCallback(() => {
    for (const id of timersRef.current) window.clearTimeout(id);
    timersRef.current = [];
  }, []);

  useEffect(() => () => {
    clearTimers();
    abortRef.current?.abort();
  }, [clearTimers]);

  const reset = useCallback(() => {
    clearTimers();
    abortRef.current?.abort();
    abortRef.current = null;
    setPhase('idle');
    setVisible(0);
    setSelected(null);
    setLiveError(null);
    setLiveRuns([]);
  }, [clearTimers]);

  /** Recorded mode: replay the committed runs one by one so the drift accumulates on screen. */
  const startRecorded = useCallback(() => {
    clearTimers();
    setPhase('running');
    setVisible(0);
    setSelected(null);
    fixture.runs.forEach((_, i) => {
      const id = window.setTimeout(() => {
        setVisible(i + 1);
        if (i === fixture.runs.length - 1) setPhase('done');
      }, 260 * (i + 1));
      timersRef.current.push(id);
    });
  }, [fixture, clearTimers]);

  /** Live mode: the viewer's own key, browser-direct, sequential so rate limits are visible. */
  const startLive = useCallback(async () => {
    const controller = new AbortController();
    abortRef.current = controller;
    setPhase('running');
    setVisible(0);
    setSelected(null);
    setLiveError(null);
    setLiveRuns([]);
    const collected: RunInput[] = [];
    try {
      for (let i = 0; i < runCount; i += 1) {
        const result = await runOnce(
          {
            endpoint: endpoint.value || DEFAULT_ENDPOINT,
            model: model.value,
            apiKey: apiKey.value,
            temperature: fixture.temperature,
          },
          fixture.systemPrompt,
          fixture.userPrompt,
          controller.signal,
        );
        collected.push({
          index: i + 1,
          raw: result.content,
          latencyMs: result.latencyMs,
          completionTokens: result.completionTokens,
        });
        setLiveRuns([...collected]);
        setVisible(collected.length);
      }
      setPhase('done');
    } catch (error) {
      if (controller.signal.aborted) return;
      setLiveError(
        error instanceof Error ? error.message : 'Заявката не успя. Вероятна причина: CORS или лимит.',
      );
      setPhase('done');
    }
  }, [runCount, endpoint.value, model.value, apiKey.value, fixture]);

  const canRunLive = mode === 'live' && apiKey.value.trim().length > 0 && model.value.trim().length > 0;
  const running = phase === 'running';

  return (
    <Card
      className="my-7 gap-5 py-6"
      aria-label="Разсейване на отговорите при един и същ промпт"
    >
      <CardHeader className="gap-3 px-6">
        <div className="flex flex-wrap items-center justify-between gap-3">
          <CardTitle className="text-base font-semibold sm:text-lg">
            Един промпт, {runCount} изпълнения
          </CardTitle>
          <Tabs
            value={mode}
            onValueChange={(value) => {
              reset();
              setMode(value as Mode);
            }}
          >
            <TabsList aria-label="Режим">
              <TabsTrigger value="recorded">Записан режим</TabsTrigger>
              {allowLive && <TabsTrigger value="live">На живо (със свой ключ)</TabsTrigger>}
            </TabsList>
          </Tabs>
        </div>
        <CardDescription className="text-sm leading-relaxed text-muted-foreground">
          {mode === 'recorded' ? (
            <>
              Записани отговори от {fixture.recordedAt} — работи без ключ и без мрежа. Модел:{' '}
              <span className="course-mono">{fixture.model}</span>, temperature{' '}
              {fixture.temperature}.
            </>
          ) : (
            <>
              Ключът остава в браузъра ви (<span className="course-mono">localStorage</span>) и се
              изпраща директно към доставчика. Този сайт не го препраща и не го записва.
            </>
          )}
        </CardDescription>
      </CardHeader>

      <CardContent className="flex flex-col gap-5 px-6">
        <div>
          <Button type="button" variant="outline" size="sm" onClick={() => setShowPrompt((v) => !v)}>
            {showPrompt ? 'Скрий промпта' : 'Покажи промпта'}
          </Button>
          {showPrompt && (
            <div className="mt-3 grid gap-2">
              <p className="course-note">system</p>
              <pre className="max-w-full overflow-x-auto rounded-lg border border-border bg-muted p-3 text-sm">
                {fixture.systemPrompt}
              </pre>
              <p className="course-note">user</p>
              <pre className="max-w-full overflow-x-auto rounded-lg border border-border bg-muted p-3 text-sm">
                {fixture.userPrompt}
              </pre>
            </div>
          )}
        </div>

        {mode === 'live' && (
          <div className="grid gap-3 rounded-lg border border-border bg-muted/40 p-4">
            <p
              className="rounded-lg border border-warning bg-warning/10 px-3.5 py-3 text-sm text-foreground"
              role="note"
            >
              <strong>Непроверено:</strong> извикванията директно от браузъра зависят от CORS
              политиката на доставчика. Това още не е потвърдено за доставчика на курса — вижте
              „Инструменти и ключове“. Ако не сработи, записаният режим е официалният път.
            </p>
            <label className="grid gap-1.5 text-sm">
              <span className="font-medium">API ключ</span>
              <input
                className="h-10 rounded-lg border border-input bg-background px-3 text-sm outline-none focus-visible:ring-3 focus-visible:ring-ring/50"
                type="password"
                autoComplete="off"
                spellCheck={false}
                value={apiKey.value}
                placeholder="sk-..."
                onChange={(event) => apiKey.setValue(event.target.value)}
              />
            </label>
            <label className="grid gap-1.5 text-sm">
              <span className="font-medium">Модел</span>
              <input
                className="h-10 rounded-lg border border-input bg-background px-3 text-sm outline-none focus-visible:ring-3 focus-visible:ring-ring/50"
                type="text"
                spellCheck={false}
                value={model.value}
                onChange={(event) => model.setValue(event.target.value)}
              />
            </label>
            <label className="grid gap-1.5 text-sm">
              <span className="font-medium">Endpoint</span>
              <input
                className="h-10 rounded-lg border border-input bg-background px-3 text-sm outline-none focus-visible:ring-3 focus-visible:ring-ring/50"
                type="url"
                spellCheck={false}
                value={endpoint.value}
                onChange={(event) => endpoint.setValue(event.target.value)}
              />
            </label>
            <div>
              <Button type="button" variant="outline" size="sm" onClick={apiKey.clear}>
                Изтрий ключа от браузъра
              </Button>
            </div>
          </div>
        )}

        <div className="flex flex-wrap items-center gap-3">
          <Button
            type="button"
            variant="cta"
            disabled={running || (mode === 'live' && !canRunLive)}
            onClick={() => {
              if (mode === 'recorded') startRecorded();
              else void startLive();
            }}
          >
            {running ? 'Изпълнява се…' : `Стартирай ${runCount} изпълнения`}
          </Button>
          <Button type="button" variant="outline" onClick={reset} disabled={phase === 'idle'}>
            Изчисти
          </Button>
          {mode === 'live' && !canRunLive && (
            <span className="course-note">Въведете ключ и модел, за да стартирате.</span>
          )}
        </div>

        {liveError && (
          <p
            className="rounded-lg border border-destructive bg-destructive/10 px-3.5 py-3 text-sm text-destructive"
            role="alert"
          >
            Грешка: <span className="course-mono">{liveError}</span>
          </p>
        )}

        {visible > 0 && (
          <>
            <Separator />

            <dl className="grid grid-cols-[repeat(auto-fit,minmax(9rem,1fr))] gap-3">
              <Stat label="Изпълнения" value={String(summary.totalRuns)} />
              <Stat
                label="Различни схеми"
                value={String(summary.distinctSchemas)}
                tone={summary.distinctSchemas > 1 ? 'bad' : 'ok'}
              />
              <Stat
                label="Невалиден JSON"
                value={String(summary.failedRuns)}
                tone={summary.failedRuns > 0 ? 'bad' : 'ok'}
              />
              <Stat
                label="С обвивка (текст/фенс)"
                value={String(summary.wrappedRuns)}
                tone={summary.wrappedRuns > 0 ? 'warn' : 'ok'}
              />
              <Stat
                label="Полета във всички"
                value={`${summary.stablePaths.length} / ${summary.fields.length}`}
                tone={summary.unstablePaths.length > 0 ? 'warn' : 'ok'}
              />
              <Stat
                label="Конфликт в типа"
                value={String(summary.conflictingPaths.length)}
                tone={summary.conflictingPaths.length > 0 ? 'bad' : 'ok'}
              />
            </dl>

            <div>
              <h4 className="mb-1 text-base font-semibold">Полета по изпълнение</h4>
              <p className="course-note mb-3">
                Ред = път в JSON. Колона = изпълнение. Празна клетка означава, че полето изобщо
                липсва в този отговор.
              </p>
              <div className="max-w-full overflow-auto max-h-[26rem] rounded-lg border border-border">
                <Table className="text-center">
                  <caption className="sr-only">Матрица на полетата спрямо изпълненията</caption>
                  <TableHeader className="sticky top-0 z-10 bg-card">
                    <TableRow className="hover:bg-transparent">
                      <TableHead className="sticky left-0 z-20 bg-card text-left">път</TableHead>
                      {runs.map((run) => (
                        <TableHead
                          key={run.index}
                          className="text-center"
                          title={`Изпълнение ${run.index}`}
                        >
                          {run.index}
                        </TableHead>
                      ))}
                    </TableRow>
                  </TableHeader>
                  <TableBody>
                    {summary.fields.map((field, rowIndex) => {
                      const conflicting = field.kinds.length > 1;
                      return (
                        <TableRow
                          key={field.path}
                          className={
                            rowIndex % 2 === 1 ? 'bg-muted/30 hover:bg-muted/40' : undefined
                          }
                        >
                          <TableCell
                            className={
                              'course-mono sticky left-0 z-10 bg-card text-left font-medium' +
                              (conflicting ? ' text-destructive' : '')
                            }
                          >
                            {field.path}
                          </TableCell>
                          {runs.map((run) => {
                            const kind = run.shape.get(field.path);
                            return (
                              <TableCell
                                key={run.index}
                                className={
                                  kind
                                    ? conflicting
                                      ? 'bg-destructive/10 text-center font-semibold text-destructive'
                                      : 'text-center'
                                    : 'text-center text-muted-foreground/60'
                                }
                                title={kind ? `${field.path}: ${kind}` : `${field.path}: липсва`}
                              >
                                {kind ? KIND_LABEL[kind] : '—'}
                              </TableCell>
                            );
                          })}
                        </TableRow>
                      );
                    })}
                  </TableBody>
                </Table>
              </div>
            </div>

            <div>
              <h4 className="mb-3 text-base font-semibold">Отговорите едно до друго</h4>
              <div className="max-w-full overflow-x-auto flex gap-3 pb-2">
                {runs.map((run) => (
                  <RunCard
                    key={run.index}
                    run={run}
                    open={selected === run.index}
                    onToggle={() => setSelected(selected === run.index ? null : run.index)}
                  />
                ))}
              </div>
            </div>
          </>
        )}
      </CardContent>
    </Card>
  );
}

const STAT_TONE_CLASS: Record<'ok' | 'warn' | 'bad', string> = {
  ok: 'text-success',
  warn: 'text-warning',
  bad: 'text-destructive',
};

function Stat({
  label,
  value,
  tone,
}: {
  readonly label: string;
  readonly value: string;
  readonly tone?: 'ok' | 'warn' | 'bad';
}): React.ReactElement {
  return (
    <div className="rounded-lg border border-border bg-card px-3.5 py-3 shadow-sm">
      <dt className="course-note text-xs">{label}</dt>
      <dd className={'text-2xl font-bold ' + (tone ? STAT_TONE_CLASS[tone] : 'text-foreground')}>
        {value}
      </dd>
    </div>
  );
}

const RUN_BORDER_TONE_CLASS: Record<'ok' | 'warn' | 'bad', string> = {
  ok: 'border-l-success',
  warn: 'border-l-warning',
  bad: 'border-l-destructive',
};

function RunCard({
  run,
  open,
  onToggle,
}: {
  readonly run: AnalysedRun;
  readonly open: boolean;
  readonly onToggle: () => void;
}): React.ReactElement {
  const tone: 'ok' | 'warn' | 'bad' = !run.parsed ? 'bad' : run.hadWrapper || run.schemaId !== 1 ? 'warn' : 'ok';

  return (
    <Card
      className={
        'min-w-60 flex-none gap-2.5 border-l-4 px-0.5 py-4 shadow-sm transition-shadow hover:shadow-md ' +
        RUN_BORDER_TONE_CLASS[tone] +
        (open ? ' max-w-[32rem]' : ' max-w-80')
      }
    >
      <CardHeader className="flex-row flex-wrap items-center gap-1.5 px-4">
        <strong className="text-sm">#{run.index}</strong>
        {run.parsed ? (
          <Badge variant={run.schemaId === 1 ? 'ok' : 'warn'}>схема {run.schemaId}</Badge>
        ) : (
          <Badge variant="destructive">не се парсва</Badge>
        )}
        {run.hadWrapper && <Badge variant="warn">обвивка</Badge>}
      </CardHeader>
      <CardContent className="flex flex-col gap-2.5 px-4">
        <p className="course-note">
          {run.latencyMs} ms · {run.completionTokens} токена · {run.shape.size} полета
        </p>
        {run.error && (
          <p className="course-mono rounded-md bg-destructive/10 px-2 py-1.5 text-sm text-destructive">
            {run.error}
          </p>
        )}
        <div>
          <Button type="button" variant="outline" size="sm" onClick={onToggle}>
            {open ? 'Скрий отговора' : 'Покажи отговора'}
          </Button>
        </div>
        {open && (
          <pre className="max-h-80 overflow-auto rounded-md bg-muted p-2.5 text-sm break-words whitespace-pre-wrap">
            {run.raw}
          </pre>
        )}
      </CardContent>
    </Card>
  );
}
