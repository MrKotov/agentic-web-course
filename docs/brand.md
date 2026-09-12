# Brand: TU Sofia colors

Single source of truth for color across `apps/site/` and `apps/platform/`. Both restyles
must pull from this file rather than inventing their own values, so the two apps read as
one system rather than two unrelated redesigns.

## Where these numbers came from

Not guessed, not from a public brand-guidelines PDF (none is indexed publicly as of this
writing). Sampled directly from `tu-sofia.bg`'s live, rendered page on 2026-09-12:

- Header background, computed via `getComputedStyle`, converted through a canvas
  round-trip: **`#233876`**.
- Primary nav buttons ("За университета", "Студенти", "Наука и иновации"): **`#1c2d5e`**.
- Repeated pill/tag elements (category labels on news cards, most frequent single value
  on the page): **`#1d3b76`**.
- The one bright, saturated color on the page, used only for the single primary
  call-to-action ("Прием 2026"): **`#1447e6`**.
- Light card background behind image placeholders: **`#f5f7ff`**.
- The university's own logo mark ships in exactly two variants: solid white, and solid
  black — no color in the mark itself. White-on-navy is the pairing actually used in
  their own header. That is the pairing to reuse, not a novel combination.

These four navy values (`#233876`, `#1c2d5e`, `#1d3b76`, plus `#233875` seen once) are
one design intent expressed slightly differently across components, not four different
colors — treat them as one navy with minor implementation drift on the source site.

## Tokens

```css
/* Brand — from tu-sofia.bg, do not adjust without re-sampling the source */
--tu-navy:        #1d3b76;  /* primary: headers, nav, primary buttons */
--tu-navy-dark:   #14285c;  /* hover/active state on navy, dark-mode surface */
--tu-navy-light:  #2c4f96;  /* hover state on white, accessible-on-navy tints */
--tu-blue:        #1447e6;  /* single accent — reserve for ONE primary action per view */
--tu-blue-tint:   #f5f7ff;  /* card/section backgrounds, light mode only */

/* Neutrals — not sampled from the source (their site doesn't need to serve MDX prose
   or code blocks); chosen to sit quietly next to --tu-navy without competing */
--ink:            #101828;  /* body text, light mode */
--ink-muted:      #4b5565;
--paper:          #ffffff;  /* page background, light mode */
--paper-sunken:   #f5f7ff;  /* = --tu-blue-tint, reused for consistency */
--border:         #dfe4ee;

/* Dark mode — navy is already dark, so dark mode inverts around it rather than
   producing a second unrelated palette */
--ink-dark:       #e8ecf5;
--ink-muted-dark: #a3adc2;
--paper-dark:     #0b1224;
--paper-sunken-dark: #121a33;
--border-dark:    #263257;

/* Semantic — functional, not brand. Never repurpose these for decoration. */
--success:        #176e45;  /* darkened from an earlier #1a7f4f: that measured 4.42:1 on
                                --success-tint, just under AA's 4.5:1 for body text. This
                                measures 5.52:1. */
--success-tint:   #e6f4ec;
--danger:         #c4293a;
--danger-tint:    #fbeaec;
--warning:        #a15c00;
--warning-tint:   #fbf0dc;
```

## Visual stack (decided 2026-09-12, superseding the first hand-rolled-CSS pass)

The first redesign pass (hand-rolled `course.css` custom properties, Django templates
styled by hand) read as dated rather than modern — confirmed by the user directly, not a
guess. Replacing it with the stack the current AI-coding-agent ecosystem has actually
converged on, per a live search on 2026-09-12 (shadcn/ui ~75k GitHub stars, official
Astro support, what Claude/Cursor/v0/Bolt are trained on and default to):

- **`apps/site/`** (Astro + Starlight, one React island): **Tailwind CSS + shadcn/ui**.
  shadcn ships component *source*, not a package — it lands in the repo as ordinary
  editable React/TSX, which is why agents default to it. Use Astro's official Tailwind
  integration and shadcn's Astro install path (check current docs at implementation
  time rather than trusting this file's memory of exact package names — verify, this
  moves fast). Starlight's own design tokens should be bridged to Tailwind's, not
  fought — Starlight ships an official Tailwind pairing for exactly this.
- **`apps/platform/`** (Django + HTMX, server-rendered, no React): **Tailwind CSS +
  DaisyUI**. shadcn doesn't apply here — it's a React source-copy pattern, and there is
  no React in this app, on purpose, per `CLAUDE.md`'s settled Django+HTMX stack
  decision. DaisyUI is the equivalent-tier, similarly-adopted choice for
  framework-agnostic server-rendered HTML: plain class names, no JS framework
  dependency, works directly in Django templates.
- **Both still read `docs/brand.md`'s color tokens above** — the library changes, the
  brand identity (TU Sofia navy, one-accent-per-view discipline) does not. Map the
  `--tu-*`/`--success`/etc. custom properties into each tool's own theming layer
  (Tailwind theme config / shadcn's CSS variables / DaisyUI's theme system) rather than
  hand-writing a second, parallel color system.
- Aim for what actually reads as current in 2026: generous whitespace, a restrained
  neutral base (the brand color does the talking, not five competing tones), soft
  borders and subtle shadows instead of heavy ones, real spacing rhythm, one accent
  color per view. Compare against what shadcn's own component gallery and Starlight's
  official demo sites look like before calling something done — not against what the
  first pass produced.

## Rules

1. **`--tu-blue` is scarce on purpose.** The source site uses its one bright blue for
   exactly one thing per page: the primary call to action. Copy that discipline — one
   `--tu-blue` element per view (the join-quiz button, "Стартирай" on the variance
   runner), not every interactive element.
2. **Navy carries the identity, not blue.** Headers, nav, and primary buttons are navy.
   If a page reads as "a blue site" rather than "a navy site with one blue accent,"
   that's the token misused.
3. **White text on navy, navy text on white** — the verified pairing. Don't put navy
   text on `--tu-blue-tint` at low contrast; check against WCAG AA (4.5:1 body text)
   before shipping any new color pair, especially in dark mode where the swaps above are
   inversions, not verified samples.
4. **Semantic colors stay semantic.** `--success`/`--danger`/`--warning` are for pass/fail
   states (autograder results, form validation) — never used as decoration or to imply
   brand.
5. Both apps expose these as CSS custom properties on `:root` (and the dark-mode block),
   named identically, so a value changed here is a value changed in exactly two files,
   not a search-and-replace across templates.
