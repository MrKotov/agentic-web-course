/**
 * Recorded fixture for the prompt variance runner (lecture 1 demo).
 *
 * One prompt, ten runs, same model, same temperature. The point of the demo is that the
 * *text* is roughly right every time and the *schema* is different almost every time, so
 * anything downstream that assumes a shape breaks in production and not in the demo.
 *
 * These are recorded responses committed to the repo on purpose: the demo must run with no
 * key and no network. No student data, no secrets, no account identifiers.
 */

export interface RecordedRun {
  /** 1-based run number as presented in the hall. */
  readonly index: number;
  /** Raw assistant message content, exactly as it came back — fences, prose and all. */
  readonly raw: string;
  readonly latencyMs: number;
  readonly completionTokens: number;
  readonly finishReason: 'stop' | 'length';
}

export interface VarianceFixture {
  readonly id: string;
  readonly label: string;
  readonly model: string;
  readonly temperature: number;
  readonly recordedAt: string;
  readonly systemPrompt: string;
  readonly userPrompt: string;
  readonly promptTokens: number;
  readonly runs: readonly RecordedRun[];
}

const SYSTEM_PROMPT =
  'Ти си парсер на обяви за работа. Връщай само JSON, без обяснения.';

const INPUT_AD = `Търсим Senior Frontend Developer за екипа ни в София (хибридно, 2 дни в офиса).
Работа с React и TypeScript, опит с GraphQL е предимство. Минимум 5 години опит.
Възнаграждение: 6000 – 8000 лв. нето месечно. Постоянен трудов договор.
Предлагаме допълнително здравно осигуряване и бюджет за обучение.`;

const USER_PROMPT = `Извлечи структурирани данни от следната обява за работа и ги върни като JSON:

${INPUT_AD}`;

/** The ten recorded runs. Drift is deliberate and was not edited in. */
const RUNS: readonly RecordedRun[] = [
  {
    index: 1,
    latencyMs: 1840,
    completionTokens: 158,
    finishReason: 'stop',
    raw: `{
  "title": "Senior Frontend Developer",
  "company": null,
  "location": "София",
  "employment_type": "постоянен трудов договор",
  "remote": "хибридно",
  "salary": { "min": 6000, "max": 8000, "currency": "BGN", "period": "месечно", "net": true },
  "requirements": ["React", "TypeScript", "5 години опит"],
  "nice_to_have": ["GraphQL"],
  "benefits": ["допълнително здравно осигуряване", "бюджет за обучение"]
}`,
  },
  {
    index: 2,
    latencyMs: 2110,
    completionTokens: 141,
    finishReason: 'stop',
    // camelCase instead of snake_case, salary collapsed into a string.
    raw: `{
  "jobTitle": "Senior Frontend Developer",
  "companyName": null,
  "location": "София",
  "employmentType": "full-time",
  "isRemote": false,
  "hybridDays": 2,
  "salaryRange": "6000-8000 BGN net/month",
  "skills": ["React", "TypeScript", "GraphQL"],
  "yearsOfExperience": 5
}`,
  },
  {
    index: 3,
    latencyMs: 2530,
    completionTokens: 187,
    finishReason: 'stop',
    // Prose preamble plus a markdown fence, despite "връщай само JSON".
    raw: `Ето структурираните данни от обявата:

\`\`\`json
{
  "position": "Senior Frontend Developer",
  "city": "София",
  "country": "България",
  "work_mode": "hybrid",
  "office_days_per_week": 2,
  "salary_min": 6000,
  "salary_max": 8000,
  "currency": "BGN",
  "salary_type": "net",
  "contract": "permanent",
  "required_skills": ["React", "TypeScript"],
  "preferred_skills": ["GraphQL"],
  "min_experience_years": 5
}
\`\`\`

Забележка: името на компанията не е посочено в обявата.`,
  },
  {
    index: 4,
    latencyMs: 1960,
    completionTokens: 203,
    finishReason: 'stop',
    // Skills promoted from strings to objects; extra nesting under "job".
    raw: `{
  "job": {
    "title": "Senior Frontend Developer",
    "seniority": "senior",
    "location": { "city": "София", "country": "BG", "arrangement": "hybrid", "onsite_days": 2 },
    "compensation": { "min": 6000, "max": 8000, "currency": "BGN", "period": "month", "is_net": true },
    "tech_stack": [
      { "name": "React", "required": true },
      { "name": "TypeScript", "required": true },
      { "name": "GraphQL", "required": false }
    ],
    "experience_years_min": 5
  },
  "metadata": { "language": "bg", "confidence": 0.92 }
}`,
  },
  {
    index: 5,
    latencyMs: 2240,
    completionTokens: 149,
    finishReason: 'stop',
    // Top-level array instead of an object. Everything downstream that did obj.title breaks.
    raw: `[
  {
    "title": "Senior Frontend Developer",
    "company": "не е посочена",
    "location": "София (хибридно)",
    "employment_type": "постоянен",
    "salary": "6000 – 8000 лв. нето",
    "requirements": ["React", "TypeScript", "минимум 5 години опит"],
    "advantages": ["GraphQL"],
    "benefits": ["здравно осигуряване", "бюджет за обучение"]
  }
]`,
  },
  {
    index: 6,
    latencyMs: 3010,
    completionTokens: 176,
    finishReason: 'stop',
    // Invalid JSON: a trailing comma. JSON.parse throws. This happens in production.
    raw: `{
  "title": "Senior Frontend Developer",
  "location": "София",
  "remote_policy": "хибридно, 2 дни в офиса",
  "salary": { "min": 6000, "max": 8000, "currency": "лв.", "period": "месечно" },
  "requirements": [
    "React",
    "TypeScript",
    "5+ години опит",
  ],
  "optional": ["GraphQL"]
}`,
  },
  {
    index: 7,
    latencyMs: 1770,
    completionTokens: 118,
    finishReason: 'stop',
    // requirements is a single string, not an array. salary numbers became strings.
    raw: `{
  "title": "Senior Frontend Developer",
  "company": "",
  "location": "София",
  "employment_type": "постоянен трудов договор",
  "remote": "хибридно",
  "salary": { "min": "6000", "max": "8000", "currency": "BGN", "period": "месечно", "net": true },
  "requirements": "React, TypeScript, минимум 5 години опит, GraphQL е предимство",
  "benefits": ["допълнително здравно осигуряване", "бюджет за обучение"]
}`,
  },
  {
    index: 8,
    latencyMs: 2620,
    completionTokens: 211,
    finishReason: 'stop',
    // Invented fields that are nowhere in the input: deadline, contact, id.
    raw: `{
  "id": "job-2026-0417",
  "title": "Senior Frontend Developer",
  "company": null,
  "location": "София",
  "employment_type": "постоянен трудов договор",
  "remote": "хибридно",
  "application_deadline": "2026-03-15",
  "contact_email": "jobs@company.bg",
  "salary": { "min": 6000, "max": 8000, "currency": "BGN", "period": "месечно", "net": true },
  "requirements": ["React", "TypeScript", "5 години опит"],
  "nice_to_have": ["GraphQL"],
  "benefits": ["допълнително здравно осигуряване", "бюджет за обучение"]
}`,
  },
  {
    index: 9,
    latencyMs: 1690,
    completionTokens: 74,
    finishReason: 'stop',
    // Minimal answer. Half the fields are simply gone.
    raw: `{
  "title": "Senior Frontend Developer",
  "location": "София",
  "salary": "6000-8000 лв.",
  "skills": ["React", "TypeScript", "GraphQL"]
}`,
  },
  {
    index: 10,
    latencyMs: 2380,
    completionTokens: 165,
    finishReason: 'stop',
    // Bulgarian keys. The prompt was Bulgarian, so the model localised the schema too.
    raw: `{
  "длъжност": "Senior Frontend Developer",
  "компания": null,
  "локация": "София",
  "режим_на_работа": "хибриден",
  "дни_в_офис": 2,
  "възнаграждение": { "от": 6000, "до": 8000, "валута": "лв.", "период": "месец", "нето": true },
  "изисквания": ["React", "TypeScript", "5 години опит"],
  "предимства": ["GraphQL"],
  "тип_договор": "постоянен"
}`,
  },
];

export const PROMPT_VARIANCE_FIXTURE: VarianceFixture = {
  id: 'job-ad-extraction-v1',
  label: 'Извличане на структурирани данни от обява за работа',
  model: 'записан модел (среден клас, инструкционно настроен)',
  temperature: 0.7,
  recordedAt: '2026-02-11',
  systemPrompt: SYSTEM_PROMPT,
  userPrompt: USER_PROMPT,
  promptTokens: 214,
  runs: RUNS,
};

export const PROMPT_VARIANCE_FIXTURES: readonly VarianceFixture[] = [PROMPT_VARIANCE_FIXTURE];
