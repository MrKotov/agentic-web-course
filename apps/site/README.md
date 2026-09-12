# Course site

Static site for "Програмиране в Internet" (agentic web development), TU-Sofia. Astro +
Starlight, content in MDX, interactive pieces as React islands. Public, no login, no
student data. Spec: `handover/01-course-site.spec.md`.

## Requirements

- Node 24 (see `.nvmrc`). System Node on some machines is much older — check with
  `node -v` before running anything.

## Running locally

```bash
cd apps/site
npm install
npm run dev        # http://localhost:4321
```

## Building

```bash
npm run build           # dist/ — normal static output, served from a domain root or SITE_BASE
npm run build:offline   # dist-offline/ — opens directly from disk via a file:// URL, no server
npm run preview         # serve dist/ locally to sanity-check a production build
```

`npm run build:offline` runs `astro build` with `OFFLINE_BUILD=1` (real `.html` files
instead of `<page>/index.html` directories, no Pagefind index, base forced to `/`), then
`scripts/make-offline.mjs`, which rewrites the output so it works with **no server and no
network**:

- every root-relative `href`/`src` becomes relative to the file it's written in;
- `<script type="module">` tags are bundled into classic, deferred `<script>`s, because
  browsers refuse to fetch a module's import graph from `file://`;
- React islands (`<astro-island>`, used by the prompt variance runner) are hydrated by a
  runtime `import()` call rather than a `<script>` tag, so their `component-url` and
  `renderer-url` are inlined as self-contained `data:` URIs instead — see the comment at
  the top of `scripts/make-offline.mjs` for why this has to happen bottom-up (naively
  bundling each entry independently duplicates the shared React runtime chunk and crashes
  hydration with `Cannot read properties of null (reading 'useState')`).

Verified for this build: opening `dist-offline/*.html` directly via `file://` in Chrome
(headless, `--dump-dom` and a Puppeteer smoke pass across every page) shows zero console
errors and zero failed requests, internal navigation between pages works, and the prompt
variance runner in lecture 1 is fully clickable and produces output with no key and no
network. See the handoff notes for the exact commands used.

## Adding a new lecture, exercise, or reference page

Content lives under `src/content/docs/`:

```
lectures/NN-slug.mdx     # numbered 01-10
exercises/NN-slug.mdx    # numbered 01-05
reference/slug.mdx
```

Every page needs Starlight frontmatter (`title`, `description` — quote both if the text
contains a colon, or the YAML parser breaks). A lecture page should carry, in this order:
concepts, the live demo script for the instructor, a predict-then-reveal prompt with its
expected wrong answer, and a link to the matching folder in `apps/examples/`. Lectures 3–10
and exercises 2–5 are currently stubs with the section headings already in place — filling
them in is prose, not restructuring.

Sidebars are auto-generated from the three top-level directories (see
`astro.config.mjs`, `sidebar: [...]`); a new file just needs to exist in the right folder
with correct frontmatter to show up.

## Interactive components

`src/components/`. Only the **prompt variance runner** (`PromptVarianceRunner.tsx`,
lecture 1) is fully built, wired to the recorded fixture in `src/data/prompt-variance.ts`
(ten real-shaped, hand-varied responses to one prompt — inconsistent casing, a field that
moves between flat and nested, a type flip on `salary`, an object-vs-array flip, one
deliberately invalid JSON payload, and one run where the model localised the keys into
Bulgarian). It works fully offline with the "Записан режим" (recorded mode) button; "На
живо" (live mode) needs the viewer's own API key and depends on an **unverified** CORS
assumption — see `src/content/docs/reference/tooling.mdx`.

The other five components from the spec are placeholders (`*Placeholder.tsx`), each citing
the exact spec section it implements and why it isn't built yet. The agent-loop stepper
specifically must stay a placeholder until `docs/gate-zero.md` item 4 (whether VoltAgent's
own execution console is presentable) is resolved — building it before that check risks
throwing away the most expensive component on the site.

## Deploying

`.github/workflows/deploy-site.yml`, at the **monorepo root** (GitHub Pages workflows must
live in a root-level `.github/workflows/`; Actions does not look inside
`apps/site/.github/`). It triggers only on pushes touching `apps/site/**`, builds with
`npm run build`, and deploys `apps/site/dist` to GitHub Pages. When `apps/site/` is split
into its own public repo (`docs/splitting-repos.md`), this file moves with it, the `paths`
filter is dropped, and the `working-directory: apps/site` / `apps/site/` path prefixes in
the workflow are removed since the site becomes the whole repo at that point.

## Known gaps

- Lectures 3–10 and exercises 2–5 are stubs (see `handover/01-course-site.spec.md` scope
  for this pass — only lectures 1–2 got full content).
- `reference/conspectus.mdx` lists 14 topics justified by the specs; slots 15–24 are
  marked TODO rather than invented.
- Live mode's CORS assumption (`docs/gate-zero.md` item 5) has not been tested against the
  real provider from a browser.
- `npm audit` reports vulnerabilities (1 critical, 1 high) in Astro's dependency chain
  (XSS advisories, a `sharp`/libvips issue) fixed only by a major upgrade to Astro 7,
  which `npm audit fix --force` would apply. Not done in this pass: it's a breaking change
  that would need the `file://` offline-build fixes in `scripts/make-offline.mjs`
  re-verified against Astro 7's output shape before trusting it. Track separately.
