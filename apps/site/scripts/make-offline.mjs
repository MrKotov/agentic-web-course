#!/usr/bin/env node
/**
 * Post-processes an `OFFLINE_BUILD=1 astro build` output (in dist-offline/) so it opens
 * correctly from a `file://` URL with no network and no server.
 *
 * Problems that remain after Astro's `build.format: 'file'`, and what this does about them:
 *
 * 1. Astro still emits root-relative URLs (`href="/_astro/…"`). A browser resolves those
 *    against the `file://` path of the *current* document, so anything not at the site
 *    root 404s. Every such attribute is rewritten to a path relative to the file it is
 *    written into.
 * 2. Astro's client hydration entrypoints are `<script type="module">`. Chromium and
 *    Firefox both refuse to fetch the import graph of a module script from `file://`.
 *    Fix: every `<script type="module" src="…">` on a page is bundled *together* into one
 *    classic IIFE with esbuild (one bundle per page, not per script — see point 3) and
 *    replaced by one `<script defer src="…">`.
 * 3. Module scripts execute in one shared module graph, so a helper imported by two entry
 *    points (e.g. Starlight's `<starlight-toc>` custom element definition, imported by both
 *    the desktop and mobile table-of-contents scripts) runs exactly once. Bundling each
 *    entry point separately would duplicate that helper and its side effects (a duplicate
 *    `customElements.define` throws). Bundling all of a page's module scripts as one
 *    synthetic entry lets esbuild dedupe the shared module graph, just as the browser's
 *    module loader would.
 * 4. Module scripts (inline or external) are implicitly deferred: they run after the DOM
 *    has parsed. Plain `<script>` in the document `<head>` runs immediately and can hit
 *    `document.body === null`. External replacements get `defer`; inline replacements are
 *    wrapped so they still run in a shared global scope without colliding on identifiers
 *    two originally-separate module scopes both declared (e.g. two `class s { … }`), so
 *    each inline script also gets its own IIFE.
 * 5. React islands (`<astro-island component-url="/…" renderer-url="/…">`) are not loaded
 *    via a `<script>` tag at all: Astro's client runtime calls `import(componentUrl)` at
 *    hydration time. A root-relative `file://` import is blocked the same way a `<script
 *    type="module" src>` is, and Chromium's allow-list for that fetch includes the `data:`
 *    scheme — but a *relative* import from inside a `data:` module fails too (`data:` URLs
 *    cannot be a base for relative resolution: "Invalid relative url or base scheme isn't
 *    hierarchical"), and an import map does not rescue it, because import maps only
 *    intercept specifiers that would otherwise resolve against a real base.
 * 6. `component-url` and `renderer-url` both import a shared React runtime chunk (so React
 *    is a singleton on the page). The fix for point 5 is applied bottom-up: each file's
 *    relative import specifiers are recursively resolved and substituted *in its source
 *    text* with the literal `data:` URI of the already-processed dependency, before that
 *    file itself becomes a `data:` URI. The result has no relative imports left to
 *    resolve. Because a dependency's `data:` URI is computed once and cached by its
 *    original file path, every importer that needs it is handed the exact same URI string
 *    — and two `import()` calls for byte-identical specifier text resolve to the same
 *    entry in the browser's module map, so the shared chunk (and React's internal state
 *    with it) still loads and evaluates exactly once.
 *
 * This only has to handle what Astro + Starlight actually emit for this project — it is
 * not a general-purpose file:// bundler.
 */
import { build } from 'esbuild';
import { mkdtemp, readdir, readFile, rm, writeFile, stat } from 'node:fs/promises';
import { tmpdir } from 'node:os';
import path from 'node:path';
import crypto from 'node:crypto';
import { fileURLToPath } from 'node:url';

const here = path.dirname(fileURLToPath(import.meta.url));
const distDir = path.join(here, '..', 'dist-offline');

async function listFiles(dir) {
  const entries = await readdir(dir, { withFileTypes: true });
  const files = [];
  for (const entry of entries) {
    const full = path.join(dir, entry.name);
    if (entry.isDirectory()) files.push(...(await listFiles(full)));
    else files.push(full);
  }
  return files;
}

/** Path, relative to `fromFile`'s directory, that reaches `distDir + rootPath`. */
function toRelative(fromFile, rootPath) {
  const targetAbs = path.join(distDir, rootPath);
  let rel = path.relative(path.dirname(fromFile), targetAbs).split(path.sep).join('/');
  if (rel === '') rel = path.basename(targetAbs);
  if (!rel.startsWith('.')) rel = `./${rel}`;
  return rel;
}

/**
 * Bundle a set of already-built ESM entry files, in order, into one classic IIFE that
 * dedupes any module they share. Cached by the exact ordered combination, since most pages
 * on a docs site reference the same script set.
 */
const pageBundleCache = new Map();
async function bundlePageScripts(entryRootPaths) {
  const cacheKey = entryRootPaths.join('|');
  const cached = pageBundleCache.get(cacheKey);
  if (cached) return cached;

  const hash = crypto.createHash('sha1').update(cacheKey).digest('hex').slice(0, 12);
  const outRootPath = `_astro/offline-bundles/page-${hash}.js`;
  const outAbsPath = path.join(distDir, outRootPath);

  const tmpDir = await mkdtemp(path.join(tmpdir(), 'course-site-offline-'));
  const entryFile = path.join(tmpDir, 'entry.mjs');
  const importLines = entryRootPaths
    .map((rootPath) => `import ${JSON.stringify(path.join(distDir, rootPath))};`)
    .join('\n');
  await writeFile(entryFile, importLines, 'utf8');

  await build({
    entryPoints: [entryFile],
    bundle: true,
    format: 'iife',
    minify: false,
    outfile: outAbsPath,
    logLevel: 'warning',
  });
  await rm(tmpDir, { recursive: true, force: true });

  pageBundleCache.set(cacheKey, outRootPath);
  return outRootPath;
}

/** Relative import specifiers (`./foo.js`, `../foo.js`) referenced by an ESM source file. */
function relativeImportSpecifiers(source) {
  const specifiers = new Set();
  const re = /\b(?:from|import)\s*\(?\s*["'](\.[^"']+)["']/g;
  for (const match of source.matchAll(re)) specifiers.add(match[1]);
  return [...specifiers];
}

/**
 * Turn a built ESM file into a self-contained `data:` URI: every relative import it makes
 * is first resolved (recursively, depth-first) to its dependency's own `data:` URI and
 * substituted directly into the source text, so nothing is left for the browser to resolve
 * relative to a non-hierarchical `data:` base. Memoized by absolute path, so a chunk shared
 * by multiple importers is only ever turned into one `data:` URI string — which is what
 * keeps it a single, shared module at runtime (see point 6 above).
 */
async function chunkToDataUri(absPath, cache) {
  const cached = cache.get(absPath);
  if (cached) return cached;
  let source = await readFile(absPath, 'utf8');
  const specifiers = relativeImportSpecifiers(source);
  const uriBySpecifier = new Map();
  for (const specifier of specifiers) {
    const depAbsPath = path.join(path.dirname(absPath), specifier);
    uriBySpecifier.set(specifier, await chunkToDataUri(depAbsPath, cache));
  }
  source = source.replace(
    /\b(from|import)(\s*\(?\s*)(["'])(\.[^"']+)\3/g,
    (full, kw, mid, _quote, spec) => {
      const uri = uriBySpecifier.get(spec);
      return uri ? `${kw}${mid}${JSON.stringify(uri)}` : full;
    },
  );
  const uri = `data:text/javascript;base64,${Buffer.from(source, 'utf8').toString('base64')}`;
  cache.set(absPath, uri);
  return uri;
}

/** Rewrite every `<astro-island>`'s `component-url`/`renderer-url` to a self-contained `data:` URI. */
async function inlineAstroIslands(html, dataUriCache) {
  const islandRe = /<astro-island\b[^>]*>/g;
  const matches = [...html.matchAll(islandRe)];
  for (const match of matches) {
    let tag = match[0];
    const original = tag;
    for (const attr of ['component-url', 'renderer-url']) {
      const attrRe = new RegExp(`${attr}="/([^"]+)"`);
      const attrMatch = attrRe.exec(tag);
      if (!attrMatch) continue;
      const entryAbsPath = path.join(distDir, attrMatch[1]);
      const uri = await chunkToDataUri(entryAbsPath, dataUriCache);
      tag = tag.replace(attrRe, `${attr}="${uri}"`);
    }
    if (tag !== original) html = html.replace(original, tag);
  }
  return html;
}

async function processHtmlFile(filePath, dataUriCache) {
  let html = await readFile(filePath, 'utf8');

  html = await inlineAstroIslands(html, dataUriCache);

  // Collect every `<script type="module" src="/…">` tag on the page, in document order,
  // then replace the whole set with one deferred, deduped bundle.
  const moduleSrcRe = /<script\b[^>]*?\btype="module"[^>]*?\bsrc="\/([^"]+)"[^>]*><\/script>/g;
  const srcMatches = [...html.matchAll(moduleSrcRe)];
  if (srcMatches.length > 0) {
    const rootPaths = srcMatches.map((m) => m[1]);
    const bundleRootPath = await bundlePageScripts(rootPaths);
    const relHref = toRelative(filePath, bundleRootPath);
    let first = true;
    for (const match of srcMatches) {
      html = html.replace(match[0], first ? `<script defer src="${relHref}"></script>` : '');
      first = false;
    }
  }

  // Remaining `<script type="module">…inline…</script>` blocks are Starlight's small
  // interactive-element definitions with no `src`. Give each its own function scope (two
  // originally-separate module scopes may both declare, say, `class s`) and defer its run
  // until the DOM has parsed, since module scripts are deferred and plain scripts are not.
  html = html.replace(
    /<script\b([^>]*?)\btype="module"([^>]*?)>([\s\S]*?)<\/script>/g,
    (_full, pre, post, body) => {
      const wrapped = `document.addEventListener("DOMContentLoaded",function(){${body}});`;
      return `<script${pre}${post}>${wrapped}</script>`;
    },
  );

  // Drop modulepreload hints; they target file:// module URLs we no longer use.
  html = html.replace(/<link\b[^>]*\brel="modulepreload"[^>]*>\s*/g, '');

  // Rewrite every remaining root-relative href/src (not `//host`, not `http`) to a path
  // relative to this file. Astro's `build.format: 'file'` writes each page route as a
  // sibling `<name>.html` (there is no `<name>/index.html` directory), but Starlight's own
  // internal links still carry a trailing slash (`/lectures/x/`) regardless of the
  // `trailingSlash` setting. So a page link's trailing slash is stripped and `.html` is
  // appended to match the file actually on disk; `href="/"` maps to the site's `index.html`.
  // Non-page assets (css/js/svg/xml under `_astro/`, `favicon.svg`, …) never end in `/` and
  // already carry their real extension, so they pass through unchanged.
  html = html.replace(/\b(href|src)="\/(?!\/)([^"]*)"/g, (_m, attr, rootPath) => {
    let targetPath = rootPath;
    if (targetPath.endsWith('/')) {
      targetPath = targetPath.slice(0, -1);
      targetPath = targetPath === '' ? 'index.html' : `${targetPath}.html`;
    } else if (targetPath === '') {
      targetPath = 'index.html';
    }
    const rel = toRelative(filePath, targetPath);
    return `${attr}="${rel}"`;
  });

  await writeFile(filePath, html, 'utf8');
}

async function main() {
  try {
    const rootStat = await stat(distDir);
    if (!rootStat.isDirectory()) throw new Error(`${distDir} is not a directory`);
  } catch {
    console.error(`make-offline: ${distDir} does not exist — run with OFFLINE_BUILD=1 first.`);
    process.exitCode = 1;
    return;
  }

  const files = await listFiles(distDir);
  const htmlFiles = files.filter((f) => f.endsWith('.html'));
  const dataUriCache = new Map();
  for (const file of htmlFiles) {
    await processHtmlFile(file, dataUriCache);
  }
  console.log(`make-offline: rewrote ${htmlFiles.length} HTML file(s) for file:// use in ${distDir}`);
}

await main();
