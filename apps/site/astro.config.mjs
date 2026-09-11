// @ts-check
import { defineConfig } from 'astro/config';
import starlight from '@astrojs/starlight';
import react from '@astrojs/react';

/**
 * OFFLINE_BUILD=1 produces an output that can be opened straight from disk (file://):
 * `build.format: 'file'` emits real .html files, and scripts/make-offline.mjs afterwards
 * rewrites every absolute URL to a relative one and inlines the island JS as a classic
 * script (browsers refuse to load external ES modules over file://).
 *
 * SITE_BASE is the GitHub Pages sub-path. The deploy workflow sets it to the repo name.
 */
const offline = process.env.OFFLINE_BUILD === '1';
const base = offline ? '/' : (process.env.SITE_BASE ?? '/');

export default defineConfig({
  site: process.env.SITE_URL ?? 'https://example.github.io',
  base,
  outDir: offline ? './dist-offline' : './dist',
  build: { format: offline ? 'file' : 'directory', inlineStylesheets: 'auto' },
  trailingSlash: offline ? 'never' : 'ignore',
  integrations: [
    react(),
    starlight({
      title: 'Агентно уеб разработване',
      description:
        'Курс „Програмиране в Internet“ — ТУ София, ФКСТ. Агентно софтуерно инженерство за уеб разработчици.',
      defaultLocale: 'bg',
      locales: { root: { label: 'Български', lang: 'bg' } },
      customCss: ['./src/styles/course.css'],
      pagefind: !offline,
      credits: false,
      tableOfContents: { minHeadingLevel: 2, maxHeadingLevel: 3 },
      sidebar: [
        { label: 'Лекции', autogenerate: { directory: 'lectures' } },
        { label: 'Упражнения', autogenerate: { directory: 'exercises' } },
        { label: 'Справочник', autogenerate: { directory: 'reference' } },
      ],
    }),
  ],
});
