/**
 * Browser-direct call to an OpenAI-compatible chat completions endpoint.
 *
 * OPEN QUESTION, see reference/tooling: browser-origin calls depend on the provider
 * sending permissive CORS headers. This has NOT been verified for the provider the course
 * will use. Until it is, recorded mode is the supported path and live mode is opt-in.
 *
 * The key goes from the viewer's browser straight to the endpoint in the Authorization
 * header. Nothing is proxied and nothing is logged.
 */

export interface LiveConfig {
  readonly endpoint: string;
  readonly model: string;
  readonly apiKey: string;
  readonly temperature: number;
}

export interface LiveResult {
  readonly content: string;
  readonly latencyMs: number;
  readonly completionTokens: number;
}

interface ChatChoice {
  readonly message?: { readonly content?: string };
}
interface ChatResponse {
  readonly choices?: readonly ChatChoice[];
  readonly usage?: { readonly completion_tokens?: number };
}

export const DEFAULT_ENDPOINT = 'https://openrouter.ai/api/v1/chat/completions';

export async function runOnce(
  config: LiveConfig,
  systemPrompt: string,
  userPrompt: string,
  signal: AbortSignal,
): Promise<LiveResult> {
  const startedAt = performance.now();
  const response = await fetch(config.endpoint, {
    method: 'POST',
    signal,
    headers: {
      'Content-Type': 'application/json',
      Authorization: `Bearer ${config.apiKey}`,
    },
    body: JSON.stringify({
      model: config.model,
      temperature: config.temperature,
      messages: [
        { role: 'system', content: systemPrompt },
        { role: 'user', content: userPrompt },
      ],
    }),
  });

  if (!response.ok) {
    throw new Error(`HTTP ${response.status} ${response.statusText}`);
  }
  const payload = (await response.json()) as ChatResponse;
  const content = payload.choices?.[0]?.message?.content ?? '';
  return {
    content,
    latencyMs: Math.round(performance.now() - startedAt),
    completionTokens: payload.usage?.completion_tokens ?? 0,
  };
}
