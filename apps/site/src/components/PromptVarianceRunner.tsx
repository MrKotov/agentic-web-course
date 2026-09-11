import { useCallback, useEffect, useMemo, useRef, useState } from 'react';
import {
  PROMPT_VARIANCE_FIXTURE,
  type RecordedRun,
  type VarianceFixture,
} from '../data/prompt-variance';
import { analyse, type AnalysedRun, type RunInput, type ShapeKind } from './lib/json-shape';
import { DEFAULT_ENDPOINT, runOnce } from './lib/live-provider';
import { useLocalSetting } from './lib/use-api-key';

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
    <section className="course-panel pv" aria-label="Разсейване на отговорите при един и същ промпт">
      <header className="course-panel__head">
        <h3 className="course-panel__title">Един промпт, {runCount} изпълнения</h3>
        <div className="course-controls" role="group" aria-label="Режим">
          <button
            type="button"
            className="course-btn"
            aria-pressed={mode === 'recorded'}
            data-variant={mode === 'recorded' ? 'primary' : undefined}
            onClick={() => {
              reset();
              setMode('recorded');
            }}
          >
            Записан режим
          </button>
          {allowLive && (
            <button
              type="button"
              className="course-btn"
              aria-pressed={mode === 'live'}
              data-variant={mode === 'live' ? 'primary' : undefined}
              onClick={() => {
                reset();
                setMode('live');
              }}
            >
              На живо (със свой ключ)
            </button>
          )}
        </div>
      </header>

      <p className="course-note">
        {mode === 'recorded' ? (
          <>
            Записани отговори от {fixture.recordedAt} — работи без ключ и без мрежа. Модел:{' '}
            <span className="course-mono">{fixture.model}</span>, temperature {fixture.temperature}.
          </>
        ) : (
          <>
            Ключът остава в браузъра ви (<span className="course-mono">localStorage</span>) и се
            изпраща директно към доставчика. Този сайт не го препраща и не го записва.
          </>
        )}
      </p>

      <div className="pv__prompt">
        <button type="button" className="course-btn" onClick={() => setShowPrompt((v) => !v)}>
          {showPrompt ? 'Скрий промпта' : 'Покажи промпта'}
        </button>
        {showPrompt && (
          <div className="pv__promptBody">
            <p className="course-note">system</p>
            <pre className="course-scroll-x">{fixture.systemPrompt}</pre>
            <p className="course-note">user</p>
            <pre className="course-scroll-x">{fixture.userPrompt}</pre>
          </div>
        )}
      </div>

      {mode === 'live' && (
        <div className="pv__live">
          <p className="pv__warn" role="note">
            <strong>Непроверено:</strong> извикванията директно от браузъра зависят от CORS
            политиката на доставчика. Това още не е потвърдено за доставчика на курса — вижте
            „Инструменти и ключове“. Ако не сработи, записаният режим е официалният път.
          </p>
          <label className="pv__field">
            <span>API ключ</span>
            <input
              className="course-input"
              type="password"
              autoComplete="off"
              spellCheck={false}
              value={apiKey.value}
              placeholder="sk-..."
              onChange={(event) => apiKey.setValue(event.target.value)}
            />
          </label>
          <label className="pv__field">
            <span>Модел</span>
            <input
              className="course-input"
              type="text"
              spellCheck={false}
              value={model.value}
              onChange={(event) => model.setValue(event.target.value)}
            />
          </label>
          <label className="pv__field">
            <span>Endpoint</span>
            <input
              className="course-input"
              type="url"
              spellCheck={false}
              value={endpoint.value}
              onChange={(event) => endpoint.setValue(event.target.value)}
            />
          </label>
          <div className="course-controls">
            <button type="button" className="course-btn" onClick={apiKey.clear}>
              Изтрий ключа от браузъра
            </button>
          </div>
        </div>
      )}

      <div className="course-controls pv__actions">
        <button
          type="button"
          className="course-btn"
          data-variant="primary"
          disabled={running || (mode === 'live' && !canRunLive)}
          onClick={() => {
            if (mode === 'recorded') startRecorded();
            else void startLive();
          }}
        >
          {running ? 'Изпълнява се…' : `Стартирай ${runCount} изпълнения`}
        </button>
        <button type="button" className="course-btn" onClick={reset} disabled={phase === 'idle'}>
          Изчисти
        </button>
        {mode === 'live' && !canRunLive && (
          <span className="course-note">Въведете ключ и модел, за да стартирате.</span>
        )}
      </div>

      {liveError && (
        <p className="pv__error" role="alert">
          Грешка: <span className="course-mono">{liveError}</span>
        </p>
      )}

      {visible > 0 && (
        <>
          <dl className="pv__summary">
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

          <h4 className="pv__h">Полета по изпълнение</h4>
          <p className="course-note">
            Ред = път в JSON. Колона = изпълнение. Празна клетка означава, че полето изобщо
            липсва в този отговор.
          </p>
          <div className="course-scroll-x pv__matrixWrap">
            <table className="pv__matrix">
              <caption className="pv__srOnly">
                Матрица на полетата спрямо изпълненията
              </caption>
              <thead>
                <tr>
                  <th scope="col">път</th>
                  {runs.map((run) => (
                    <th key={run.index} scope="col" title={`Изпълнение ${run.index}`}>
                      {run.index}
                    </th>
                  ))}
                </tr>
              </thead>
              <tbody>
                {summary.fields.map((field) => {
                  const conflicting = field.kinds.length > 1;
                  return (
                    <tr key={field.path} data-conflict={conflicting || undefined}>
                      <th scope="row" className="course-mono">
                        {field.path}
                      </th>
                      {runs.map((run) => {
                        const kind = run.shape.get(field.path);
                        return (
                          <td
                            key={run.index}
                            data-present={kind ? 'yes' : 'no'}
                            title={kind ? `${field.path}: ${kind}` : `${field.path}: липсва`}
                          >
                            {kind ? KIND_LABEL[kind] : '—'}
                          </td>
                        );
                      })}
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </div>

          <h4 className="pv__h">Отговорите едно до друго</h4>
          <div className="pv__runs course-scroll-x">
            {runs.map((run) => (
              <RunCard
                key={run.index}
                run={run}
                open={selected === run.index}
                onToggle={() => setSelected(selected === run.index ? null : run.index)}
              />
            ))}
          </div>
        </>
      )}
    </section>
  );
}

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
    <div className="pv__stat">
      <dt>{label}</dt>
      <dd data-tone={tone}>{value}</dd>
    </div>
  );
}

function RunCard({
  run,
  open,
  onToggle,
}: {
  readonly run: AnalysedRun;
  readonly open: boolean;
  readonly onToggle: () => void;
}): React.ReactElement {
  return (
    <article className="pv__run" data-open={open || undefined}>
      <header>
        <strong>#{run.index}</strong>
        {run.parsed ? (
          <span className="course-badge" data-tone={run.schemaId === 1 ? 'ok' : 'warn'}>
            схема {run.schemaId}
          </span>
        ) : (
          <span className="course-badge" data-tone="bad">
            не се парсва
          </span>
        )}
        {run.hadWrapper && (
          <span className="course-badge" data-tone="warn">
            обвивка
          </span>
        )}
      </header>
      <p className="course-note">
        {run.latencyMs} ms · {run.completionTokens} токена · {run.shape.size} полета
      </p>
      {run.error && <p className="pv__error course-mono">{run.error}</p>}
      <button type="button" className="course-btn" onClick={onToggle}>
        {open ? 'Скрий отговора' : 'Покажи отговора'}
      </button>
      {open && <pre className="pv__raw">{run.raw}</pre>}
    </article>
  );
}
